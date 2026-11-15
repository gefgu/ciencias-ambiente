"""Camada ciber-física via MQTT (M3): sensores virtuais -> broker -> controlador -> comando de fase -> SUMO.

Tópicos (contrato M1, src/m1/contract.py):
  cps/curitiba/{intersection_id}/sensors/{sensor_id}   <- Automação (nó sensor)
  cps/curitiba/{intersection_id}/metrics               <- fila e CO2 instantâneo
  cps/curitiba/{intersection_id}/signal/cmd            <- Computação (controlador)
Broker de produção: Eclipse Mosquitto (sim/mosquitto.conf). Nos testes usa-se o broker Python `amqtt` (mesmo protocolo MQTT 3.1.1).
"""
from __future__ import annotations
import json, queue, threading, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from .controllers import Controller, Params, State
from src.m1.contract import IntersectionMessage

BASE = "cps/curitiba"


def _client(cid: str, host: str, port: int) -> mqtt.Client:
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    c.connect(host, port, keepalive=30)
    try:
        import socket
        c.socket().setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # evita que Nagle/ACK atrasado domine a latência medida
    except Exception:
        pass
    c.loop_start()
    return c


class MqttBridge:
    """Interface `exchange(tls_id, State, now)` usada por tobe.run: publica o estado, espera o comando do controlador remoto."""

    def __init__(self, host="127.0.0.1", port=1883, params: Params | None = None, timeout=2.0):
        self.params, self.timeout = params or Params(), timeout
        self.sensor = _client("sensor-node", host, port)
        self.ctrl = _client("controller-node", host, port)
        self.sim = _client("sumo-actuator", host, port)
        self.ctrls: dict[str, Controller] = {}
        self.inbox: dict[str, queue.Queue] = {}
        self.latency_ms: list[float] = []
        self.stale = 0      # respostas descartadas por seq antigo
        self.timeouts = 0   # trocas sem resposta no prazo (a fase fica em 'hold': estado seguro)
        self.n_msgs = 0
        self.ctrl.on_message = self._on_sensor
        self.sim.on_message = self._on_cmd
        self.ctrl.subscribe(f"{BASE}/+/state")
        self.sim.subscribe(f"{BASE}/+/signal/cmd")
        time.sleep(0.3)

    # --- nó controlador (Computação) ---
    def _on_sensor(self, c, u, msg):
        d = json.loads(msg.payload)
        iid = d["intersection_id"]
        ctl = self.ctrls.setdefault(iid, Controller(Params(**self.params.__dict__)))
        s = State(**d["state"])
        a, secs = ctl.decide(s)
        c.publish(f"{BASE}/{iid}/signal/cmd", json.dumps({"action": a, "seconds": secs, "t_sent": d["t_sent"], "seq": d["seq"]}), qos=1)

    # --- atuador no lado do SUMO (Automação) ---
    def _on_cmd(self, c, u, msg):
        iid = msg.topic.split("/")[2]
        self.inbox.setdefault(iid, queue.Queue()).put(json.loads(msg.payload))

    def exchange(self, tls_id: str, s: State, now: float):
        iid = tls_id.replace("/", "_")
        q = self.inbox.setdefault(iid, queue.Queue())
        t_sent = time.time()
        self.seq = getattr(self, "seq", 0) + 1
        seq = self.seq
        # mensagem de sensores conforme o contrato (validada) + estado interno para o controlador
        msg = {"timestamp": datetime.now(timezone.utc).isoformat(), "intersection_id": iid,
               "sensors": [{"sensor_id": f"loop_green", "state": "occupied" if s.occ_green > 0 else "free", "vehicle_speed_kmh": None}],
               "instantaneous_metrics": {"queue_length_meters": 7.5 * (s.q_green + s.q_red), "co2_grams_per_second": 0.0}}  # CO2 instantâneo não é estimado no nó sensor (campo exigido pelo contrato; preencher com o modelo de emissões)
        IntersectionMessage.model_validate(msg)
        self.sensor.publish(f"{BASE}/{iid}/sensors/loop_green", json.dumps(msg), qos=0)
        self.sensor.publish(f"{BASE}/{iid}/metrics", json.dumps({"timestamp": msg["timestamp"], "queue_length_meters": msg["instantaneous_metrics"]["queue_length_meters"]}), qos=0)
        self.sensor.publish(f"{BASE}/{iid}/state", json.dumps({"intersection_id": iid, "t_sent": t_sent, "seq": seq, "state": s.__dict__}), qos=1)
        self.n_msgs += 3
        deadline = time.time() + self.timeout
        r = None
        while time.time() < deadline:   # descarta respostas atrasadas de trocas anteriores (seq diferente)
            try:
                cand = q.get(timeout=max(deadline - time.time(), 0.01))
            except queue.Empty:
                break
            if cand.get("seq") == seq:
                r = cand
                break
            self.stale += 1
        if r is None:
            self.timeouts += 1
            return "hold", 0.0
        self.latency_ms.append(1000 * (time.time() - r["t_sent"]))
        return r["action"], r["seconds"]

    def close(self):
        for c in (self.sensor, self.ctrl, self.sim):
            c.loop_stop(); c.disconnect()
