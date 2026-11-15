"""Onda verde adaptativa (M3/M4): ciclo comum e defasagens ao longo de um eixo (Rua Mariano Torres), com reajuste periódico pela velocidade de progressão.

Premissas (sem dados reais de semáforos): ciclo comum C; as durações de verde de cada semáforo do eixo são reescaladas proporcionalmente
para somar C (amarelos mantidos); a "fase principal" é a que serve mais ligações das vias do eixo. Defasagem ideal do semáforo i:
    off_i = (s_i / v_prog) mod C,   s_i = posição ao longo do eixo (m), v_prog = velocidade de progressão (m/s).
Adaptação: a cada UPDATE_S segundos, v_prog é reestimada pela velocidade média das arestas do eixo (limitada) e a defasagem de cada
semáforo é deslocada, no máximo MAX_SHIFT s por atualização, ajustando a duração restante da fase atual.
"""
from __future__ import annotations
import json, math
import numpy as np
import sumolib
import traci
from .common import SIM, WORK

CORRIDOR = "Rua Mariano Torres"   # Floriano (eixo do manual) não recebeu nenhum semáforo na inferência do netconvert; Mariano Torres (via do contorno) recebeu 34 aproximações semaforizadas
CYCLE = 90.0
UPDATE_S = 300
MAX_SHIFT = 8.0
V_MIN, V_MAX = 5.5, 13.9   # m/s


def select_corridor(net_file: str = str(SIM / "net.net.xml"), name: str = CORRIDOR) -> dict:
    """Semáforos (e arestas) do eixo, ordenados ao longo dele (projeção no eixo principal)."""
    net = sumolib.net.readNet(net_file)
    edges = [e for e in net.getEdges() if e.getName() == name and not e.getID().startswith(":")]
    pts = np.array([e.getShape()[0] for e in edges])
    if len(pts) < 2:
        return {"tls": [], "edges": [], "pos": []}
    c = pts.mean(0); u, s, vt = np.linalg.svd(pts - c); axis = vt[0]
    tls = {}
    for e in edges:
        node = e.getToNode()
        if node.getType().startswith("traffic") and node.getID() in {t.getID() for t in net.getTrafficLights()}:
            x, y = node.getCoord()
            tls[node.getID()] = float(np.dot(np.array([x, y]) - c, axis))
    order = sorted(tls, key=tls.get)
    pos = [tls[t] - tls[order[0]] for t in order]
    return {"tls": order, "pos": pos, "edges": [e.getID() for e in edges]}


def ideal_offsets(pos: list[float], v_prog: float, cycle: float = CYCLE) -> list[float]:
    return [(p / v_prog) % cycle for p in pos]


def wrap(d: float, cycle: float = CYCLE) -> float:
    """Diferença de defasagem no intervalo (−C/2, C/2]."""
    return (d + cycle / 2) % cycle - cycle / 2


def scale_durations(durs: list[float], is_green: list[bool], cycle: float = CYCLE) -> list[float]:
    """Reescala só os verdes para o ciclo somar `cycle` (amarelos/vermelhos de limpeza fixos). Verde mínimo de 5 s."""
    fixed = sum(d for d, g in zip(durs, is_green) if not g)
    gsum = sum(d for d, g in zip(durs, is_green) if g)
    f = max(cycle - fixed, 5.0 * sum(is_green)) / gsum if gsum else 1.0
    return [max(d * f, 5.0) if g else d for d, g in zip(durs, is_green)]


class GreenWave:
    def __init__(self, tm, corridor: dict, cycle: float = CYCLE, v0: float = 11.1):
        self.tm, self.cyc = tm, cycle
        keep = [(t, p) for t, p in zip(corridor["tls"], corridor["pos"]) if t in tm.ids]
        self.ids = [t for t, _ in keep]; self.pos = [p for _, p in keep]
        self.edges = corridor["edges"]
        self.main: dict[str, int] = {}
        self.durs: dict[str, list[float]] = {}
        self.cur_off: dict[str, float] = {}
        self.v = v0
        offs = ideal_offsets(self.pos, v0, cycle)
        names = set(self.edges)
        for t, off in zip(self.ids, offs):
            lg = tm.phases[t]
            greens = tm.is_green[t]
            links = traci.trafficlight.getControlledLinks(t)
            score = []
            for k, ph in enumerate(lg.phases):
                n = sum(1 for i, c in enumerate(ph.state) if c in "Gg" and i < len(links) and links[i] and traci.lane.getEdgeID(links[i][0][0]) in names)
                score.append(n if greens[k] else -1)
            self.main[t] = int(np.argmax(score))
            d = scale_durations([p.duration if p.duration > 0 else 10 for p in lg.phases], greens, cycle)
            self.durs[t] = d
            phases = [traci.trafficlight.Phase(dd, p.state) for dd, p in zip(d, lg.phases)]
            traci.trafficlight.setProgramLogic(t, traci.trafficlight.Logic("gw", 0, 0, phases=phases))
            self._start(t, off)
            self.cur_off[t] = off

    def _start(self, t: str, off: float):
        d = self.durs[t]; k_main = self.main[t]
        s_main = sum(d[:k_main])
        pos0 = (s_main - off) % self.cyc
        acc = 0.0
        for k, dd in enumerate(d):
            if acc <= pos0 < acc + dd:
                traci.trafficlight.setPhase(t, k)
                traci.trafficlight.setPhaseDuration(t, dd - (pos0 - acc))
                return
            acc += dd

    def update(self, now: float):
        """Reajuste adaptativo: reestima v_prog (média espacial no eixo) e desloca as defasagens em até MAX_SHIFT s."""
        sp = [traci.edge.getLastStepMeanSpeed(e) for e in self.edges]
        sp = [s for s in sp if s > 0.1]
        if sp:
            self.v = float(np.clip(np.mean(sp), V_MIN, V_MAX))
        for t, off_new in zip(self.ids, ideal_offsets(self.pos, self.v, self.cyc)):
            d = wrap(off_new - self.cur_off[t], self.cyc)
            d = max(-MAX_SHIFT, min(MAX_SHIFT, d))
            if abs(d) < 1:
                continue
            rem = traci.trafficlight.getNextSwitch(t) - now
            if rem + d >= 3:
                traci.trafficlight.setPhaseDuration(t, rem + d)
                self.cur_off[t] = (self.cur_off[t] + d) % self.cyc


def save_corridor(c: dict):
    (WORK).mkdir(exist_ok=True)
    (SIM / "corridor_greenwave.json").write_text(json.dumps(c))
