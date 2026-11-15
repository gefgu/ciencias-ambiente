"""Figuras do relatório M4: As-Is × To-Be com IC 95% entre réplicas."""
from __future__ import annotations
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import src.m1.figures  # rcParams
from src.m1 import theme as T
from .common import OUT, ROOT

FIG = ROOT / "report" / "figures"
COL = {"asis": T.MUTED, "tobe_pi": T.AMBER, "tobe": T.TEAL, "tobe_fake": T.PURPLE}
LAB = {"asis": "As-Is (actuated)", "tobe_pi": "PI sobre programas fixos", "tobe": "To-Be (actuated + prioridade ao ônibus)", "tobe_fake": "Ablação (ônibus falsos)"}


def bars(res, metrics, titles, fname, ncols=4, h=2.5):
    wins = [w for w in ("am", "pm") if w in res]
    fig, axs = plt.subplots(1, len(metrics), figsize=(7.2, h))
    axs = np.atleast_1d(axs)
    for ax, m, ti in zip(axs, metrics, titles):
        x = np.arange(len(wins)); w = 0.2
        for i, s in enumerate(["asis", "tobe_pi", "tobe", "tobe_fake"]):
            vals = [res[k][s][m]["mean"] for k in wins if s in res[k]]
            err = [res[k][s][m]["ci95"] for k in wins if s in res[k]]
            ax.bar(x[:len(vals)] + (i - 1.5) * w, vals, w, yerr=err, color=COL[s], label=LAB[s], capsize=2, error_kw=dict(lw=.8))
        ax.set_xticks(x, ["Manhã" if k == "am" else "Tarde" for k in wins]); ax.set_title(ti, fontsize=8)
    axs[0].legend(fontsize=6.5, frameon=False, loc="upper center", bbox_to_anchor=(2.0, -.18), ncol=2)
    fig.tight_layout(); fig.savefig(FIG / fname); plt.close(fig)


def all_m4():
    FIG.mkdir(exist_ok=True)
    res = json.loads((OUT / "m4_results.json").read_text())
    bars(res, ["delay_s", "speed_kmh", "bus_delay_s"], ["Atraso médio (s)", "Velocidade média (km/h)", "Atraso dos ônibus (s)"], "m4_trafego.png")
    bars(res, ["CO2_t_window", "NOx_kg_window", "CO2_g_per_vkm"], ["CO₂ na janela (t)", "NOx na janela (kg)", "CO₂ por veículo-km (g)"], "m4_emis.png")
    bars(res, ["Leq_mean_dba"], ["Leq médio (dB, CoRTN 10 m)"], "m4_ruido.png", h=2.4)


if __name__ == "__main__":
    all_m4()
