"""IPPUC layers (SIRGAS 2000 / UTM 22S) clipped to the study polygon, exported as WGS84 GeoJSON."""
from __future__ import annotations
import geopandas as gpd
from .geo import RAW, PROC

LAYERS = {"sistema_viario": "SIST_VIARIO_CLASSIFICADO", "ciclovias": "CICLOVIA_OFICIAL", "ciclorrotas": "CICLORROTA",
          "calcadao": "CALCADAO", "terminais": "TERMINAL_DE_TRANSPORTE", "bairros": "DIVISA_DE_BAIRROS"}


def build() -> dict:
    poly = gpd.read_file(PROC / "study_area.geojson").to_crs(31982).geometry.iloc[0]
    out = {}
    for key, shp in LAYERS.items():
        g = gpd.read_file(f"zip://{RAW / 'ippuc' / (shp + '.zip')}")
        g = gpd.clip(g, poly)
        g = g[~g.geometry.is_empty]
        g.to_crs(4326).to_file(PROC / f"ippuc_{key}.geojson", driver="GeoJSON")
        out[key] = len(g)
    return out


if __name__ == "__main__":
    print(build())
