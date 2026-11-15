"""Avaliação dos modos ativos (M3/M4): pedestres no Calçadão e ciclistas, com e sem as intervenções.

As-Is ativo : rede com pedestres/ciclovias, semáforos actuated padrão.
To-Be ativo: + faixas exclusivas de bicicleta nas vias de apoio + controle adaptativo com prioridade ao ônibus.
Demanda de pedestres e bicicletas PROVISÓRIA (ver active_modes.py).
"""
from __future__ import annotations
import json, math
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from scipy import stats as st
from . import active_modes
from .controllers import Params
from .common import OUT, SIM, WORK

SCEN = {  # nome: (rede, controle). Três cenários separam o efeito das faixas de bicicleta do efeito do controle
    "asis_act": ("net_active.net.xml", False),   # pedestres/ciclovias, actuated padrão
    "bike_only": ("net_tobe.net.xml", False),    # + faixas exclusivas de bicicleta, actuated padrão
    "tobe_act": ("net_tobe.net.xml", True),      # + prioridade ao ônibus sobre o actuated
}
SEEDS = [1, 2, 3]


def repaired_car_routes(win: str = "am") -> dict:
    """As variantes ativas não fundem arestas (mantêm todos os ids da base), mas as rotas do M2 têm 'saltos' onde a base fundiu trechos;
    o duarouter --repair preenche os saltos. Mesma demanda de carros nas duas variantes."""
    from .common import run
    out = WORK / f"routes_active_cars_{win}.rou.xml"
    p = run(["duarouter", "-n", SIM / "net_active.net.xml", "--route-files", SIM / f"routes_asis_{win}.rou.xml", "-o", out, "--repair", "true",
             "--ignore-errors", "true", "--no-warnings", "true", "--no-step-log", "true", "--additional-files", SIM / "vtypes.add.xml"])
    assert out.exists(), p.stderr[-400:]
    import re
    txt = re.sub(r"<vType [^>]*?(?:/>|>.*?</vType>)", "", out.read_text(), flags=re.S)  # tipos já vêm de vtypes.add.xml
    out.write_text(txt)
    n_in = open(SIM / f"routes_asis_{win}.rou.xml").read().count("<vehicle ")
    n_out = open(out).read().count("<vehicle ")
    (OUT / "m4_active_routes.json").write_text(json.dumps({"vehicles_in": n_in, "vehicles_out": n_out}))
    return {"in": n_in, "out": n_out}


def _job(a):
    scen, seed = a
    from . import tobe
    net, adaptive = SCEN[scen]
    src = WORK / "active_am.rou.xml"
    tag = f"{scen}_s{seed}"
    tobe.run("am", adaptive=adaptive, bus_priority=adaptive, static=False, params=Params(bus_only=True) if adaptive else None, tag=tag, seed=seed, net=net,
             routes=WORK / "routes_active_cars_am.rou.xml", extra_routes=str(src), extra=["--ignore-route-errors", "true"])  # descarta rotas inválidas na variante (contado em metrics)
    return metrics(tag)


def metrics(tag: str) -> dict:
    root = ET.parse(WORK / f"tripinfo_{tag}_am.xml").getroot()
    veh = pd.DataFrame([{"type": x.get("vType"), "dur": float(x.get("duration")), "loss": float(x.get("timeLoss")), "len": float(x.get("routeLength"))} for x in root.iter("tripinfo")])
    cars = veh[~veh.type.isin(["bike"])]
    bikes = veh[veh.type == "bike"]
    pers = []
    for p in root.iter("personinfo"):
        for w in p.iter("walk"):
            pers.append({"dur": float(w.get("duration", 0)), "loss": float(w.get("timeLoss", 0)), "len": float(w.get("routeLength", 0))})
    pers = pd.DataFrame(pers)
    return {"tag": tag, "cars": len(cars), "car_delay_s": cars.loss.mean(), "bikes": len(bikes), "bike_speed_kmh": float(bikes.len.sum() / bikes.dur.sum() * 3.6) if len(bikes) else np.nan,
            "bike_delay_s": bikes.loss.mean() if len(bikes) else np.nan, "persons": len(pers), "ped_timeloss_s": pers.loss.mean() if len(pers) else np.nan,
            "ped_speed_kmh": float(pers.len.sum() / pers.dur.sum() * 3.6) if len(pers) and pers.dur.sum() else np.nan}


def run(workers=9):
    repaired_car_routes("am")
    active_modes.build_demand(str(SIM / "net_active.net.xml"), "am")  # uma vez; as mesmas rotas valem nas duas variantes
    jobs = [(s, k) for s in SCEN for k in SEEDS]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_job, jobs))
    df = pd.DataFrame(rows)
    df["scenario"] = [j[0] for j in jobs]; df["seed"] = [j[1] for j in jobs]
    df.to_csv(OUT / "m4_active_runs.csv", index=False)
    res = {}
    for s in SCEN:
        g = df[df.scenario == s].drop(columns=["tag", "scenario", "seed"])
        res[s] = {c: {"mean": float(g[c].mean()), "ci95": float(st.t.ppf(.975, len(g) - 1) * g[c].std(ddof=1) / math.sqrt(len(g)))} for c in g.columns}
    res = {s: {c: {k: (None if v != v else v) for k, v in o.items()} for c, o in d.items()} for s, d in res.items()}  # NaN -> null
    (OUT / "m4_active.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
