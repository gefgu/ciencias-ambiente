"""Dados REAIS da URBS (espelho aberto da UFPR/C3SL: http://dadosabertos.c3sl.ufpr.br/curitibaurbs/).

Baixa um dia útil (linhas, shapes, pontos, GPS dos veículos) e extrai as passagens de ônibus pelo Quadrilátero:
  data/processed/urbs_pings.parquet   posições GPS (5–10 s) dentro do polígono + 150 m
  data/processed/urbs_trips.parquet   viagens (veículo, linha, início, fim) com ≥300 m dentro da área
"""
from __future__ import annotations
import json, subprocess
import numpy as np, pandas as pd, geopandas as gpd
from .geo import ROOT, PROC

RAW = ROOT / "data" / "raw" / "urbs"
BASE = "http://dadosabertos.c3sl.ufpr.br/curitibaurbs"
DAY = "2026_11_13"          # o arquivo do dia 13 contém as posições de 12/11 (quinta-feira) — ver DTHR
BBOX = (-49.30, -25.46, -49.23, -25.41)


def download(day: str = DAY):
    RAW.mkdir(parents=True, exist_ok=True)
    for f in ("linhas", "shapeLinha", "pontosLinha", "veiculos"):
        p = RAW / f"{day}_{f}.json"
        if not p.exists():
            subprocess.run(f"curl -s -O {BASE}/{day}_{f}.json.xz && xz -d {day}_{f}.json.xz", shell=True, cwd=RAW, check=True)


def pings(day: str = DAY) -> pd.DataFrame:
    out = PROC / "urbs_pings.parquet"
    if out.exists():
        return pd.read_parquet(out)
    rows = []
    with open(RAW / f"{day}_veiculos.json") as fh:
        for ln in fh:
            try:
                r = json.loads(ln)
                lat = float(r["LAT"].replace(",", ".")); lon = float(r["LON"].replace(",", "."))
            except Exception:
                continue
            if BBOX[0] < lon < BBOX[2] and BBOX[1] < lat < BBOX[3]:
                rows.append((r["VEIC"], r["COD_LINHA"], r["DTHR"], lat, lon))
    df = pd.DataFrame(rows, columns=["veic", "linha", "dthr", "lat", "lon"])
    df["t"] = pd.to_datetime(df.dthr, format="%d/%m/%Y %H:%M:%S")
    area = gpd.read_file(PROC / "study_area.geojson").to_crs(31982).union_all().buffer(150)
    g = gpd.GeoSeries(gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(31982)
    df = df[g.within(area).values].drop(columns="dthr").sort_values(["veic", "t"]).drop_duplicates(["veic", "t"]).reset_index(drop=True)
    df.to_parquet(out)
    return df


def trips(df: pd.DataFrame, gap_s: int = 90, min_m: float = 300) -> pd.DataFrame:
    """Divide em viagens: nova viagem quando muda a linha, o intervalo entre pings passa de gap_s ou o ônibus sai da área."""
    d = df.sort_values(["veic", "t"]).copy()
    new = (d.veic != d.veic.shift()) | (d.linha != d.linha.shift()) | ((d.t - d.t.shift()).dt.total_seconds() > gap_s)
    d["trip"] = new.cumsum()
    g = gpd.GeoSeries(gpd.points_from_xy(d.lon, d.lat), crs=4326).to_crs(31982)
    d["x"], d["y"] = g.x.values, g.y.values
    d["dx"] = np.hypot(d.x.diff(), d.y.diff()).where(~new, 0)
    t = d.groupby("trip").agg(veic=("veic", "first"), linha=("linha", "first"), t0=("t", "min"), t1=("t", "max"), n=("t", "size"), dist_m=("dx", "sum"))
    t = t[(t.dist_m >= min_m) & (t.n >= 8)]
    d = d[d.trip.isin(t.index)]
    d.to_parquet(PROC / "urbs_pings_trips.parquet")
    t.to_parquet(PROC / "urbs_trips.parquet")
    return t


if __name__ == "__main__":
    download()
    p = pings()
    print("pings:", len(p), "veículos:", p.veic.nunique(), "linhas:", p.linha.nunique(), p.t.min(), p.t.max())
    t = trips(p)
    print("viagens:", len(t), "linhas:", t.linha.nunique())
    print(t.groupby(t.t0.dt.hour).size().to_string())
