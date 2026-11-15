"""Study area + road network from Overture Maps (replaces Overpass/OSMnx)."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[2]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
BBOX = "-49.32,-25.475,-49.235,-25.405"  # W,S,E,N — covers all six boundary streets

# manual §1: the six streets that delimit the quadrilateral (exact Overture primary names)
BOUNDARY_STREETS = {
    "Av. Pres. Kennedy": "Avenida Presidente Kennedy",
    "Calçadão R. XV de Novembro": "Rua XV de Novembro",
    "Av. Mal. Floriano Peixoto": "Avenida Marechal Floriano Peixoto",
    "Alameda Dr. Muricy": "Alameda Doutor Muricy",
    "R. Martim Afonso": "Rua Martim Afonso",
    "R. Gen. Mário Tourinho": "Rua General Mário Tourinho",
}


def download(force: bool = False) -> None:
    for t in ("segment", "connector"):
        out = RAW / f"overture_{t}_study.parquet"
        if out.exists() and not force:
            continue
        subprocess.run([sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={BBOX}",
                        "-f", "geoparquet", "-t", t, "-o", str(out)], check=True)


def load_segments() -> gpd.GeoDataFrame:
    s = gpd.read_parquet(RAW / "overture_segment_study.parquet")
    s["name"] = s["names"].apply(lambda n: n.get("primary") if isinstance(n, dict) else None)
    return s[s["subtype"] == "road"].copy()


def study_polygon(seg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Convex hull of the six boundary streets (decision: literal reading of the manual)."""
    parts = []
    for label, name in BOUNDARY_STREETS.items():
        g = seg[seg["name"] == name]
        if g.empty:
            raise ValueError(f"boundary street not found: {name}")
        parts.append(g.geometry.union_all())
    hull = gpd.GeoSeries(parts, crs=seg.crs).union_all().convex_hull
    return gpd.GeoDataFrame({"name": ["Quadrilátero Central (hull das 6 vias)"]}, geometry=[hull], crs=seg.crs)


def build() -> dict:
    PROC.mkdir(parents=True, exist_ok=True)
    seg = load_segments()
    poly = study_polygon(seg)
    inside = seg[seg.intersects(poly.geometry.iloc[0])].copy()
    inside["is_boundary"] = inside["name"].isin(BOUNDARY_STREETS.values())
    keep = ["id", "name", "class", "subclass", "is_boundary", "geometry"]
    poly.to_file(PROC / "study_area.geojson", driver="GeoJSON")
    inside[keep].to_file(PROC / "roads.geojson", driver="GeoJSON")
    area_km2 = poly.to_crs(31982).area.iloc[0] / 1e6  # SIRGAS 2000 / UTM 22S
    return {"segments": len(inside), "area_km2": round(area_km2, 2), "classes": inside["class"].value_counts().to_dict()}


if __name__ == "__main__":
    download()
    print(build())
