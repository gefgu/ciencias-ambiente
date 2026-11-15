"""Bus telemetry (URBS) -> fastmob (map-matching) -> speed / stop-and-go indicators.

The real URBS vehicle-position API needs a registration code (not public). With env URBS_API_KEY set,
`fetch_live` is the hook to use; otherwise `synthetic_traces` produces GPS fixes along real street geometry
and EVERYTHING derived from it is flagged is_placeholder=True in the outputs.
"""
from __future__ import annotations
import math, os
import numpy as np, pandas as pd, geopandas as gpd
from shapely.ops import linemerge
from fastmob import TrajDataFrame
from fastmob.network import match_trajectory
from .geo import PROC, load_segments
from .network import build_graph

CORE_BBOX = (-49.285, -25.445, -49.245, -25.420)  # downtown core used for the matching demo
CORRIDORS = {"Av. Mal. Floriano Peixoto": "Avenida Marechal Floriano Peixoto",
             "R. Mariano Torres": "Rua Mariano Torres", "Alameda Dr. Muricy": "Alameda Doutor Muricy"}
WINDOWS = {"Pico manhã (06:30–09:00)": ("06:30", 18.0), "Entrepico (10:00–16:00)": ("11:00", 27.0),
           "Pico tarde (17:00–19:00)": ("17:00", 15.0)}  # label: (start, mean cruise speed km/h) — placeholder values


def fetch_live(api_key: str | None = None) -> pd.DataFrame | None:
    """Ponto de extensão para a API de posição de veículos da URBS (requer código de acesso, não público).
    Sem chave retorna None e o pipeline usa telemetria sintética (is_placeholder=True)."""
    if not (api_key or os.environ.get("URBS_API_KEY")):
        return None
    raise NotImplementedError("Implementar após receber a chave/endpoint oficial da URBS.")


def _corridor_line(name: str, seg: gpd.GeoDataFrame):
    g = seg[(seg["name"] == name)].cx[CORE_BBOX[0]:CORE_BBOX[2], CORE_BBOX[1]:CORE_BBOX[3]]
    m = linemerge(list(g.to_crs(31982).geometry.union_all().geoms) if g.shape[0] > 1 else list(g.to_crs(31982).geometry))
    return max(m.geoms, key=lambda x: x.length) if m.geom_type == "MultiLineString" else m


def synthetic_traces(seed: int = 7, buses_per_window: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seg = load_segments()
    rows = []
    for label, wname in [(k, v) for k, v in WINDOWS.items()]:
        t0, vmean = wname
        for cname, street in CORRIDORS.items():
            line = _corridor_line(street, seg)
            for b in range(buses_per_window):
                s, t = 0.0, pd.Timestamp(f"2026-08-21 {t0}") + pd.Timedelta(seconds=int(rng.integers(0, 1800)))
                rev = b % 2 == 1
                phase = rng.uniform(0, 6.28)
                while s < line.length:
                    # stop-and-go: sinusoidal modulation + random red-light stops (stronger in peak windows)
                    stop_p = 0.16 if vmean < 20 else 0.05
                    v = max(0.0, vmean * (1 + 0.8 * math.sin(s / 140 + phase))) / 3.6
                    if rng.random() < stop_p:
                        v = 0.0
                    s += v * 10
                    p = line.interpolate(line.length - s if rev else s)
                    rows.append((f"{label}|{cname}|{b}", label, cname, t, p.x + rng.normal(0, 8), p.y + rng.normal(0, 8), v * 3.6))
                    t += pd.Timedelta(seconds=10)
    df = pd.DataFrame(rows, columns=["uid", "window", "corridor", "datetime", "x", "y", "true_kmh"])
    pts = gpd.GeoSeries(gpd.points_from_xy(df.x, df.y), crs=31982).to_crs(4326)
    df["lng"], df["lat"] = pts.x.values, pts.y.values
    return df.drop(columns=["x", "y"])


def _speeds(m: pd.DataFrame) -> pd.DataFrame:
    """Speed from consecutive matched fixes (haversine / dt), per vehicle trace."""
    m = m.sort_values(["uid", "datetime"]).copy()
    lat, lng = np.radians(m.matched_lat.values), np.radians(m.matched_lng.values)
    same = (m.uid.values[1:] == m.uid.values[:-1])
    a = np.sin((lat[1:] - lat[:-1]) / 2) ** 2 + np.cos(lat[:-1]) * np.cos(lat[1:]) * np.sin((lng[1:] - lng[:-1]) / 2) ** 2
    d = 2 * 6371000 * np.arcsin(np.sqrt(a))
    dt = (m.datetime.values[1:] - m.datetime.values[:-1]) / np.timedelta64(1, "s")
    v = np.where(same & (dt > 0), d / np.where(dt > 0, dt, 1) * 3.6, np.nan)
    m["kmh"] = np.concatenate([[np.nan], v])
    return m


def run() -> dict:
    tr = synthetic_traces()
    _, _, net = build_graph(CORE_BBOX)
    matched = match_trajectory(tr[["uid", "datetime", "lat", "lng"]], network=net, uid_col="uid",
                               datetime_col="datetime", lat_col="lat", lng_col="lng")
    m = matched.to_pandas() if hasattr(matched, "to_pandas") else pd.DataFrame(matched)
    m = m[m.match_status != "unmatched"].merge(tr[["uid", "datetime", "window", "corridor"]], on=["uid", "datetime"])
    m = _speeds(m)
    PROC.mkdir(parents=True, exist_ok=True)
    m[["uid", "window", "corridor", "datetime", "matched_lat", "matched_lng", "kmh", "distance_to_road_m"]].to_parquet(PROC / "bus_fixes.parquet")
    g = m.dropna(subset=["kmh"]).groupby(["window", "corridor"])
    kpi = g.agg(vel_media_kmh=("kmh", "mean"), pct_parado=("kmh", lambda x: 100 * (x < 5).mean()),
                desvio_vel=("kmh", "std"), n_fixes=("kmh", "size")).round(2).reset_index()
    kpi["is_placeholder"] = True  # synthetic telemetry until URBS key is available
    kpi.to_csv(PROC / "bus_kpis.csv", index=False)
    return {"fixes": len(tr), "matched": len(m), "median_dist_to_road_m": round(float(m.distance_to_road_m.median()), 1),
            "kpi": kpi.groupby("window")[["vel_media_kmh", "pct_parado"]].mean().round(1).to_dict()}


if __name__ == "__main__":
    print(run())
