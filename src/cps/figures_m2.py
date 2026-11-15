"""Figuras e tabelas do memorial M2 (lê data/processed/m2_*)."""
from __future__ import annotations
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
import src.m1.figures  # aplica rcParams
from src.m1 import theme as T
from .common import OUT, ROOT

FIG = ROOT / "report" / "figures"


def geh_fig():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, w, lbl in zip(axs, ("am", "pm"), ("Pico da manhã", "Pico da tarde")):
        p = OUT / f"m2_geh_{w}.csv"
        if not p.exists():
            continue
        m = pd.read_csv(p).sort_values("geh").reset_index(drop=True)
        ax.bar(m.index, m.geh, color=[T.TEAL if g < 5 else T.RED for g in m.geh], width=.8)
        ax.axhline(5, color=T.INK, ls="--", lw=1)
        ax.set_title(f"{lbl}: {100 * (m.geh < 5).mean():.0f}% com GEH < 5", fontsize=9)
        ax.set_xlabel("aproximação monitorada (ordenada)")
    axs[0].set_ylabel("GEH")
    fig.tight_layout(); fig.savefig(FIG / "m2_geh.png"); plt.close(fig)


def scatter_fig():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for ax, w, lbl in zip(axs, ("am", "pm"), ("Manhã", "Tarde")):
        p = OUT / f"m2_geh_{w}.csv"
        if not p.exists():
            continue
        m = pd.read_csv(p)
        ax.scatter(m.obs_vph, m.sim_vph, color=T.BLUE, s=22)
        mx = float(max(m.obs_vph.max(), m.sim_vph.max())) * 1.05
        ax.plot([0, mx], [0, mx], color=T.MUTED, lw=1); ax.set_xlim(0, mx); ax.set_ylim(0, mx)
        ax.set_xlabel("observado provisório (veíc/h)"); ax.set_title(lbl, fontsize=9)
    axs[0].set_ylabel("simulado (veíc/h)")
    fig.tight_layout(); fig.savefig(FIG / "m2_scatter.png"); plt.close(fig)


def emis_fig():
    b = json.loads((OUT / "m2_baseline.json").read_text())
    fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.4))
    for ax, (k, lbl) in zip(axs, [("CO2", "CO₂ (t)"), ("NOx", "NOx (kg)"), ("CO", "CO (kg)"), ("PMx", "MP escapamento (kg)")]):
        vals = [b[w]["window_kg"][k] / (1000 if k == "CO2" else 1) for w in b]
        ax.bar([b[w]["label"] for w in b], vals, color=[T.TEAL, T.AMBER][:len(vals)], width=.6)
        ax.set_title(lbl, fontsize=8); ax.tick_params(axis="x", labelsize=6.5, rotation=20)
    fig.tight_layout(); fig.savefig(FIG / "m2_emis.png"); plt.close(fig)


def all_m2():
    import shutil
    FIG.mkdir(exist_ok=True)
    for f in OUT.glob("m2_*.json"):
        shutil.copy(f, FIG / f.name)
    geh_fig(); scatter_fig(); emis_fig()


if __name__ == "__main__":
    all_m2()
