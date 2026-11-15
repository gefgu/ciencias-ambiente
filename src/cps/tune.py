"""Sintonia do controlador PI (M3): busca em grade avaliada numa semente DIFERENTE das usadas na avaliação final (M4)."""
from __future__ import annotations
import json
from concurrent.futures import ProcessPoolExecutor
import xml.etree.ElementTree as ET
import pandas as pd
from .controllers import Params
from .common import OUT, WORK

TUNE_SEED = 11  # as réplicas do M4 usam 1–5
GRID = {
    "asis": dict(),  # referência sem controle adaptativo (programa actuated do netconvert)
    "base": dict(),
    "kp2": dict(kp=2.0),
    "theta2": dict(theta=2.0),
    "ki0": dict(ki=0.0),
    "min12": dict(min_green=12.0),
    "ext3": dict(extend=3.0),
    "max35": dict(max_green=35.0),
    "step10": dict(step=10.0),
    "null": dict(min_green=1e9, bus_switch=False),
    "extonly": dict(theta=1e9, bus_switch=False, kp=0.0, ki=0.0),
    "ov_full": dict(static=False),
    "ov_bus": dict(static=False, bus_only=True),
    "ov_theta3": dict(static=False, theta=3.0, min_green=10.0),
}


def _job(item):
    name, kw = item
    from . import tobe
    tag = f"tune_{name}"
    kw = dict(kw)
    static = kw.pop("static", True)
    info = tobe.run("am", params=Params(**kw), adaptive=(name != "asis"), bus_priority=True, tag=tag, seed=TUNE_SEED, static=static)
    flw = pd.DataFrame([{k: float(v) for k, v in x.attrib.items() if k != "id"} for x in ET.parse(WORK / f"edge_flow_{tag}_am.xml").iter("edge")])
    root = ET.parse(WORK / f"stats_{tag}_am.xml").getroot()
    ti = [float(x.get("timeLoss")) for x in ET.parse(WORK / f"tripinfo_{tag}_am.xml").iter("tripinfo")]
    return {"name": name, **kw, "speed_kmh": float((flw.speed * flw.sampledSeconds).sum() / flw.sampledSeconds.sum() * 3.6), "finished": len(ti), "delay_finished_s": sum(ti) / len(ti),
            "teleports": int(root.find("teleports").attrib["total"]), "depart_delay_s": float(root.find("vehicleTripStatistics").attrib["departDelay"])}


DESC = {"asis": "As-Is (actuated padrão, sem sobreposição)", "null": "Programas fixos, sem controle (controle nulo)", "extonly": "Fixo + só extensão de verde",
        "base": "PI padrão sobre programas fixos", "kp2": "PI, Kp=2", "theta2": "PI, θ=2", "ki0": "PI sem integral", "min12": "PI, verde mínimo 12 s", "ext3": "PI, extensão 3 s",
        "max35": "PI, verde máximo 35 s", "step10": "PI, amostragem 10 s", "ov_full": "PI sobreposto ao actuated", "ov_theta3": "PI sobreposto, θ=3, verde mín. 10 s",
        "ov_bus": "Actuated + só prioridade ao ônibus"}


def collect():
    """Reúne (a partir dos arquivos já gerados) todas as variantes testadas na semente de sintonia."""
    rows = []
    for name, desc in DESC.items():
        tag = f"tune_{name}"
        try:
            flw = pd.DataFrame([{k: float(v) for k, v in x.attrib.items() if k != "id"} for x in ET.parse(WORK / f"edge_flow_{tag}_am.xml").iter("edge")])
            root = ET.parse(WORK / f"stats_{tag}_am.xml").getroot()
            ti = [float(x.get("timeLoss")) for x in ET.parse(WORK / f"tripinfo_{tag}_am.xml").iter("tripinfo")]
        except Exception:
            continue
        rows.append({"name": name, "desc": desc, "speed_kmh": float((flw.speed * flw.sampledSeconds).sum() / flw.sampledSeconds.sum() * 3.6), "finished": len(ti),
                     "delay_finished_s": sum(ti) / len(ti), "teleports": int(root.find("teleports").attrib["total"]),
                     "depart_delay_s": float(root.find("vehicleTripStatistics").attrib["departDelay"])})
    df = pd.DataFrame(rows).sort_values("speed_kmh", ascending=False)
    df.to_csv(OUT / "m3_tuning.csv", index=False)
    return df


def run(workers=4):
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_job, GRID.items()))
    # baseline do As-Is na mesma semente
    return collect()


if __name__ == "__main__":
    print(run().to_string())
