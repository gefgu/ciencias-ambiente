"""Demanda As-Is: contagens PROVISÓRIAS nas aproximações dos pontos -> routeSampler -> rotas com tipos de veículo."""
from __future__ import annotations
import random
import numpy as np, pandas as pd, sumolib
from src.m1.traffic import PH, STREETS
from src.m1.geo import load_segments
from . import vtypes
from .common import SIM, WORK, pytool, window_scale

NET = SIM / "net.net.xml"
RADIUS_M = 80
END_RADIUS_M = 35


def monitored_edges(net) -> pd.DataFrame:
    """Aproximações = arestas que CHEGAM ao cruzamento (fim da aresta a ≤35 m do ponto) e cujo nome bate com uma das duas vias.
    Só entradas recebem contagem: fluxo de entrada e de saída do mesmo nó não devem ser somados."""
    pts = pd.read_csv(PH / "points.csv")
    rows = []
    for r in pts.itertuples():
        x, y = net.convertLonLat2XY(r.lon, r.lat)
        names = {STREETS[r.street_a], STREETS[r.street_b]}
        for e, d in net.getNeighboringEdges(x, y, RADIUS_M):
            if e.getName() in names and e.allows("passenger") and not e.getID().startswith(":"):
                ex, ey = e.getShape()[-1]
                if ((ex - x) ** 2 + (ey - y) ** 2) ** .5 <= END_RADIUS_M:
                    rows.append((r.point_id, e.getID(), e.getName(), e.getLaneNumber(), round(d, 1)))
    return pd.DataFrame(rows, columns=["point_id", "edge", "street", "lanes", "dist_m"])


def observed_counts(win: str, seed: int = 3) -> pd.DataFrame:
    """PROVISÓRIO: reparte o fluxo de pico do ponto entre suas arestas (peso = nº de faixas, ruído ±15%)."""
    net = sumolib.net.readNet(str(NET))
    me = monitored_edges(net)
    p = pd.read_csv(PH / "points.csv").merge(pd.read_csv(PH / "field_counts.csv"), on="point_id")
    from src.m1.traffic import vph_peak
    rng = np.random.default_rng(seed)
    out = []
    for pid, g in me.groupby("point_id"):
        vph = vph_peak(p.loc[p.point_id == pid, "vpd_total"].iloc[0], {"am": "manha", "pm": "tarde"}[win])
        w = g.lanes.values / g.lanes.sum()
        out += [(pid, e, vph * wi * rng.uniform(.85, 1.15)) for e, wi in zip(g.edge, w)]
    return pd.DataFrame(out, columns=["point_id", "edge", "obs_vph"])


def write_counts(df: pd.DataFrame, path, col="target_vph"):
    rows = "\n".join(f'    <edge id="{r.edge}" entered="{getattr(r, col):.1f}"/>' for r in df.itertuples())
    path.write_text(f'<data>\n  <interval id="h" begin="0" end="3600">\n{rows}\n  </interval>\n</data>\n')


def via_pool(net, edges: list[str], n_per_edge: int = 40, seed: int = 5):
    """Viagens forçadas a passar por cada aresta monitorada (origem/destino sorteados ≥800 m), roteadas com duarouter."""
    out = WORK / "pool_via.rou.xml"
    if out.exists():
        return out
    rng = random.Random(seed)
    cand = [e for e in net.getEdges() if e.allows("passenger") and e.getLength() > 30 and not e.getID().startswith(":")]
    trips = []
    for eid in edges:
        ex, ey = net.getEdge(eid).getShape()[0]
        far = [e for e in cand if ((e.getShape()[0][0] - ex) ** 2 + (e.getShape()[0][1] - ey) ** 2) ** .5 > 800]
        for k in range(n_per_edge):
            a, b = rng.sample(far, 2)
            trips.append(f'<trip id="{eid}_{k}" depart="{k * 3600 / n_per_edge:.1f}" from="{a.getID()}" to="{b.getID()}" via="{eid}"/>')
    (WORK / "via_trips.xml").write_text("<routes>\n" + "\n".join(trips) + "\n</routes>")
    from .common import run
    run(["duarouter", "-n", NET, "-r", WORK / "via_trips.xml", "-o", out, "--ignore-errors", "true", "--no-warnings", "true", "--no-step-log", "true"])
    return out


def build_routes(counts: pd.DataFrame, win: str, seed: int = 42, pool_period: float = 0.6) -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    pool = WORK / "pool.rou.xml"
    net_t = NET.stat().st_mtime
    if pool.exists() and pool.stat().st_mtime < net_t:  # rede mudou: invalida os caches de rotas
        for f in (pool, WORK / "pool_via.rou.xml"):
            f.unlink(missing_ok=True)
    if not pool.exists():
        r = pytool("randomTrips.py", "-n", NET, "-o", WORK / "trips.xml", "-r", pool, "-e", 3600, "-p", pool_period, "--fringe-factor", 15,
                   "--min-distance", 800, "--vehicle-class", "passenger", "--validate", "--seed", seed, "--random")
        assert pool.exists(), r.stderr[-500:]
    vp = via_pool(sumolib.net.readNet(str(NET)), counts.edge.tolist())
    write_counts(counts, WORK / f"counts_{win}.xml")
    raw = WORK / f"routes_{win}_raw.rou.xml"
    r = pytool("routeSampler.py", "-r", f"{pool},{vp}", "-d", WORK / f"counts_{win}.xml", "-o", raw, "--optimize", "full", "--seed", seed, "--begin", 0, "--end", 3600,
               "--min-count", 1, "--weighted", "--threads", 1)
    assert raw.exists(), r.stderr[-600:]
    # atribui tipos de veículo conforme a frota (rota inalterada)
    m = vtypes.mix(); keys, probs = list(m), np.array(list(m.values())); rng = random.Random(seed)
    out = [f'<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">']
    vs = sorted(sumolib.xml.parse(str(raw), "vehicle"), key=lambda v: float(v.depart))
    n = 0
    for v in vs:
        t = rng.choices(keys, probs)[0]
        edges = v.route[0].edges
        out.append(f'  <vehicle id="v{n}" type="{t}" depart="{float(v.depart):.2f}" departLane="best" departSpeed="max"><route edges="{edges}"/></vehicle>')
        n += 1
    out.append("</routes>")
    (WORK / f"routes_{win}.rou.xml").write_text("\n".join(out))
    return {"vehicles": n, "target_total_vph": float(counts.target_vph.sum())}
