"""Avaliação As-Is × To-Be (M4): réplicas com sementes diferentes, métricas, ruído e intervalos de confiança.

As-Is e To-Be usam a MESMA rede, as MESMAS rotas e as MESMAS sementes (pareamento por semente).
Totais por janela usam só a hora de demanda (edgeData 0–3600 s) × k; atrasos vêm dos veículos concluídos (viés de sobrevivência, reportado).
"""
from __future__ import annotations
import json, math, sys
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from scipy import stats as st
from .controllers import Params
from .common import OUT, SIM, WORK, window_scale
from src.m1 import noise
from src.m1.traffic import PH

SCENARIOS = {  # nome: argumentos de tobe.run
    "asis": dict(adaptive=False),                                                                                    # actuated padrão do netconvert
    "tobe_pi": dict(adaptive=True, static=True, bus_priority=True, params=Params(step=10.0)),                       # PI completo sobre programas fixos
    "tobe": dict(adaptive=True, static=False, bus_priority=True, params=Params(bus_only=True)),                     # actuated + prioridade ao ônibus (avança o ciclo)
    "tobe_fake": dict(adaptive=True, static=False, bus_priority=True, params=Params(bus_only=True), fake_bus_every=30),  # ablação: regra em 1/30 dos veículos que não são ônibus
    "tobe_bus2": dict(adaptive=True, static=False, bus_priority=True, params=Params(bus_only=True, bus_targeted=True)),  # prioridade condicional (próxima fase serve o ônibus)
    "tobe_gw": dict(adaptive=False, greenwave=True),                                                                # onda verde adaptativa na Rua Mariano Torres
    "tobe_fixed90": dict(adaptive=False, greenwave="fixed"),                                                        # CONTROLE da onda: mesmos programas fixos de 90 s, defasagens aleatórias
}
SEEDS = [1, 2, 3, 4, 5]
SWEEP_SCALES = [0.5, 0.6, 0.7, 0.85]
SWEEP_SCENS = ["asis", "tobe", "tobe_bus2"]
METRICS = ["delay_s", "speed_kmh", "finished", "inserted", "teleports", "bus_delay_s", "q_p95_m", "q_max_mean_m", "CO2_t_window", "NOx_kg_window",
           "CO_kg_window", "PMx_kg_window", "CO2_g_per_vkm", "Leq_cortn_dba", "Leq_harm_dba", "corridor_speed_kmh", "corridor_speed_fwd_kmh", "corridor_speed_rev_kmh",
           "corridor_wait_s", "veh_km"]


def _one(args):
    from . import tobe
    scen, win, seed, scale, tag = args
    return tobe.run(win, tag=tag, seed=seed, scale=scale, **SCENARIOS[scen])


def _save_decisions(infos):
    """Guarda quantas decisões de controle (hold/extend/switch) cada rodada tomou: sem isso 'sem efeito' não se distingue de 'a regra quase não disparou'."""
    f = OUT / "m4_decisions.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    for i in infos:
        d[f'{i["tag"]}_{i["window"]}'] = i["decisions"]
    f.write_text(json.dumps(d, indent=1))


def run_all(wins=("am", "pm"), scens=tuple(SCENARIOS), seeds=SEEDS, workers=10):
    jobs = [(s, w, k, 1.0, f"{s}_s{k}") for w in wins for s in scens for k in seeds]
    with ProcessPoolExecutor(workers) as ex:
        out = list(ex.map(_one, jobs))
    _save_decisions(out)
    return out


def run_sweep(workers=10, seeds=(1, 2, 3), scales=None):
    jobs = [(s, "am", k, sc, f"sw{sc}_{s}_s{k}") for sc in (scales or SWEEP_SCALES) for s in SWEEP_SCENS for k in seeds]
    with ProcessPoolExecutor(workers) as ex:
        out = list(ex.map(_one, jobs))
    _save_decisions(out)
    return out


def _edges(path, tag="edge"):
    return [{k: float(v) for k, v in x.attrib.items() if k != "id"} | {"id": x.get("id")} for x in ET.parse(path).iter(tag)]


def _egy(levels):
    """Média energética de níveis em dB."""
    v = [x for x in levels if x == x]
    return 10 * math.log10(sum(10 ** (x / 10) for x in v) / len(v)) if v else float("nan")


