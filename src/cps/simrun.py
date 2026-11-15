"""Executa o SUMO (As-Is) e extrai fluxos por aresta, emissões e estatísticas de viagem."""
from __future__ import annotations
import os
import pandas as pd
import xml.etree.ElementTree as ET
from .common import SIM, WORK, run

END = 5400  # 1 h de demanda + 30 min para escoar


def additional_xml(prefix: str, tag: str, win: str, end: int = END) -> str:
    """Saídas por aresta. `flow`/`emi` cobrem 0–end (calibração GEH e totais com escoamento); os arquivos *1h cobrem só a hora de demanda
    (0–3600 s) e são os usados nos totais por janela (o fator k estende UMA hora de demanda à janela), no vazão horária e no ruído harmonoise."""
    e = lambda i, kind, f, b, en: f'  <edgeData id="{i}"{kind} file="{prefix}{f}_{tag}_{win}.xml" begin="{b}" end="{en}" excludeEmpty="true"/>\n'
    return ("<additional>\n" + e("flow", "", "edge_flow", 0, end) + e("emi", ' type="emissions"', "edge_emi", 0, end)
            + e("flow1h", "", "edge_flow1h", 0, 3600) + e("emi1h", ' type="emissions"', "edge_emi1h", 0, 3600)
            + e("noise1h", ' type="harmonoise"', "edge_noise1h", 0, 3600) + "</additional>")


def write_additional(win: str, tag: str = "asis", end: int = END):
    WORK.mkdir(exist_ok=True)
    f = SIM / f"detectors_{tag}_{win}.add.xml"
    f.write_text(additional_xml("work/", tag, win, end))
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
  <output><tripinfo-output value="work/tripinfo_{tag}_{win}.xml"/><statistic-output value="work/stats_{tag}_{win}.xml"/>
    <queue-output value="work/queue_{tag}_{win}.xml"/><queue-output.aggregation value="3600"/><queue-output.percentile value="95"/></output>
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
