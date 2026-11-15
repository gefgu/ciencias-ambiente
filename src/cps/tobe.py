"""Runner TraCI do cenário To-Be: mesmos arquivos de demanda e semente do As-Is + controle adaptativo (M3/M4)."""
from __future__ import annotations
import time
import traci
from .common import SIM, WORK, WINDOWS
from .controllers import Controller, Params, State


def write_add(win: str, tag: str):
    """Saídas com o tag no nome: não sobrescrevem as do As-Is."""
    from .simrun import additional_xml
    f = WORK / f"detectors_{tag}_{win}.add.xml"
    f.write_text(additional_xml(f"{WORK}/", tag, win))
    return f


class TlsMap:
    """Estrutura estática de cada semáforo: faixas servidas por fase."""

    def __init__(self):
        self.ids = [t for t in traci.trafficlight.getIDList()]
        self.phases, self.green_lanes, self.all_lanes, self.is_green = {}, {}, {}, {}
        self.lane_len = {}
        self.lane_to_tls: dict[str, str] = {}
        keep = []
        for t in self.ids:
            logic = traci.trafficlight.getAllProgramLogics(t)[0]
            links = traci.trafficlight.getControlledLinks(t)
            allw = {l[0][0] for l in links if l}
            greens = []
            for ph in logic.phases:
                greens.append({links[i][0][0] for i, c in enumerate(ph.state) if c in "Gg" and i < len(links) and links[i]})
            n_green = sum(1 for ph in logic.phases if any(c in "Gg" for c in ph.state) and "y" not in ph.state)
            if n_green < 2:
                continue
            keep.append(t)
            self.phases[t], self.green_lanes[t], self.all_lanes[t] = logic, greens, allw
            self.is_green[t] = [any(c in "Gg" for c in ph.state) and "y" not in ph.state and "Y" not in ph.state for ph in logic.phases]
            for l in allw:
                self.lane_to_tls[l] = t
                self.lane_len[l] = traci.lane.getLength(l)
        self.ids = keep


def to_static(tm: TlsMap, only: list[str] | None = None):
    """Converte programas actuated do netconvert em programas estáticos controlados por TraCI (só os semáforos em `only`)."""
    for t in (only if only is not None else tm.ids):
        lg = tm.phases[t]
        ph = [traci.trafficlight.Phase(p.duration if p.duration > 0 else 10, p.state) for p in lg.phases]
        new = traci.trafficlight.Logic("adaptive", 0, 0, phases=ph)
        traci.trafficlight.setProgramLogic(t, new)


def measure(tm: TlsMap, t: str, buses: set[str], bus_dist: float = 120.0, served: set | None = None, last_red: dict | None = None) -> State:
    ph = traci.trafficlight.getPhase(t)
    g = tm.green_lanes[t][ph]
    r = tm.all_lanes[t] - g
    q_g = sum(traci.lane.getLastStepHaltingNumber(l) for l in g)
    q_r = sum(traci.lane.getLastStepHaltingNumber(l) for l in r)
    occ = sum(traci.lane.getLastStepOccupancy(l) for l in g) / max(len(g), 1)
    co2 = sum(traci.lane.getCO2Emission(l) for l in tm.all_lanes[t]) / 1000.0   # mg/s -> g/s
    bg = br = False
    nxt = True
    reds = []
    n_ph = len(tm.green_lanes[t])
    for b in buses:
        try:
            ln = traci.vehicle.getLaneID(b)
        except traci.TraCIException:
            continue
        if tm.lane_to_tls.get(ln) != t:
            continue
        if tm.lane_len[ln] - traci.vehicle.getLanePosition(b) < bus_dist:
            if ln in g:
                bg = True
            elif traci.vehicle.getSpeed(b) > 1.0 and not (served is not None and (b, t) in served):  # ônibus em ponto (parado) não pede prioridade; 1 pedido por ônibus/semáforo
                br = True
                reds.append(b)
                k = next((k for k in ((ph + i) % n_ph for i in range(1, n_ph)) if tm.is_green[t][k]), None)
                nxt = nxt and (k is not None and ln in tm.green_lanes[t][k])
    if last_red is not None:
        last_red[t] = reds
    return State(ph, traci.trafficlight.getSpentDuration(t), tm.is_green[t][ph], q_g, q_r, bg, br, occ, nxt if br else True, co2)


