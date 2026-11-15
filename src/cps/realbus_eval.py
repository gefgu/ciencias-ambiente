"""Prioridade ao ônibus com a demanda de ônibus REAL (GPS da URBS, 12/11/2026): As-Is × prioridade, pareado por semente.

Também valida a simulação com os tempos de viagem observados dos MESMOS ônibus (GPS × SUMO)."""
from __future__ import annotations
import json
import xml.etree.ElementTree as ET
import numpy as np, pandas as pd
from scipy import stats as st
from . import evaluate as ev
from .common import OUT, SIM, WORK

SC = ["asis_rb", "tobe_rb", "tobe_bus2_rb"]


def run():
    out = ev.run_all(scens=tuple(SC))
    return len(out)


def bus_table(tag: str, win: str) -> pd.DataFrame:
    ti = pd.DataFrame([x.attrib for x in ET.parse(WORK / f"tripinfo_{tag}_{win}.xml").iter("tripinfo")])
    ti = ti[ti.id.str.startswith("rb")].copy()
    for c in ("duration", "routeLength", "timeLoss", "waitingTime"):
        ti[c] = ti[c].astype(float)
    ti["i"] = ti.id.str[2:].astype(int)
    return ti


def validate(win: str = "am", seeds=range(1, 6)) -> dict:
    """Tempo de viagem real × simulado dos mesmos ônibus (viagem dentro da área). O real inclui paradas de embarque (não modeladas)."""
    real = pd.read_csv(OUT / f"realbus_{win}.csv").reset_index().rename(columns={"index": "i"})
    t = pd.read_parquet(OUT / "urbs_trips.parquet")
    real = real.merge(t[["t0", "t1", "dist_m"]], left_on="trip", right_index=True)
    real["dur_real"] = (real.t1 - real.t0).dt.total_seconds()
    rows = []
    for k in seeds:
        b = bus_table(f"asis_rb_s{k}", win).merge(real[["i", "dur_real", "dist_m", "len_m"]], on="i")
        b = b[(b.dur_real > 60) & (b.duration > 0)]
        rows.append({"seed": k, "n": len(b), "sim_kmh": float((b.routeLength.sum() / b.duration.sum()) * 3.6), "real_kmh": float(b.dist_m.sum() / b.dur_real.sum() * 3.6),
                     "sim_dur_s": float(b.duration.median()), "real_dur_s": float(b.dur_real.median()), "spearman": float(st.spearmanr(b.duration, b.dur_real).statistic)})
    return pd.DataFrame(rows).mean(numeric_only=True).round(3).to_dict()


def summarize(seeds=range(1, 6)) -> dict:
    res = {"n_real_buses": {}, "validation": {}}
    rows = []
    for w in ("am", "pm"):
        res["n_real_buses"][w] = int(open(SIM / f"routes_realbus_{w}.rou.xml").read().count("<vehicle "))
        for s in SC:
            for k in seeds:
                m = ev.metrics(f"{s}_s{k}", w)
                b = bus_table(f"{s}_s{k}", w)
                m.update({"bus_n": len(b), "bus_dur_s": b.duration.mean(), "bus_speed_kmh": b.routeLength.sum() / b.duration.sum() * 3.6, "bus_wait_s": b.waitingTime.mean()})
                rows.append({**m, "scenario": s, "window": w, "seed": k})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "m4_realbus_runs.csv", index=False)
    dec = json.loads((OUT / "m4_decisions.json").read_text())
    for w in ("am", "pm"):
        res[w] = {}
        base = df[(df.window == w) & (df.scenario == "asis_rb")].set_index("seed")
        for s in SC:
            cur = df[(df.window == w) & (df.scenario == s)].set_index("seed")
            d = {}
            for c in ("bus_speed_kmh", "bus_dur_s", "bus_delay_s", "speed_kmh", "delay_s", "finished", "teleports", "CO2_g_per_vkm", "q_p95_m"):
                x = cur[c]; d[c] = {"mean": float(x.mean()), "sd": float(x.std())}
                if s != "asis_rb":
                    diff = x - base[c].reindex(x.index)
                    d[c].update({"diff": float(diff.mean()), "p": float(st.ttest_rel(x, base[c].reindex(x.index)).pvalue), "n_better": int((diff > 0).sum()) if c in ("bus_speed_kmh", "speed_kmh", "finished") else int((diff < 0).sum())})
            d["decisions"] = dec.get(f"{s}_s1_{w}", {})
            res[w][s] = d
        res["validation"][w] = validate(w, seeds)
    (OUT / "m4_realbus.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    import sys
    if "run" in sys.argv[1:] or len(sys.argv) == 1:
        print(run())
    print(json.dumps(summarize(), indent=1, default=float))
