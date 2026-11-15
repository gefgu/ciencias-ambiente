"""Demonstração/teste da malha fechada via MQTT: SUMO -> sensores -> broker -> controlador -> comando -> SUMO.

Mede a latência ponta a ponta (localhost) e conta mensagens, respostas atrasadas e timeouts. NÃO verifica equivalência com a execução em processo.
"""
from __future__ import annotations
import json, statistics
import sumolib
from . import tobe
from .broker import LocalBroker
from .common import SIM, OUT
from .mqtt_bridge import MqttBridge
from .controllers import Params


def pick_tls(n=6) -> list[str]:
    """Semáforos mais próximos dos pontos de medição (P01–P04)."""
    import pandas as pd
    from src.m1.traffic import PH
    net = sumolib.net.readNet(str(SIM / "net.net.xml"))
    pts = pd.read_csv(PH / "points.csv")
    ids = []
    for r in pts.itertuples():
        x, y = net.convertLonLat2XY(r.lon, r.lat)
        nodes = [n for n in net.getNodes() if n.getType() == "traffic_light" or n.getType().startswith("traffic")]
        best = sorted(nodes, key=lambda n: (n.getCoord()[0] - x) ** 2 + (n.getCoord()[1] - y) ** 2)[:2]
        ids += [n.getID() for n in best]
    return list(dict.fromkeys(ids))[:n]


def run(seconds: int = 600) -> dict:
    tls = pick_tls()
    broker = LocalBroker().start()
    try:
        br = MqttBridge(params=Params())
        info = tobe.run("am", tag="mqtt_demo", max_sim_s=seconds, bridge=br, only_tls=tls)
        lat = br.latency_ms
        res = {"tls_controlled": tls, "sim_seconds": seconds, "msgs_published": br.n_msgs, "commands_received": len(lat),
               "latency_ms_median": round(statistics.median(lat), 2) if lat else None, "latency_ms_p95": round(sorted(lat)[int(.95 * len(lat))], 2) if lat else None,
               "stale_discarded": br.stale, "timeouts": br.timeouts, "decisions": info["decisions"]}
        br.close()
    finally:
        broker.stop()
    (OUT / "m3_mqtt.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    print(run())
