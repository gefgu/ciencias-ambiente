"""Preliminary As-Is emission baseline (pre-M2). Factors are ORDER-OF-MAGNITUDE PLACEHOLDERS (g/km at ~50 km/h);
M2 replaces them with SUMO PHEMlight/HBEFA outputs."""
from __future__ import annotations
import pandas as pd

# g/km per vehicle, reference speed 50 km/h
FACTORS = pd.DataFrame({
    "classe": ["carros", "motos", "onibus", "caminhoes", "bicicletas"],
    "CO2": [170, 85, 950, 620, 0], "NOx": [0.25, 0.20, 7.0, 4.5, 0], "CO": [1.8, 5.0, 1.5, 1.8, 0], "PM25": [0.003, 0.02, 0.12, 0.08, 0],
}).set_index("classe")
# adimensional speed correction, normalised to 1.0 at 50 km/h (U-shaped: stop-and-go penalised)
_f = lambda v: 0.5 + 15 / v + (v / 120) ** 2


def speed_factor(v_kmh: float) -> float:
    return _f(max(v_kmh, 5.0)) / _f(50.0)


def baseline_g_per_h(vph: float, mix: dict[str, float], v_kmh: float, length_km: float = 1.0) -> dict[str, float]:
    """Emission rate [g/h] over `length_km` of road, for flow vph, class shares `mix` (keys of FACTORS), mean speed v."""
    k = speed_factor(v_kmh) * length_km * vph
    return {p: float(sum(FACTORS.loc[c, p] * s for c, s in mix.items()) * k) for p in FACTORS.columns}
