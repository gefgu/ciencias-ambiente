"""Static figures for the Typst report (same data + palette as the dashboard)."""
from __future__ import annotations
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from . import data, theme as T, noise
from .geo import ROOT

OUT = ROOT / "report" / "figures"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": T.MUTED, "axes.labelcolor": T.INK, "text.color": T.INK, "xtick.color": T.MUTED, "ytick.color": T.MUTED,
                     "figure.dpi": 200, "savefig.bbox": "tight", "axes.grid": True, "grid.color": "#E5E3DA", "grid.linewidth": .6})


def _save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)


def map_fig(d):
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    ax.grid(False)
    ax.set_aspect("equal")
    proj = 31982
    d["area"].to_crs(proj).plot(ax=ax, facecolor=T.TEAL + "18", edgecolor=T.TEAL, linewidth=1.6)
    sv = d["sistema_viario"].to_crs(proj)
    widths = {"CENTRAL": 2.4, "PRIORITÁRIA": 2.0, "SETORIAL 1": 1.5, "SETORIAL 2": 1.2}
    for k, g in sv.groupby("SIST_VIARI"):
        g.plot(ax=ax, color=T.CLASS_COLORS.get(k, "#D1D5DB"), linewidth=widths.get(k, .7), label=k.title(), zorder=2)
    d["ciclovias"].to_crs(proj).plot(ax=ax, color=T.GREEN, linewidth=.9, zorder=3)
    d["calcadao"].to_crs(proj).plot(ax=ax, color=T.CALCADAO, zorder=3)
    d["terminais"].to_crs(proj).plot(ax=ax, color=T.BLUE, markersize=40, marker="s", zorder=4)
    p = d["points"]
    g = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p.lon, p.lat), crs=4326).to_crs(proj)
    g.plot(ax=ax, color=T.RED, markersize=55, edgecolor="white", linewidth=1, zorder=5)
    for r in g.itertuples():
        ax.annotate(r.point_id, (r.geometry.x, r.geometry.y), xytext=(5, 5), textcoords="offset points", fontsize=7.5, fontweight="bold", zorder=6)
    from matplotlib.lines import Line2D
    extra = [Line2D([], [], color=T.GREEN, lw=1.5, label="Ciclovia"), Line2D([], [], color=T.CALCADAO, lw=4, label="Calçadão"),
             Line2D([], [], color=T.BLUE, marker="s", ls="", label="Terminal"), Line2D([], [], color=T.RED, marker="o", ls="", label="Ponto de medição")]
    h, _ = ax.get_legend_handles_labels()
    ax.legend(handles=h + extra, loc="lower left", fontsize=7, frameon=True, framealpha=.9, ncol=2)
    ax.set_axis_off()
    _save(fig, "mapa")


def traffic_fig(d):
    p = d["points"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [3, 2]})
    bottom = np.zeros(len(p))
    for m in data.MODES:
        v = (p.vpd_total * p[f"share_{m}"]).values / 1000
        axs[0].bar(p.point_id, v, bottom=bottom, color=T.MODE_COLORS[m], label=T.MODE_LABELS[m], width=.65)
        bottom += v
    axs[0].set_ylabel("mil veículos/dia")
    axs[0].legend(fontsize=7, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.15))
    h = d["hourly"]
    axs[1].plot(h.hora, h.fracao_vpd * 100, color=T.TEAL, lw=2)
    for a, b in [(6.5, 9), (17, 19)]:
        axs[1].axvspan(a, b, color=T.AMBER, alpha=.2, lw=0)
    axs[1].set_xlabel("hora do dia")
    axs[1].set_ylabel("% do VPD")
    axs[1].set_xticks(range(0, 24, 4))
    fig.tight_layout()
    _save(fig, "trafego")


