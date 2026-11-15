"""Single loader for dashboard + report figures."""
from __future__ import annotations
import json
import geopandas as gpd, pandas as pd
from .geo import PROC
from .traffic import PH, vph_peak
from . import noise, emissions

MODES = ["carros", "motos", "onibus", "caminhoes", "bicicletas"]


def _gj(name):
    return gpd.read_file(PROC / name)


def load() -> dict:
    d = {k: _gj(f"ippuc_{k}.geojson") for k in ("sistema_viario", "ciclovias", "ciclorrotas", "calcadao", "terminais", "bairros")}
    d["area"] = _gj("study_area.geojson")
    roads = _gj("roads.geojson")
    d["roads"] = roads[roads["class"].isin(["trunk", "primary", "secondary", "tertiary"])]
    pts = pd.read_csv(PH / "points.csv").merge(pd.read_csv(PH / "field_counts.csv"), on="point_id").merge(
        pd.read_csv(PH / "noise_leq.csv"), on="point_id", suffixes=("", "_ruido"))
    for w in ("manha", "tarde"):
        pts[f"vph_{w}"] = [vph_peak(v, w) for v in pts.vpd_total]
    d["points"] = pts
    d["hourly"] = pd.read_csv(PH / "hourly_profile.csv")
    d["bus_kpis"] = pd.read_csv(PROC / "bus_kpis.csv")
    d["bus_fixes"] = pd.read_parquet(PROC / "bus_fixes.parquet")
    a = d["area"].to_crs(31982)
    d["stats"] = {"area_km2": a.area.iloc[0] / 1e6,
                  "ciclo_km": d["ciclovias"].to_crs(31982).length.sum() / 1000,
                  "n_segments": len(_gj("roads.geojson")), "n_points": len(pts)}
    return d


def emissions_table(pts: pd.DataFrame, window: str, v_kmh: float) -> pd.DataFrame:
    rows = []
    for r in pts.itertuples():
        mix = {m: getattr(r, f"share_{m}") for m in MODES}
        e = emissions.baseline_g_per_h(getattr(r, f"vph_{window}"), mix, v_kmh)
        rows.append({"point_id": r.point_id, "name": r.name, **{k: v / 1000 for k, v in e.items()}})  # kg/h por km de via
    return pd.DataFrame(rows)


def cortn_table(pts: pd.DataFrame, window: str, v_kmh: float, d_m: float = 10.0) -> pd.Series:
    out = []
    for r in pts.itertuples():
        hv = 100 * (r.share_onibus + r.share_caminhoes)
        out.append(noise.leq_from_l10(noise.cortn_l10_1h(getattr(r, f"vph_{window}"), v_kmh, hv, d_m)))
    return pd.Series(out, index=pts.point_id)
