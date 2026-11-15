"""Noise: NBR 10151 limits + first-order CoRTN estimate (placeholder-grade until field calibration)."""
from __future__ import annotations
import math

# ABNT NBR 10151:2019 — limites RLAeq (dB) por tipo de área (diurno, noturno). Conferir a numeração da tabela na norma.
NBR10151 = {"Residencial rural": (40, 35), "Estritamente residencial / escolas / hospitais": (50, 45), "Mista, predominância residencial": (55, 50), "Mista, comercial/administrativa": (60, 55),
            "Mista, cultura/lazer/turismo": (65, 55), "Predominantemente industrial": (70, 60)}


def cortn_l10_1h(q_vph: float, v_kmh: float, heavy_pct: float, d_m: float, h_m: float = 0.7) -> float:
    """CoRTN (UK DoT 1988) basic noise level L10(1h) [dB(A)] at distance d from the nearest carriageway EDGE (not the axis); h = receiver height above source (~0.7 m for a 1.2 m mic).
    VALIDITY: CoRTN assumes free-flowing traffic; the speed term is not validated below ~20 km/h (stop-and-go, signals).
    q: veh/h, v: mean speed km/h, heavy_pct: % heavy vehicles. Gradient/surface/reflection corrections omitted."""
    q = max(q_vph, 1.0)
    base = 42.2 + 10 * math.log10(q)
    speed_hgv = 33 * math.log10(v_kmh + 40 + 500 / v_kmh) + 10 * math.log10(1 + 5 * heavy_pct / v_kmh) - 68.8
    d_prime = math.sqrt((d_m + 3.5) ** 2 + h_m ** 2)
    return base + speed_hgv - 10 * math.log10(d_prime / 13.5)


def leq_from_l10(l10: float) -> float:
    """Approximate Leq(1h) ≈ L10(1h) − 3 dB (free-flowing traffic, CoRTN guidance)."""
    return l10 - 3.0


def reduction_db(q1: float, q2: float) -> float:
    """Pure flow effect: 10·log10(q2/q1)."""
    return 10 * math.log10(q2 / q1)
