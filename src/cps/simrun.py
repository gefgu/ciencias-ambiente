"""Executa o SUMO (As-Is) e extrai fluxos por aresta, emissões e estatísticas de viagem."""
from __future__ import annotations
import os
import pandas as pd
import xml.etree.ElementTree as ET
from .common import SIM, WORK, run

END = 5400  # 1 h de demanda + 30 min para escoar


def write_additional(win: str, tag: str = "asis", end: int = END):
    """edgeData cobre a simulação inteira (0–end): emissões e distância percorrida no MESMO período."""
    WORK.mkdir(exist_ok=True)
    f = SIM / f"detectors_{tag}_{win}.add.xml"
    f.write_text(f'''<additional>
  <edgeData id="flow" file="work/edge_flow_{tag}_{win}.xml" begin="0" end="{end}" excludeEmpty="true"/>
  <edgeData id="emi" type="emissions" file="work/edge_emi_{tag}_{win}.xml" begin="0" end="{end}" excludeEmpty="true"/>
</additional>''')
    return f


def write_config(win: str, routes, tag: str = "asis", seed: int = 1, net: str = "net.net.xml", end: int = END):
    """sumocfg com caminhos RELATIVOS (portável): sim/<tag>_<win>.sumocfg."""
    rel = os.path.relpath(routes, SIM)
    cfg = SIM / f"{tag}_{win}.sumocfg"
    cfg.write_text(f'''<configuration>
  <input><net-file value="{net}"/><route-files value="{rel}"/><additional-files value="vtypes.add.xml,detectors_{tag}_{win}.add.xml"/></input>
  <time><begin value="0"/><end value="{end}"/><step-length value="1"/></time>
  <processing><time-to-teleport value="300"/></processing>
  <random_number><seed value="{seed}"/></random_number>
  <output><tripinfo-output value="work/tripinfo_{tag}_{win}.xml"/><statistic-output value="work/stats_{tag}_{win}.xml"/></output>
  <report><no-step-log value="true"/><no-warnings value="true"/></report>
</configuration>''')
    return cfg


def simulate(win: str, routes=None, seed: int = 1, tag: str = "asis", end: int = END) -> dict:
    routes = routes or WORK / f"routes_{win}.rou.xml"
    write_additional(win, tag, end)
    cfg = write_config(win, routes, tag, seed, end=end)
    p = run(["sumo", "-c", cfg])
    return {"rc": p.returncode, "err": p.stderr[-300:]}


def read_flow(win: str, tag: str = "asis") -> pd.DataFrame:
    root = ET.parse(WORK / f"edge_flow_{tag}_{win}.xml").getroot()
    return pd.DataFrame([(e.get("id"), float(e.get("entered", 0))) for e in root.iter("edge")], columns=["edge", "sim_vph"])


def geh(m: float, c: float) -> float:
    return (2 * (m - c) ** 2 / (m + c)) ** 0.5 if (m + c) > 0 else 0.0
