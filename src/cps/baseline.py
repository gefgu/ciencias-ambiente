"""Pegada de carbono e poluentes do As-Is nas janelas de pico (memorial de cálculo do M2).

Contabilidade: emissões e distância percorrida vêm do MESMO edgeData (0–3600 s: a hora de demanda, todos os veículos, inclusive os que ainda
estão na rede), de modo que g/km não mistura períodos nem populações. Atrasos vêm dos veículos concluídos (viés para baixo,
reportado junto de inseridos/concluídos/em espera).

Ressuspensão: US EPA AP-42 cap. 13.2.1, vias pavimentadas, E = k·sL^0,91·W^1,02·(1−P/4N)  [g/VMT],
k(MP2,5)=0,15  k(MP10)=0,62 g/VMT; W em toneladas curtas. PREMISSAS: sL=0,03 g/m² (Tabela 13.2.1-2, ADT>10 000), W da frota simulada,
P=150 dias com chuva ≥0,254 mm (a confirmar com dados do INMET) e N=365.
"""
from __future__ import annotations
import json
import xml.etree.ElementTree as ET
import pandas as pd
from src.m1.traffic import PH
from .common import OUT, WORK, WINDOWS, window_scale
from . import vtypes

SL_G_M2 = 0.03
RAIN_P, RAIN_N = 150, 365
K_PM = {"PM25": 0.15, "PM10": 0.62}
MI_PER_KM = 0.621371
MASS_T = {"car_g": 1.2, "car_d": 1.4, "moto": 0.2, "bus": 13.0, "truck": 14.0}  # massa média por classe (t métricas) — PREMISSA
SHORT_TON = 1.10231


def fleet_weight_short_tons() -> float:
    m = vtypes.mix()
    return SHORT_TON * sum(m[k] * MASS_T[k] for k in m)


def resusp_g_per_km(pm: str) -> float:
    w = fleet_weight_short_tons()
    return K_PM[pm] * SL_G_M2 ** 0.91 * w ** 1.02 * (1 - RAIN_P / (4 * RAIN_N)) * MI_PER_KM


def read(win: str, tag: str = "asis") -> dict:
    prof = pd.read_csv(PH / "hourly_profile.csv").fracao_vpd.tolist()
    emi = pd.DataFrame([{k: float(v) for k, v in x.attrib.items() if k != "id"} for x in ET.parse(WORK / f"edge_emi1h_{tag}_{win}.xml").iter("edge")])
    flw = pd.DataFrame([{k: float(v) for k, v in x.attrib.items() if k != "id"} for x in ET.parse(WORK / f"edge_flow1h_{tag}_{win}.xml").iter("edge")])
    tot_mg = {k: float(emi[f"{k}_abs"].sum()) for k in ("CO2", "CO", "NOx", "PMx", "HC", "fuel")}
    dist_m = float((flw.speed * flw.sampledSeconds).sum())   # distância = velocidade média × segundos amostrados, somada nas arestas
    km = dist_m / 1000                       # veículos-km de TODOS os veículos, mesmo período das emissões
    spd = float(dist_m / flw.sampledSeconds.sum() * 3.6)  # velocidade média espacial na rede
    ti = pd.DataFrame([{"dur": float(x.get("duration")), "loss": float(x.get("timeLoss")), "wait": float(x.get("waitingTime")), "len": float(x.get("routeLength")),
                        "type": x.get("vType")} for x in ET.parse(WORK / f"tripinfo_{tag}_{win}.xml").iter("tripinfo")])
    root = ET.parse(WORK / f"stats_{tag}_{win}.xml").getroot()
    v = root.find("vehicles").attrib
    vs = root.find("vehicleTripStatistics").attrib
    bus = ti[ti.type == "bus"]
    sc = window_scale(win, prof)
    kg = lambda mg: mg / 1e6
    from .evaluate import noise_levels, metrics as _m
    nl = noise_levels(tag, win)
    mm = _m(tag, win)
    return {"window": win, "label": WINDOWS[win]["label"], "scale_to_window": round(sc, 3),
            "loaded": int(v["loaded"]), "inserted": int(v["inserted"]), "finished": len(ti), "running_at_end": int(v["running"]), "waiting_to_enter_at_end": int(v["waiting"]),
            "depart_delay_s": round(float(vs["departDelay"]), 1), "veh_km": round(km, 1), "mean_speed_kmh": round(spd, 1),
            "mean_delay_finished_s": round(float(ti.loss.mean()), 1), "mean_wait_finished_s": round(float(ti.wait.mean()), 1), "teleports": int(root.find("teleports").attrib["total"]),
            "bus_n": len(bus), "bus_mean_dur_s": round(float(bus.dur.mean()), 1) if len(bus) else None,
            "total_kg": {k: round(kg(x), 2) for k, x in tot_mg.items()}, "window_kg": {k: round(kg(x) * sc, 2) for k, x in tot_mg.items()},
            "g_per_vkm": {k: round(tot_mg[k] / 1000 / km, 3) for k in ("CO2", "CO", "NOx", "PMx", "HC")},
            "fleet_weight_short_tons": round(fleet_weight_short_tons(), 2),
            "resuspension_window_kg": {pm: round(resusp_g_per_km(pm) * km * sc / 1000, 2) for pm in K_PM},
            "resuspension_g_per_km": {pm: round(resusp_g_per_km(pm), 4) for pm in K_PM},
            "noise_leq_dba": {k: round(x, 1) for k, x in nl.items()}, "queue_p95_m": round(mm["q_p95_m"], 1), "queue_max_mean_m": round(mm["q_max_mean_m"], 1)}


def main():
    res = {w: read(w) for w in ("am", "pm") if (WORK / f"edge_emi1h_asis_{w}.xml").exists()}
    (OUT / "m2_baseline.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, ensure_ascii=False))
