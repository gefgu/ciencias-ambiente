"""Ônibus REAIS da URBS no SUMO: viagens do GPS (src/m1/urbs_real) -> map-matching na rede -> rotas com horário real.

Cada viagem observada (quinta-feira 12/11/2026) vira um <vehicle type="bus"> que parte no instante real (deslocado para a hora de demanda).
Os ônibus do sorteio provisório (4% da frota) saem das rotas; os reais entram no lugar.
"""
from __future__ import annotations
import json
import numpy as np, pandas as pd, sumolib
from sumolib import route as sroute
from src.m1.geo import PROC
from .common import SIM, WORK

HOUR0 = {"am": 7, "pm": 17}   # hora do dia simulada (mesma que define o vph de pico)


def match(win: str, delta: float = 30.0) -> pd.DataFrame:
    net = sumolib.net.readNet(str(SIM / "net.net.xml"))
    p = pd.read_parquet(PROC / "urbs_pings_trips.parquet")
    t = pd.read_parquet(PROC / "urbs_trips.parquet")
    h = HOUR0[win]
    t = t[(t.t0.dt.hour == h)]
    rows = []
    for tid, row in t.iterrows():
        g = p[p.trip == tid].sort_values("t")
        pts = [net.convertLonLat2XY(lo, la) for lo, la in zip(g.lon, g.lat)]
        pts = [q for q in pts if -50 <= q[0] <= 4400 and -50 <= q[1] <= 4550]
        if len(pts) < 6:
            continue
        try:
            edges = sroute.mapTrace(pts, net, delta, fillGaps=300, vClass="bus")
        except Exception:
            continue
        if not edges or len(edges) < 3:
            continue
        ids = [e.getID() for e in edges]
        rows.append((tid, row.linha, row.veic, (row.t0 - row.t0.normalize()).total_seconds() - h * 3600, " ".join(ids), sum(e.getLength() for e in edges)))
    return pd.DataFrame(rows, columns=["trip", "linha", "veic", "depart", "edges", "len_m"])


def write(win: str) -> dict:
    df = match(win)
    df = df[(df.depart >= 0) & (df.depart < 3600)].sort_values("depart")
    out = ['<routes>']
    for i, r in enumerate(df.itertuples()):
        out.append(f'  <vehicle id="rb{i}" type="bus" depart="{r.depart:.1f}" departLane="best" departSpeed="0"><route edges="{r.edges}"/></vehicle>')
    out.append("</routes>")
    raw = WORK / f"realbus_raw_{win}.rou.xml"
    raw.write_text("\n".join(out))
    from .common import run
    import re
    fin = SIM / f"routes_realbus_{win}.rou.xml"
    p = run(["duarouter", "-n", SIM / "net.net.xml", "--route-files", raw, "-o", fin, "--repair", "true", "--ignore-errors", "true", "--no-warnings", "true",
             "--no-step-log", "true", "--additional-files", SIM / "vtypes.add.xml"])
    assert fin.exists(), p.stderr[-400:]
    fin.write_text(re.sub(r"<vType [^>]*?(?:/>|>.*?</vType>)", "", fin.read_text(), flags=re.S))
    n_ok = fin.read_text().count("<vehicle ")
    df.to_csv(PROC / f"realbus_{win}.csv", index=False)
    # rotas sem os ônibus do sorteio provisório
    src = (SIM / f"routes_asis_{win}.rou.xml").read_text().splitlines()
    keep, skip = [], 0
    for ln in src:
        if 'type="bus"' in ln:
            continue
        keep.append(ln)
    (SIM / f"routes_nobus_{win}.rou.xml").write_text("\n".join(keep))
    return {"win": win, "buses": n_ok, "matched": len(df), "lines": int(df.linha.nunique()), "mean_len_m": float(df.len_m.mean())}


if __name__ == "__main__":
    print([write(w) for w in ("am", "pm")])
