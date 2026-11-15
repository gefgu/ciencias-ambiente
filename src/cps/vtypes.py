"""Frota (M2). Classes de emissão: HBEFA3 embutidas no SUMO 1.28.

Limitações assumidas e documentadas:
 - motos usam a classe HBEFA4/MC_4S_le250cc_Euro-4 (motocicleta 4 tempos até 250 cc, Euro 4); os demais veículos seguem HBEFA3 (carros, ônibus, caminhões)
 - bicicletas e pedestres entram só no M3
 - participações (mix) vêm de data/placeholders/field_counts.csv (PROVISÓRIO) renormalizadas sem bicicletas
"""
from __future__ import annotations
import pandas as pd
from src.m1.traffic import PH
from .common import SIM

TYPES = {  # id: (vClass, emissionClass, length, maxSpeed, accel, decel)
    "car_g": ("passenger", "HBEFA3/PC_G_EU4", 4.5, 16.7, 2.6, 4.5),
    "car_d": ("passenger", "HBEFA3/PC_D_EU4", 4.5, 16.7, 2.6, 4.5),
    "moto": ("motorcycle", "HBEFA4/MC_4S_le250cc_Euro-4", 2.2, 16.7, 4.0, 5.0),
    "bus": ("bus", "HBEFA3/Bus", 12.0, 13.9, 1.2, 4.0),
    "truck": ("truck", "HBEFA3/HDV_D_EU4", 9.0, 13.9, 1.0, 4.0),
}
CAR_DIESEL_SHARE = 0.10  # PROVISÓRIO (flex/gasolina dominam a frota leve)


def mix() -> dict[str, float]:
    f = pd.read_csv(PH / "field_counts.csv")
    w = (f.vpd_total.values[:, None] * f[["share_carros", "share_motos", "share_onibus", "share_caminhoes"]].values).sum(0)
    w = w / w.sum()
    return {"car_g": w[0] * (1 - CAR_DIESEL_SHARE), "car_d": w[0] * CAR_DIESEL_SHARE, "moto": w[1], "bus": w[2], "truck": w[3]}


def write():
    rows = "\n".join(f'  <vType id="{k}" vClass="{v[0]}" emissionClass="{v[1]}" length="{v[2]}" maxSpeed="{v[3]}" accel="{v[4]}" decel="{v[5]}" sigma="0.5" color="{c}"/>'
                     for (k, v), c in zip(TYPES.items(), ["0,100,200", "20,60,120", "217,119,6", "15,118,110", "124,58,237"]))
    (SIM / "vtypes.add.xml").write_text(f"<additional>\n{rows}\n</additional>\n")
