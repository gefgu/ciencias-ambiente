"""Modos ativos (M3): pedestres na região do Calçadão da XV e ciclistas.

Demanda PROVISÓRIA (sem contagem de pedestres/ciclistas): pedestres sorteados entre arestas de pedestre/calçada dentro de ~250 m do
Calçadão (IPPUC); ciclistas sorteados entre arestas que permitem bicicleta. Substituir pelos números de campo
(a coluna ped_h_pico de data/placeholders/field_counts.csv dá a ordem de grandeza).
"""
from __future__ import annotations
import random
import geopandas as gpd, sumolib
from .common import SIM, WORK, OUT, run

PED_PER_H = 2400   # PROVISÓRIO
BIKE_PER_H = 300   # PROVISÓRIO
OVERSAMPLE = 10    # a rede de pedestres aberta é fragmentada: pedimos mais pares e mantemos só os roteáveis (viés: pares conectados)
VTYPES = '''<additional>
  <vType id="bike" vClass="bicycle" length="1.8" maxSpeed="5.5" width="0.6" color="77,124,15" emissionClass="Zero/default"/>
  <vType id="ped" vClass="pedestrian" color="124,58,237"/>
</additional>'''


def build_demand(net_file: str, win: str = "am", seed: int = 9) -> str:
    """Escreve rotas de pedestres e bicicletas para uma variante de rede; devolve o caminho do .rou.xml (já roteado)."""
    rng = random.Random(seed)
    net = sumolib.net.readNet(net_file)
    cal = gpd.read_file(OUT / "ippuc_calcadao.geojson").to_crs(31982).union_all().buffer(250)
    ped_e, bike_e = [], []
    for e in net.getEdges():
        if e.getID().startswith(":"):
            continue
        x, y = e.getShape()[0]
        px, py = net.convertXY2LonLat(x, y)  # noqa
        if e.allows("pedestrian") and not e.allows("passenger"):
            from shapely.geometry import Point
            gx = gpd.GeoSeries([Point(px, py)], crs=4326).to_crs(31982).iloc[0]
            if cal.contains(gx):
                ped_e.append(e.getID())
        if e.allows("bicycle") and e.getLength() > 40:
            bike_e.append(e.getID())
    items = []
    for i in range(PED_PER_H * OVERSAMPLE):
        a, b = rng.sample(ped_e, 2)
        items.append((rng.uniform(0, 3600), f'<person id="ped{i}" type="ped" depart="DEP"><walk from="{a}" to="{b}"/></person>'))
    for i in range(BIKE_PER_H):
        a, b = rng.sample(bike_e, 2)
        items.append((rng.uniform(0, 3600), f'<trip id="bike{i}" type="bike" depart="DEP" from="{a}" to="{b}"/>'))
    items.sort(key=lambda z: z[0])
    body = "\n".join(s.replace("DEP", f"{t:.1f}") for t, s in items)
    raw = WORK / f"active_{win}.trips.xml"
    raw.write_text(f"<routes>\n{VTYPES.replace('<additional>', '').replace('</additional>', '')}\n{body}\n</routes>")
    out = WORK / f"active_{win}.rou.xml"
    p = run(["duarouter", "-n", net_file, "-r", raw, "-o", out, "--ignore-errors", "true", "--no-warnings", "true", "--no-step-log", "true"])
    assert out.exists(), p.stderr[-400:]
    import json, xml.etree.ElementTree as ET
    tree = ET.parse(out)
    r = tree.getroot()
    persons = r.findall("person")
    routable = len(persons)
    for extra in rng.sample(persons, max(0, routable - PED_PER_H)):  # mantém PED_PER_H pedestres
        r.remove(extra)
    tree.write(out)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "m3_active_demand.json").write_text(json.dumps({"persons_requested": PED_PER_H, "persons_requested_total": PED_PER_H * OVERSAMPLE, "persons_routable": routable, "persons_routed": len(r.findall("person")), "bikes_requested": BIKE_PER_H,
                                                             "bikes_routed": len(r.findall("vehicle")) + len(r.findall("trip")), "ped_edges_near_calcadao": len(ped_e), "bike_edges": len(bike_e)}))
    return str(out)
