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
COL = {"asis": T.MUTED, "tobe_pi": T.AMBER, "tobe": T.TEAL, "tobe_fake": T.PURPLE, "tobe_bus2": T.BLUE, "tobe_gw": T.GREEN}
LAB = {"asis": "As-Is (actuated)", "tobe_pi": "PI sobre programas fixos", "tobe": "Actuated + prioridade ao ônibus", "tobe_fake": "Ablação (ônibus falsos)", "tobe_bus2": "Prioridade condicional", "tobe_gw": "Onda verde (Mariano Torres)"}
SHOW = ["asis", "tobe_pi", "tobe", "tobe_gw"]


def bars(res, metrics, titles, fname, ncols=4, h=2.5):
    wins = [w for w in ("am", "pm") if w in res]
    fig, axs = plt.subplots(1, len(metrics), figsize=(7.2, h))
    axs = np.atleast_1d(axs)
    for ax, m, ti in zip(axs, metrics, titles):
        x = np.arange(len(wins)); w = 0.2
        for i, s in enumerate(SHOW):
            vals = [res[k][s][m]["mean"] for k in wins if s in res[k]]
            err = [res[k][s][m]["ci95"] for k in wins if s in res[k]]
            ax.bar(x[:len(vals)] + (i - 1.5) * w, vals, w, yerr=err, color=COL[s], label=LAB[s], capsize=2, error_kw=dict(lw=.8))
        ax.set_xticks(x, ["Manhã" if k == "am" else "Tarde" for k in wins]); ax.set_title(ti, fontsize=8)
    axs[0].legend(fontsize=6.5, frameon=False, loc="upper center", bbox_to_anchor=(2.0, -.18), ncol=2)
    fig.tight_layout(); fig.savefig(FIG / fname); plt.close(fig)


def sweep_fig():
    sw = json.loads((OUT / "m4_sweep.json").read_text())
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.5))
    for ax, (m, ti) in zip(axs, [("speed_kmh", "Velocidade média (km/h)"), ("teleports", "Teleports"), ("q_p95_m", "Fila p95 (m)")]):
        for s in ("asis", "tobe"):
            ks = sorted((k for k in sw if s in sw[k]), key=float)
            y = np.array([sw[k][s][m]["mean"] for k in ks]); e = np.array([sw[k][s][m]["ci95"] or 0 for k in ks])
            ax.errorbar([float(k) for k in ks], y, yerr=e, marker="o", ms=4, lw=1.4, capsize=2, color=COL[s], label=LAB[s])
        ax.set_title(ti, fontsize=8); ax.set_xlabel("fator de demanda")
    h, l = axs[0].get_legend_handles_labels()
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=7, frameon=False)
    fig.savefig(FIG / "m4_sweep.png"); plt.close(fig)


def all_m4():
    FIG.mkdir(exist_ok=True)
    res = json.loads((OUT / "m4_results.json").read_text())
    bars(res, ["speed_kmh", "q_p95_m", "teleports"], ["Velocidade média (km/h)", "Fila p95 (m)", "Teleports"], "m4_trafego.png")
    bars(res, ["CO2_t_window", "NOx_kg_window", "CO2_g_per_vkm"], ["CO₂ na janela (t)", "NOx na janela (kg)", "CO₂ por veículo-km (g)"], "m4_emis.png")
    bars(res, ["Leq_cortn_dba", "Leq_harm_dba"], ["Leq CoRTN (dB)", "Leq harmonoise (dB)"], "m4_ruido.png", h=2.4)
    sweep_fig()


if __name__ == "__main__":
    all_m4()
