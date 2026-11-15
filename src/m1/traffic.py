"""Measurement points (real coordinates, from boundary-street crossings) + PLACEHOLDER counts/profile.

Real values must replace data/placeholders/*.csv after field work (contagem manual de VPD, medição de Leq).
"""
from __future__ import annotations
import itertools
import numpy as np, pandas as pd, geopandas as gpd
from .geo import PROC, load_segments, BOUNDARY_STREETS
from pathlib import Path

PH = Path(__file__).resolve().parents[2] / "data" / "placeholders"
LIMITE_DIURNO = 60  # NBR 10151: área mista comercial/administrativa (diurno)
EXTRA = {"R. Mariano Torres": "Rua Mariano Torres"}
CLASS_VPD = {"trunk": 38000, "primary": 26000, "secondary": 17000, "tertiary": 9000}  # order-of-magnitude placeholders
PEAK_PROFILE = np.array([.8, .5, .4, .4, .6, 1.6, 4.0, 7.4, 8.0, 6.4, 5.6, 5.5, 5.8, 5.6, 5.6, 6.0, 7.0, 8.2, 7.6, 5.2, 3.6, 2.6, 1.8, 1.2])
PEAK_PROFILE = PEAK_PROFILE / PEAK_PROFILE.sum()


STREETS = {**BOUNDARY_STREETS, **EXTRA}


def find_points() -> gpd.GeoDataFrame:
    """Crossings between pairs of boundary/corridor streets (<=25 m apart) -> candidate measurement points."""
    seg = load_segments().to_crs(31982)
    streets = STREETS
    geoms = {lab: seg[seg["name"] == n].geometry.union_all() for lab, n in streets.items()}
    pts = []
    for (a, ga), (b, gb) in itertools.combinations(geoms.items(), 2):
        if ga.distance(gb) > 25:
            continue
        i = ga.intersection(gb)
        if i.is_empty:  # quase-cruzamento (<=25 m, ex.: geometrias que não se tocam por pequena folga)
            from shapely.ops import nearest_points
            p = nearest_points(ga, gb)[0]
        else:
            p = i.centroid if i.geom_type in ("Point", "MultiPoint") else i.representative_point()
        pts.append((f"{a.split(' ', 1)[-1]} × {b.split(' ', 1)[-1]}", a, b, p))
    g = gpd.GeoDataFrame(pts, columns=["name", "street_a", "street_b", "geometry"], crs=31982).to_crs(4326)
    g["point_id"] = [f"P{i + 1:02d}" for i in range(len(g))]
    return g


def make_placeholders(force: bool = False, seed: int = 11) -> None:
    PH.mkdir(parents=True, exist_ok=True)
    pts = find_points()
    pts.assign(lat=pts.geometry.y, lon=pts.geometry.x).drop(columns="geometry").to_csv(PH / "points.csv", index=False)
    rng = np.random.default_rng(seed)
    seg = load_segments()
    cls = seg.dropna(subset=["name"]).groupby("name")["class"].agg(lambda s: s.mode().iloc[0]).to_dict()  # classe modal da via
    if force or not (PH / "field_counts.csv").exists():
        rows = []
        for r in pts.itertuples():
            base = max(CLASS_VPD.get(cls.get(STREETS[n], ""), 9000) for n in (r.street_a, r.street_b) if cls.get(STREETS[n]) != "pedestrian") if any(cls.get(STREETS[n]) != "pedestrian" for n in (r.street_a, r.street_b)) else 3000
            vpd = int(base * rng.uniform(0.7, 1.15))
            mix = rng.dirichlet([60, 10, 3.5, 4.5, 1.5]) # carros, motos, onibus, caminhoes, bicicletas
            rows.append(dict(point_id=r.point_id, vpd_total=vpd, share_carros=mix[0], share_motos=mix[1], share_onibus=mix[2],
                             share_caminhoes=mix[3], share_bicicletas=mix[4], ped_h_pico=int(rng.uniform(800, 4200)),
                             data_contagem="", contador="", is_placeholder=True))
        pd.DataFrame(rows).round(4).to_csv(PH / "field_counts.csv", index=False)
    if force or not (PH / "noise_leq.csv").exists():
        rows = []
        for r in pts.itertuples():
            leq = rng.uniform(68, 77)
            rows.append(dict(point_id=r.point_id, periodo="diurno", leq_dba=round(leq, 1), residual_dba=round(leq - rng.uniform(7, 12), 1),
                             limite_nbr10151=LIMITE_DIURNO, data_medicao="", instrumento="", is_placeholder=True))
        pd.DataFrame(rows).to_csv(PH / "noise_leq.csv", index=False)
    if force or not (PH / "hourly_profile.csv").exists():
        pd.DataFrame({"hora": range(24), "fracao_vpd": PEAK_PROFILE.round(5), "is_placeholder": True}).to_csv(PH / "hourly_profile.csv", index=False)


def vph_peak(vpd: float, window: str) -> float:
    h = {"manha": [7, 8], "tarde": [17, 18]}[window]  # 06:30-09:00 ~ hours 7-8; 17:00-19:00 hours 17-18
    return float(vpd * PEAK_PROFILE[h].mean())