def apply(t: str, action: str, secs: float, now: float):
    if action == "extend":
        traci.trafficlight.setPhaseDuration(t, max(traci.trafficlight.getNextSwitch(t) - now, 0) + secs)
    elif action == "switch":
        traci.trafficlight.setPhaseDuration(t, 0)


def run(win: str = "am", routes=None, adaptive: bool = True, bus_priority: bool = True, params: Params | None = None, tag: str = "tobe",
        seed: int = 1, end: int = 5400, fake_bus_every: int = 0, bridge=None, max_sim_s: int | None = None, only_tls: list[str] | None = None, extra: list[str] | None = None,
        net: str = "net.net.xml", extra_routes: str | None = None, static: bool = True, scale: float = 1.0, greenwave: bool | str = False) -> dict:   # greenwave: False | True/"wave" | "fixed" (controle)
    add = write_add(win, tag)
    routes = routes or SIM / f"routes_asis_{win}.rou.xml"
    cmd = ["sumo", "-n", str(SIM / net), "-r", str(routes) + (f",{extra_routes}" if extra_routes else ""), "-a", f"{SIM / 'vtypes.add.xml'},{add}", "--begin", "0", "--end", str(end),
           "--seed", str(seed), "--time-to-teleport", "300", "--no-step-log", "true", "--no-warnings", "true", "--step-length", "1",
           "--tripinfo-output", str(WORK / f"tripinfo_{tag}_{win}.xml"), "--statistic-output", str(WORK / f"stats_{tag}_{win}.xml"),
           "--queue-output", str(WORK / f"queue_{tag}_{win}.xml"), "--queue-output.aggregation", "3600", "--queue-output.percentile", "95",
           "--scale", str(scale)] + (extra or [])
    traci.start(cmd, label=f"{tag}_{win}")
    p = params or Params(bus_switch=bus_priority)
    p.bus_switch = bus_priority and p.bus_switch
    tm = TlsMap()
    ctl_ids = [t for t in tm.ids if (only_tls is None or t in only_tls)]
    if adaptive and static and not greenwave:
        to_static(tm, ctl_ids)   # só os controlados; static=False: sobrepõe comandos à lógica actuated original
    ctrls = {t: Controller(Params(**p.__dict__)) for t in tm.ids}
    buses: set[str] = set()
    n_dep = 0
    served: set = set()
    last_red: dict = {}
    gw = None
    if greenwave:
        from . import greenwave as G
        corr = G.select_corridor(str(SIM / net))
        G.save_corridor(corr)
        gw = G.GreenWave(tm, corr, mode="fixed" if greenwave == "fixed" else "wave", seed=seed)
    counts = {"extend": 0, "switch": 0, "hold": 0}
    t0 = time.time()
    step = 0
    limit = min(end, max_sim_s) if max_sim_s else end   # TraCI ignora --end: o laço precisa parar em `end`, como o As-Is
    while traci.simulation.getMinExpectedNumber() > 0 and step < limit:
        traci.simulationStep()
        step += 1
        now = traci.simulation.getTime()
        for v in traci.simulation.getDepartedIDList():
            n_dep += 1
            # ablação: com fake_bus_every=N, 1 em cada N veículos NÃO-ônibus recebe prioridade como se fosse ônibus
            if traci.vehicle.getTypeID(v) == "bus" or (fake_bus_every and traci.vehicle.getTypeID(v) != "bus" and n_dep % fake_bus_every == 0):
                buses.add(v)
        for v in traci.simulation.getArrivedIDList():
            buses.discard(v)
        if gw is not None and gw.mode == "wave" and step % G.UPDATE_S == 0:
            gw.update(now)
        if adaptive and step % int(p.step) == 0:
            for t in ctl_ids:
                s = measure(tm, t, buses, served=served, last_red=last_red)
                a, secs = bridge.exchange(t, s, now) if bridge else ctrls[t].decide(s)
                counts[a] += 1
                if a == "switch":
                    served.update((b, t) for b in last_red.get(t, []))
                if a != "hold":
                    apply(t, a, secs, now)
    traci.close()
    return {"tag": tag, "window": win, "steps": step, "n_tls": len(tm.ids), "controlled": len(ctl_ids), "decisions": counts, "wall_s": round(time.time() - t0, 1)}