def metrics(tag: str, win: str) -> dict:
    ti = pd.DataFrame([{k: (float(v) if k != "vType" else v) for k, v in x.attrib.items() if k in ("duration", "timeLoss", "waitingTime", "routeLength", "vType")}
                       for x in ET.parse(WORK / f"tripinfo_{tag}_{win}.xml").iter("tripinfo")])
    em = pd.DataFrame(_edges(WORK / f"edge_emi1h_{tag}_{win}.xml"))
    fl = pd.DataFrame(_edges(WORK / f"edge_flow1h_{tag}_{win}.xml"))
    dist_m = float((fl.speed * fl.sampledSeconds).sum())          # veículos-km na hora de demanda (mesmo período das emissões)
    root = ET.parse(WORK / f"stats_{tag}_{win}.xml").getroot()
    v = root.find("vehicles").attrib
    bus = ti[ti.vType == "bus"]
    km = dist_m / 1000
    k = window_scale(win, pd.read_csv(PH / "hourly_profile.csv").fracao_vpd.tolist())
    q = pd.DataFrame(_edges(WORK / f"queue_{tag}_{win}.xml")) if (WORK / f"queue_{tag}_{win}.xml").exists() else pd.DataFrame()
    q95 = float((q.samples * q.percentileQueueLengthInMeters).sum() / q.samples.sum()) if len(q) else float("nan")
    qmax = float(q.maxQueueLengthInMeters.mean()) if len(q) else float("nan")
    out = {"inserted": int(v["inserted"]), "finished": len(ti), "veh_km": km, "delay_s": ti.timeLoss.mean(), "speed_kmh": dist_m / fl.sampledSeconds.sum() * 3.6,
           "bus_delay_s": bus.timeLoss.mean(), "teleports": int(root.find("teleports").attrib["total"]), "q_p95_m": q95, "q_max_mean_m": qmax,
           "CO2_t_window": em.CO2_abs.sum() / 1e9 * k, "NOx_kg_window": em.NOx_abs.sum() / 1e6 * k, "CO_kg_window": em.CO_abs.sum() / 1e6 * k,
           "PMx_kg_window": em.PMx_abs.sum() / 1e6 * k, "CO2_g_per_vkm": em.CO2_abs.sum() / 1000 / km}
    out.update(noise_levels(tag, win))
    cj = SIM / "corridor_greenwave.json"
    if cj.exists():
        ce = set(json.loads(cj.read_text())["edges"]); c = fl[fl.id.isin(ce)]
        dirs = json.loads(cj.read_text()).get("dir", {})
        sp = lambda d: float((d.speed * d.sampledSeconds).sum() / d.sampledSeconds.sum() * 3.6) if len(d) and d.sampledSeconds.sum() else float("nan")
        out["corridor_speed_kmh"] = sp(c)
        out["corridor_speed_fwd_kmh"] = sp(c[c.id.map(lambda e: dirs.get(e, 1)) == 1])   # sentido favorecido pela onda
        out["corridor_speed_rev_kmh"] = sp(c[c.id.map(lambda e: dirs.get(e, 1)) == -1])
        out["corridor_wait_s"] = float(c.waitingTime.sum() / max(c.left.sum(), 1)) if len(c) else float("nan")
    return out


def noise_levels(tag: str, win: str, d_m: float = 10.0, v_floor: float = 20.0) -> dict:
    """Leq nos pontos monitorados: (a) CoRTN a 10 m com vazão HORÁRIA (`entered` de 0–3600 s) e piso de velocidade de 20 km/h (limite do método);
    (b) harmonoise do SUMO (ruído de rolamento + propulsão, válido em baixa velocidade). Em ambos, aproximações somadas e pontos
    combinados por média ENERGÉTICA (não aritmética) de dB."""
    from .vtypes import mix
    cal = pd.read_csv(OUT / f"m2_geh_{win}.csv")
    fl = {e["id"]: e for e in _edges(WORK / f"edge_flow1h_{tag}_{win}.xml")}
    nz = {e["id"]: e for e in _edges(WORK / f"edge_noise1h_{tag}_{win}.xml")}
    m = mix(); heavy = 100 * (m["bus"] + m["truck"])
    cort, harm = [], []
    for pid, g in cal.groupby("point_id"):
        ec = eh = 0.0
        for edge in g.edge:
            f = fl.get(edge)
            if f and f.get("entered", 0) > 1:
                ec += 10 ** (noise.leq_from_l10(noise.cortn_l10_1h(f["entered"], max(f["speed"] * 3.6, v_floor), heavy, d_m)) / 10)
            if edge in nz and nz[edge].get("noise", 0) > 0:
                eh += 10 ** (nz[edge]["noise"] / 10)
        cort.append(10 * math.log10(ec) if ec > 0 else float("nan")); harm.append(10 * math.log10(eh) if eh > 0 else float("nan"))
    return {"Leq_cortn_dba": _egy(cort), "Leq_harm_dba": _egy(harm)}


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    return None if isinstance(o, float) and math.isnan(o) else o


def _stats(x, base=None):
    n = len(x)
    ci = st.t.ppf(.975, n - 1) * x.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    o = {"mean": float(x.mean()), "ci95": float(ci), "n": int(n)}
    if base is not None and n > 2:
        b = base.reindex(x.index)
        diff = (x - b).dropna()
        o["delta_mean"] = float(diff.mean())
        o["delta_pct"] = float(100 * diff.mean() / b.mean()) if b.mean() else float("nan")
        o["p_paired"] = float(st.ttest_rel(x, b, nan_policy="omit").pvalue)
    return o


