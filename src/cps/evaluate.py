"""Avaliação As-Is × To-Be (M4): réplicas com sementes diferentes, métricas, ruído (CoRTN) e intervalos de confiança.

Observação metodológica: As-Is e To-Be usam a MESMA rede, as MESMAS rotas e as MESMAS sementes (pareamento por semente).
"""
from __future__ import annotations
import json, math, sys
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from scipy import stats as st
from .controllers import Params
from .common import OUT, SIM, WORK, WINDOWS, window_scale
from src.m1 import noise
from src.m1.traffic import PH

SCENARIOS = {  # nome: argumentos de tobe.run
    "asis": dict(adaptive=False),                                                                                    # actuated padrão do netconvert
    "tobe_pi": dict(adaptive=True, static=True, bus_priority=True, params=Params(step=10.0)),                       # PI completo sobre programas fixos (resultado negativo no M3)
    "tobe": dict(adaptive=True, static=False, bus_priority=True, params=Params(bus_only=True)),                     # actuated + prioridade ao ônibus
    "tobe_fake": dict(adaptive=True, static=False, bus_priority=True, params=Params(bus_only=True), fake_bus_every=30),  # ablação: mesma regra aplicada a 1/30 dos veículos (não-ônibus)
}
SEEDS = [1, 2, 3, 4, 5]


def _one(args):
    from . import tobe
    scen, win, seed = args
    return tobe.run(win, tag=f"{scen}_s{seed}", seed=seed, **SCENARIOS[scen])


def run_all(wins=("am", "pm"), scens=tuple(SCENARIOS), seeds=SEEDS, workers=4):
    jobs = [(s, w, k) for w in wins for s in scens for k in seeds]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_one, jobs))


def metrics(tag: str, win: str) -> dict:
    ti = pd.DataFrame([{k: (float(v) if k != "vType" else v) for k, v in x.attrib.items() if k in ("duration", "timeLoss", "waitingTime", "routeLength", "vType")}
                       for x in ET.parse(WORK / f"tripinfo_{tag}_{win}.xml").iter("tripinfo")])
    em = pd.DataFrame([{k: float(v) for k, v in x.attrib.items() if k != "id"} for x in ET.parse(WORK / f"edge_emi_{tag}_{win}.xml").iter("edge")])
    fl = pd.DataFrame([{k: float(v) for k, v in x.attrib.items() if k != "id"} for x in ET.parse(WORK / f"edge_flow_{tag}_{win}.xml").iter("edge")])
    dist_m = float((fl.speed * fl.sampledSeconds).sum())   # veículos-km de todos os veículos, no mesmo período das emissões
    root = ET.parse(WORK / f"stats_{tag}_{win}.xml").getroot()
    v = root.find("vehicles").attrib
    tele = int(root.find("teleports").attrib["total"])
    bus = ti[ti.vType == "bus"]
    km = dist_m / 1000
    prof = pd.read_csv(PH / "hourly_profile.csv").fracao_vpd.tolist()
    k = window_scale(win, prof)
    return {"inserted": int(v["inserted"]), "finished": len(ti), "veh_km": km, "delay_s": ti.timeLoss.mean(), "wait_s": ti.waitingTime.mean(),
            "speed_kmh": dist_m / fl.sampledSeconds.sum() * 3.6, "bus_dur_s": bus.duration.mean(), "bus_delay_s": bus.timeLoss.mean(), "teleports": tele,
            "CO2_t_window": em.CO2_abs.sum() / 1e9 * k, "NOx_kg_window": em.NOx_abs.sum() / 1e6 * k, "CO_kg_window": em.CO_abs.sum() / 1e6 * k,
            "PMx_kg_window": em.PMx_abs.sum() / 1e6 * k, "CO2_g_per_vkm": em.CO2_abs.sum() / 1000 / km}


def noise_levels(tag: str, win: str, d_m: float = 10.0, v_floor: float = 20.0) -> dict[str, float]:
    """Leq por ponto (CoRTN a 10 m, energia somada sobre as arestas monitoradas). v piso 20 km/h = limite de validade do método."""
    cal = pd.read_csv(OUT / f"m2_geh_{win}.csv")
    root = ET.parse(WORK / f"edge_flow_{tag}_{win}.xml").getroot()
    fl = {e.get("id"): (float(e.get("entered", 0)), float(e.get("speed", 5))) for e in root.iter("edge")}
    from .vtypes import mix
    m = mix(); heavy = 100 * (m["bus"] + m["truck"])
    out = {}
    for pid, g in cal.groupby("point_id"):
        e = 0.0
        for edge in g.edge:
            q, v = fl.get(edge, (0.0, 5.0))
            if q > 1:
                e += 10 ** (noise.leq_from_l10(noise.cortn_l10_1h(q, max(v * 3.6, v_floor), heavy, d_m)) / 10)
        out[pid] = 10 * math.log10(e) if e > 0 else float("nan")
    return out


def summarize(wins=("am", "pm"), scens=tuple(SCENARIOS), seeds=SEEDS) -> dict:
    rows = []
    for w in wins:
        for s in scens:
            for k in seeds:
                tag = f"{s}_s{k}"
                try:
                    m = metrics(tag, w)
                except Exception as ex:  # execução ausente
                    continue
                nl = noise_levels(tag, w)
                m.update({"scenario": s, "window": w, "seed": k, "Leq_mean_dba": float(np.nanmean(list(nl.values())))})
                rows.append(m)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "m4_runs.csv", index=False)
    res = {}
    for w in wins:
        res[w] = {}
        base = df[(df.window == w) & (df.scenario == "asis")].set_index("seed")
        for s in scens:
            cur = df[(df.window == w) & (df.scenario == s)].set_index("seed")
            if cur.empty:
                continue
            out = {}
            for c in ["delay_s", "wait_s", "speed_kmh", "bus_dur_s", "bus_delay_s", "teleports", "CO2_t_window", "NOx_kg_window", "CO_kg_window", "PMx_kg_window", "CO2_g_per_vkm", "Leq_mean_dba", "inserted", "finished"]:
                x = cur[c]; n = len(x)
                ci = st.t.ppf(.975, n - 1) * x.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
                o = {"mean": float(x.mean()), "ci95": float(ci)}
                if s != "asis" and len(base) == n:
                    diff = (x - base[c].reindex(x.index)).dropna()
                    o["delta_mean"] = float(diff.mean())
                    o["delta_pct"] = float(100 * diff.mean() / base[c].mean()) if base[c].mean() else float("nan")
                    o["p_paired"] = float(st.ttest_rel(x, base[c].reindex(x.index)).pvalue) if n > 2 else float("nan")
                out[c] = o
            res[w][s] = out
    def _clean(o):  # NaN não é JSON válido
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        return None if isinstance(o, float) and math.isnan(o) else o
    (OUT / "m4_results.json").write_text(json.dumps(_clean(res), indent=1))
    return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("run", "all"):
        print(run_all())
    if cmd in ("summary", "all"):
        print(json.dumps(summarize(), indent=1)[:3000])
