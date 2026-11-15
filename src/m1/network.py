"""Routable graph for fastmob built from the Overture segments already downloaded by geo.py.

Re-implements fastmob.network.builder.fetch_road_network on a local parquet (that function reads S3 via
DuckDB); everything after the SQL step reuses fastmob's own helpers so the graph schema is identical.
"""
from __future__ import annotations
import math
import geopandas as gpd
from fastmob.network import RoadNetwork, builder as fb
from .geo import RAW


def _hav(lat1, lng1, lat2, lng2) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


def build_graph(bbox: tuple[float, float, float, float]):
    """bbox = (min_lon, min_lat, max_lon, max_lat). Returns (nodes_df, edges_df, RoadNetwork)."""
    s = gpd.read_parquet(RAW / "overture_segment_study.parquet")
    s = s[(s["subtype"] == "road") & s["class"].isin(fb.DRIVABLE_CLASSES)].cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    s = s.rename(columns={"class": "road_class"})
    coords: dict[str, tuple[float, float]] = {}
    recs: list[tuple[str, str, float, float, int, str]] = []
    for r in s.itertuples():
        conns = sorted(r.connectors, key=lambda c: c["at"])
        for c1, c2 in zip(conns[:-1], conns[1:]):
            p1, p2 = r.geometry.interpolate(c1["at"], normalized=True), r.geometry.interpolate(c2["at"], normalized=True)
            v = fb._speed_kmh_for_pair(r.speed_limits, r.road_class, c1["at"], c2["at"])
            d = fb._direction_for_pair(r.access_restrictions)
            if d is None or v <= 0:
                continue
            L = max(_hav(p1.y, p1.x, p2.y, p2.x), 0.1)
            w = max(1, round(L / (v * fb.CAR_SPEED_FACTOR / 3.6) * 10))
            coords[c1["connector_id"]], coords[c2["connector_id"]] = (p1.y, p1.x), (p2.y, p2.x)
            cls = r.road_class
            if d in ("both", "forward"):
                recs.append((c1["connector_id"], c2["connector_id"], L, v, w, cls))
            if d in ("both", "backward"):
                recs.append((c2["connector_id"], c1["connector_id"], L, v, w, cls))
    nodes, idx = fb._nodes_table(coords)
    edges = fb._edges_table(recs, idx)
    return nodes, edges, RoadNetwork.build(edges, nodes)
