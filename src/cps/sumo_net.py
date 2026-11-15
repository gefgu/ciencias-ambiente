"""Overture segments -> SUMO plain XML -> netconvert (M2).

Signals are GUESSED by netconvert (no public signal-phase data): documented assumption, to be replaced by field survey.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from xml.sax.saxutils import quoteattr
import geopandas as gpd
from shapely.ops import substring
from fastmob.network import builder as fb
from src.m1.geo import RAW

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "sim"
SIM_BBOX = (-49.285, -25.455, -49.245, -25.420)  # núcleo central: cobre P01–P04 (P05, em lon −49,308, fica fora)
CLASSES = {  # classe Overture -> (faixas, velocidade m/s, prioridade)
    "trunk": (3, 16.7, 10), "primary": (2, 13.9, 9), "secondary": (2, 13.9, 8), "tertiary": (1, 11.1, 7),
    "unclassified": (1, 8.3, 5), "residential": (1, 8.3, 4), "living_street": (1, 5.6, 3)}


ACTIVE = {"footway": (1, 1.4, 2, "pedestrian", 2.0), "pedestrian": (1, 1.4, 2, "pedestrian", 4.0), "path": (1, 1.4, 2, "pedestrian", 1.5),
          "cycleway": (1, 5.5, 2, "bicycle pedestrian", 2.0)}  # classe -> (faixas, m/s, prio, allow, largura)
# Proposta To-Be: faixa exclusiva de ciclistas nas vias de apoio do centro (secundárias/terciárias com nome nos eixos abaixo)
BIKE_LANE_STREETS = {"Rua Mariano Torres", "Alameda Doutor Muricy", "Rua Martim Afonso", "Avenida Presidente Kennedy"}


def build(bbox=SIM_BBOX, variant: str = "base") -> dict:
    """variant: base (só veículos) | active (+ pedestres, ciclovias, travessias) | tobe (active + faixas de bicicleta propostas)."""
    SIM.mkdir(exist_ok=True)
    active = variant in ("active", "tobe")
    name_out = {"base": "net", "active": "net_active", "tobe": "net_tobe"}[variant]
    s = gpd.read_parquet(RAW / "overture_segment_study.parquet")
    s = s[(s["subtype"] == "road") & s["class"].isin(list(CLASSES) + (list(ACTIVE) if active else []))].cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    s = s.rename(columns={"class": "road_class"})
    nodes: dict[str, tuple[float, float]] = {}
    edges: list[str] = []
    for r in s.itertuples():
        conns = sorted(r.connectors, key=lambda c: c["at"])
        d = fb._direction_for_pair(r.access_restrictions)
        if d is None:
            continue
        is_act = r.road_class in ACTIVE
        lanes, v, prio = (ACTIVE[r.road_class][:3] if is_act else CLASSES[r.road_class])
        pname = (r.names or {}).get("primary") if isinstance(r.names, dict) else None
        bike_lane = variant == "tobe" and not is_act and pname in BIKE_LANE_STREETS and r.road_class in ("secondary", "tertiary", "primary")
        lane_attr = ""
        if is_act:
            lane_attr = f' allow="{ACTIVE[r.road_class][3]}" width="{ACTIVE[r.road_class][4]}"'
        elif active:
            lane_attr = ' disallow="pedestrian"'
        if bike_lane:
            lanes += 1
        for c1, c2 in zip(conns[:-1], conns[1:]):
            if c1["at"] == c2["at"]:
                continue
            sh = substring(r.geometry, c1["at"], c2["at"], normalized=True)
            if sh.geom_type != "LineString" or sh.length == 0:
                continue
            pts = list(sh.coords)
            nodes[c1["connector_id"]], nodes[c2["connector_id"]] = pts[0], pts[-1]
            nm = (r.names or {}).get("primary") if isinstance(r.names, dict) else None
            name = f' name={quoteattr(nm)}' if nm else ""
            base = f"{r.id[:12]}_{conns.index(c1)}"
            lanes_xml = "".join([f'<lane index="0" allow="bicycle" width="1.5"/>'] if bike_lane else []) + ""
            if active and not bike_lane:
                lanes_xml = "".join(f'<lane index="{i}"{lane_attr}/>' for i in range(lanes))
            elif bike_lane:
                lanes_xml += "".join(f'<lane index="{i}" disallow="pedestrian bicycle"/>' for i in range(1, lanes))
            spread = ""
            def emit(eid, a, b, pl):
                shp = " ".join(f"{x:.7f},{y:.7f}" for x, y in pl)
                edges.append(f'<edge id="{eid}" from="{a}" to="{b}" numLanes="{lanes}" speed="{v}" priority="{prio}"{name} shape="{shp}"{spread}>{lanes_xml}</edge>')
            if d in ("both", "forward"):
                emit(base, c1["connector_id"], c2["connector_id"], pts)
            if d in ("both", "backward"):
                emit("-" + base, c2["connector_id"], c1["connector_id"], pts[::-1])
    used = set()
    for e in edges:
        used.update([e.split('from="')[1].split('"')[0], e.split('to="')[1].split('"')[0]])
    (SIM / f"{name_out}.nod.xml").write_text('<nodes>\n' + "\n".join(f'<node id="{k}" x="{x:.7f}" y="{y:.7f}"/>' for k, (x, y) in nodes.items() if k in used) + "\n</nodes>")
    (SIM / f"{name_out}.edg.xml").write_text('<edges>\n' + "\n".join(edges) + "\n</edges>")
    cmd = ["netconvert", "--node-files", str(SIM / f"{name_out}.nod.xml"), "--edge-files", str(SIM / f"{name_out}.edg.xml"), "-o", str(SIM / f"{name_out}.net.xml"),
           "--proj.plain-geo", "true", "--proj", "+proj=utm +zone=22 +south +datum=WGS84 +units=m +no_defs",
           # variantes ativas não fundem arestas (preserva os ids da base; as rotas do M2 são reparadas com o duarouter).
           # Sem fusão a valência dos nós muda: limiar 107 dá 233 semáforos nelas (base: 223 com 110).
           "--geometry.remove", "false" if active else "true", "--junctions.join", "true",
           "--tls.guess", "true", "--tls.guess.threshold", "107" if active else "110", "--tls.default-type", "actuated",
           "--no-turnarounds", "true", *(["--crossings.guess", "true", "--walkingareas", "true"] if active else []), "--keep-edges.components", "1", "--no-warnings", "true"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    fixed = repair_orphan_tls(SIM / f"{name_out}.net.xml") if p.returncode == 0 else 0
    return {"edges_in": len(edges), "rc": p.returncode, "orphan_tls_removed": fixed, "log": (p.stderr or p.stdout)[-400:]}


def repair_orphan_tls(path) -> int:
    """netconvert pode deixar conexões apontando para um semáforo sem <tlLogic> (clusters muito grandes de junções unidas).
    Esses nós viram junções de prioridade (sem semáforo). Devolve quantos semáforos órfãos foram removidos."""
    import re
    txt = path.read_text()
    defined = set(re.findall(r'<tlLogic id="([^"]+)"', txt))
    used = set(re.findall(r' tl="([^"]+)"', txt))
    orphans = used - defined
    for o in orphans:
        eo = re.escape(o)
        txt = re.sub(rf' tl="{eo}" linkIndex="\d+"(?: linkIndex2="\d+")?', "", txt)
        txt = re.sub(rf'(<junction id="{eo}"[^>]*?)type="traffic_light(?:_unregulated|_right_on_red)?"', r'\1type="priority"', txt)
    if orphans:
        path.write_text(txt)
    return len(orphans)


if __name__ == "__main__":
    import sys
    print(build(variant=sys.argv[1] if len(sys.argv) > 1 else "base"))


def net_stats(name: str = "net") -> dict:
    """Contagens da rede gerada (lidas pelo relatório M2)."""
    import json, re
    from src.m1.geo import PROC
    t = (SIM / f"{name}.net.xml").read_text()
    s = {"edges": len(re.findall(r'<edge id="[^:]', t)), "junctions": len(re.findall(r'<junction id="[^:]', t)), "tls": len(re.findall(r"<tlLogic", t)),
         "tls_guess_threshold": 110, "bbox": list(SIM_BBOX)}
    (PROC / f"m2_{name}_stats.json").write_text(json.dumps(s))
    return s