def summarize(wins=("am", "pm"), scens=tuple(SCENARIOS), seeds=SEEDS) -> dict:
    rows, missing = [], []
    for w in wins:
        for s in scens:
            for k in seeds:
                try:
                    m = metrics(f"{s}_s{k}", w)
                except Exception:
                    missing.append(f"{s}_s{k}_{w}"); continue
                rows.append({**m, "scenario": s, "window": w, "seed": k})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "m4_runs.csv", index=False)
    res = {"_missing_runs": missing}
    for w in wins:
        res[w] = {}
        base = df[(df.window == w) & (df.scenario == "asis")].set_index("seed")
        for s in scens:
            cur = df[(df.window == w) & (df.scenario == s)].set_index("seed")
            if cur.empty:
                continue
            res[w][s] = {c: _stats(cur[c], None if s == "asis" else base[c]) for c in METRICS if c in cur}
    res["_primary"], res["_sign"] = primary_endpoints(df)
    res["_wave_vs_fixed"] = wave_vs_fixed(df)
    (OUT / "m4_results.json").write_text(json.dumps(_clean(res), indent=1))
    return res


def wave_vs_fixed(df: pd.DataFrame) -> dict:
    """Efeito da COORDENAÇÃO = onda verde menos o controle de programas fixos de 90 s com defasagens aleatórias (pareado por semente)."""
    out = {}
    for w in ("am", "pm"):
        a = df[(df.window == w) & (df.scenario == "tobe_gw")].set_index("seed")
        b = df[(df.window == w) & (df.scenario == "tobe_fixed90")].set_index("seed")
        if a.empty or b.empty:
            continue
        out[w] = {}
        for m in ["speed_kmh", "finished", "inserted", "teleports", "q_p95_m", "delay_s", "corridor_speed_fwd_kmh", "corridor_speed_rev_kmh", "Leq_harm_dba", "CO2_g_per_vkm"]:
            if m in a and m in b:
                x, y = a[m], b[m].reindex(a.index)
                out[w][m] = {"diff": float((x - y).mean()), "p": float(st.ttest_rel(x, y).pvalue), "gw": float(x.mean()), "fixed": float(y.mean())}
    return out


PRIMARY = ["speed_kmh", "finished", "CO2_g_per_vkm"]   # desfechos primários declarados a priori


def primary_endpoints(df: pd.DataFrame):
    """Testes t pareados só nos desfechos primários, com correção de Benjamini–Hochberg (FDR) sobre todos eles; e teste do sinal da velocidade."""
    rows = []
    for w in ("am", "pm"):
        base = df[(df.window == w) & (df.scenario == "asis")].set_index("seed")
        for s in [x for x in SCENARIOS if x != "asis"]:
            cur = df[(df.window == w) & (df.scenario == s)].set_index("seed")
            if cur.empty:
                continue
            for m in PRIMARY:
                b = base[m].reindex(cur.index)
                rows.append({"window": w, "scenario": s, "metric": m, "delta_pct": float(100 * (cur[m] - b).mean() / b.mean()),
                             "p": float(st.ttest_rel(cur[m], b).pvalue)})
    q = st.false_discovery_control([r["p"] for r in rows], method="bh")
    for r, qq in zip(rows, q):
        r["q_bh"] = float(qq)
    sign = {}
    for s in [x for x in SCENARIOS if x != "asis"]:
        d = []
        for w in ("am", "pm"):
            b = df[(df.window == w) & (df.scenario == "asis")].set_index("seed").speed_kmh
            c = df[(df.window == w) & (df.scenario == s)].set_index("seed").speed_kmh
            d += list((c - b.reindex(c.index)).dropna())
        if d:
            n_neg = int(sum(x < 0 for x in d))
            sign[s] = {"n_pairs": len(d), "n_slower": n_neg, "p_sign": float(st.binomtest(n_neg, len(d), 0.5).pvalue)}
    return rows, sign


def summarize_sweep() -> dict:
    rows = []
    for sc in SWEEP_SCALES:
        for s in SWEEP_SCENS:
            for k in (1, 2, 3):
                try:
                    rows.append({**metrics(f"sw{sc}_{s}_s{k}", "am"), "scale": sc, "scenario": s, "seed": k})
                except Exception:
                    pass
    df = pd.DataFrame(rows)
    # escala 1,0 = as réplicas principais (sementes 1–3)
    full = pd.read_csv(OUT / "m4_runs.csv")
    full = full[(full.window == "am") & full.scenario.isin(SWEEP_SCENS) & full.seed.isin([1, 2, 3])].assign(scale=1.0)
    df = pd.concat([df, full[df.columns.intersection(full.columns)]], ignore_index=True)
    df.to_csv(OUT / "m4_sweep_runs.csv", index=False)
    res = {}
    for sc in sorted(df.scale.unique()):
        res[str(sc)] = {}
        for s in SWEEP_SCENS:
            g = df[(df.scale == sc) & (df.scenario == s)].set_index("seed")
            if len(g):
                res[str(sc)][s] = {c: _stats(g[c]) for c in ("speed_kmh", "delay_s", "finished", "teleports", "q_p95_m", "CO2_g_per_vkm", "CO2_t_window") if c in g}
    (OUT / "m4_sweep.json").write_text(json.dumps(_clean(res), indent=1))
    return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("run", "all"):
        print(len(run_all()))
    if cmd in ("sweep", "all"):
        print(len(run_sweep()))
    if cmd in ("summary", "all"):
        summarize(); summarize_sweep(); print("ok")
