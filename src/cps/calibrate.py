"""Calibração GEH do As-Is: ≥85% das arestas monitoradas com GEH<5 (manual, Fase 2).

ATENÇÃO: as contagens observadas ainda são PROVISÓRIAS; o procedimento é real, o resultado só vale após as contagens de campo.
"""
from __future__ import annotations
import json
import pandas as pd
from . import demand, simrun
from .common import OUT, SIM, WORK


def calibrate(win: str = "am", max_iter: int = 5, tol_pass: float = 0.85) -> dict:
    obs = demand.observed_counts(win)
    obs["target_vph"] = obs.obs_vph
    hist, best = [], None
    for it in range(max_iter):
        seed = 42 + it
        info = demand.build_routes(obs, win, seed=seed)
        r = simrun.simulate(win, seed=1)
        assert r["rc"] == 0, r["err"]
        sim = simrun.read_flow(win, "asis")
        m = obs.merge(sim, on="edge", how="left").fillna({"sim_vph": 0})
        m["geh"] = [simrun.geh(a, b) for a, b in zip(m.sim_vph, m.obs_vph)]
        passed = float((m.geh < 5).mean())
        hist.append({"iter": it, "vehicles": info["vehicles"], "pct_geh_lt5": round(100 * passed, 1), "mean_geh": round(float(m.geh.mean()), 2)})
        if best is None or passed > best[0]:
            best = (passed, m.copy(), (WORK / f"routes_{win}.rou.xml").read_text())
        if passed >= tol_pass:
            break
        # realimentação AMORTECIDA: raiz do erro relativo, alvo limitado a [0,7; 1,5]× observado (evita explosão de demanda)
        ratio = ((m.obs_vph / m.sim_vph.where(m.sim_vph > 0, m.obs_vph * 0.5)) ** 0.5).clip(.8, 1.25)
        obs["target_vph"] = (obs.target_vph.values * ratio.values).clip(0.7 * obs.obs_vph.values, 1.5 * obs.obs_vph.values)
    passed, m, routes_txt = best
    (WORK / f"routes_{win}.rou.xml").write_text(routes_txt)  # fixa a melhor iteração como cenário As-Is
    (SIM / f"routes_asis_{win}.rou.xml").write_text(routes_txt)
    simrun.simulate(win, routes=SIM / f"routes_asis_{win}.rou.xml", seed=1)  # regera saídas e o .sumocfg portável da melhor iteração
    m["window"] = win
    OUT.mkdir(parents=True, exist_ok=True)
    m.round(2).to_csv(OUT / f"m2_geh_{win}.csv", index=False)
    w = (m.obs_vph * (m.geh < 5)).sum() / m.obs_vph.sum()
    res = {"window": win, "history": hist, "final_pct_geh_lt5": round(100 * passed, 1), "weighted_pct_geh_lt5": round(100 * float(w), 1),
           "sim_over_obs_total": round(float(m.sim_vph.sum() / m.obs_vph.sum()), 3), "n_links": len(m), "n_points": int(m.point_id.nunique()),
           "ok": passed >= tol_pass, "placeholder_observed": True}
    (OUT / f"m2_calibration_{win}.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    import sys
    print(calibrate(sys.argv[1] if len(sys.argv) > 1 else "am"))
