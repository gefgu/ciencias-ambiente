"""Shared helpers for the SUMO scenarios (M2–M4)."""
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path
import sumo

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "sim"
WORK = SIM / "work"
OUT = ROOT / "data" / "processed"
SUMO_HOME = Path(sumo.SUMO_HOME)
TOOLS = SUMO_HOME / "tools"
os.environ["SUMO_HOME"] = str(SUMO_HOME)
sys.path.insert(0, str(TOOLS))

# Janelas de pico do manual (horas) e fração do VPD (ver src/m1/traffic.py: perfil horário PROVISÓRIO)
WINDOWS = {"am": {"label": "06:30–09:00", "sim_hours": [7, 8], "hours": [(6, .5), (7, 1), (8, 1)]},   # sim_hours = horas cuja média define vph_peak
           "pm": {"label": "17:00–19:00", "sim_hours": [17, 18], "hours": [(17, 1), (18, 1)]}}


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def pytool(name: str, *args) -> subprocess.CompletedProcess:
    return run([sys.executable, TOOLS / name, *args])


def window_scale(win: str, profile: list[float]) -> float:
    """Fator para estender a hora simulada à janela: Σ fração(h)·peso / média das frações das horas que definem o volume simulado."""
    w = WINDOWS[win]
    ref = sum(profile[h] for h in w["sim_hours"]) / len(w["sim_hours"])  # mesma média usada em vph_peak
    return sum(profile[h] * f for h, f in w["hours"]) / ref