def noise_fig(d):
    p = d["points"]
    c = data.cortn_table(p, "manha", 18)
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    x = np.arange(len(p))
    w = .36
    ax.bar(x - w / 2, p.leq_dba, w, color=T.BLUE, label="Leq medido")
    ax.bar(x + w / 2, p.residual_dba, w, color="#9CA3AF", label="Residual")
    ax.scatter(x, c.values, marker="D", color=T.AMBER, zorder=5, label="CoRTN (10 m, 18 km/h)")
    ax.axhline(noise.NBR10151["Mista, comercial/administrativa"][0], color=T.RED, ls="--", lw=1.2, label="Limite NBR 10151 (60 dB)")
    ax.set_xticks(x, p.point_id)
    ax.set_ylim(40, 85)
    ax.set_ylabel("dB(A)")
    ax.legend(fontsize=7, ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.12))
    _save(fig, "ruido")


def emis_fig(d):
    em = data.emissions_table(d["points"], "manha", 18)
    fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.2))
    for ax, (k, lbl) in zip(axs, [("CO2", "CO₂"), ("NOx", "NOx"), ("CO", "CO"), ("PM25", "MP2,5")]):
        ax.bar(em.point_id, em[k], color=T.TEAL, width=.65)
        ax.set_title(f"{lbl} (kg/h·km)", fontsize=8)
        ax.tick_params(axis="x", labelrotation=90, labelsize=7)
    fig.tight_layout()
    _save(fig, "emissoes")


def bus_fig(d):
    order = ["Pico manhã (06:30–09:00)", "Entrepico (10:00–16:00)", "Pico tarde (17:00–19:00)"]
    k = d["bus_kpis"].groupby("window")[["vel_media_kmh", "pct_parado"]].mean().reindex(order)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.2))
    lab = ["Manhã", "Entrepico", "Tarde"]
    axs[0].bar(lab, k.vel_media_kmh, color=T.TEAL, width=.55)
    axs[0].set_ylabel("velocidade média (km/h)")
    axs[1].bar(lab, k.pct_parado, color=T.RED, width=.55)
    axs[1].set_ylabel("% do tempo parado (<5 km/h)")
    fig.tight_layout()
    _save(fig, "onibus")


def all_figs():
    d = data.load()
    for f in (map_fig, traffic_fig, noise_fig, emis_fig, bus_fig):
        f(d)
    export_tables()
    return sorted(p.name for p in OUT.glob("*"))



def export_tables():
    """JSON/CSV consumed by report/m1.typ so numbers in the text come from the pipeline."""
    import json
    d = data.load()
    p = d["points"].copy()
    c = data.cortn_table(p, "manha", 18)
    e = data.emissions_table(p, "manha", 18).set_index("point_id")
    p["cortn_dba"] = c.round(1).values
    p["vph_manha"] = p["vph_manha"].round(0).astype(int)
    p["vph_tarde"] = p["vph_tarde"].round(0).astype(int)
    p["co2_kg_h_km"] = e.loc[p.point_id, "CO2"].round(0).values
    p["nox_kg_h_km"] = e.loc[p.point_id, "NOx"].round(1).values
    p[["point_id", "name", "lat", "lon", "vpd_total", "vph_manha", "vph_tarde", "leq_dba", "residual_dba", "cortn_dba",
       "limite_nbr10151", "co2_kg_h_km", "nox_kg_h_km"]].round(5).to_csv(OUT / "pontos.csv", index=False)
    k = d["bus_kpis"].groupby("window")[["vel_media_kmh", "pct_parado"]].mean().round(1)
    s = {k_: float(v) for k_, v in d["stats"].items()}
    s["bus"] = {w: r.to_dict() for w, r in k.iterrows()}
    s["n_acima_limite"] = int((p.leq_dba > 60).sum())  # provisório
    s["mix"] = {m: float((p.vpd_total * p[f"share_{m}"]).sum() / p.vpd_total.sum()) for m in data.MODES}
    from .network import build_graph
    from .urbs import CORE_BBOX
    s["n_nodes_core"] = build_graph(CORE_BBOX)[0].num_rows
    s["n_ciclorrotas"] = len(d["ciclorrotas"]); s["n_terminais"] = len(d["terminais"])
    (OUT / "stats.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    print(all_figs())
