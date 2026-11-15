"""Estatísticas auxiliares do M4 reproduzíveis por código: diagnóstico de teleports, testes pareados dos modos ativos e contagem de testes."""
from __future__ import annotations
import collections, json, re
import pandas as pd
from scipy import stats as st
from .common import OUT, WORK, SIM


def teleports(log=WORK / "warnings_asis_am.log") -> dict:
    """Tabela de teleports de UMA rodada do As-Is (semente 1, manhã) com avisos ligados: motivo e arestas/junções."""
    import sumolib
    L = [l for l in open(log) if "Teleporting vehicle" in l]
    reason, lane = collections.Counter(), collections.Counter()
    for l in L:
        m = re.search(r"waited too long \(([^)]*)\)", l); reason[m.group(1) if m else "?"] += 1
        m = re.search(r"lane='([^']+)'", l)
        if m:
            lane[m.group(1).rsplit("_", 1)[0]] += 1
    net = sumolib.net.readNet(str(SIM / "net.net.xml"))
    top = []
    for e, c in lane.most_common(10):
        if e.startswith(":"):
            nd = net.getNode(e[1:].rsplit("_", 1)[0]); top.append({"where": "junction", "teleports": c, "streets": sorted({x.getName() for x in nd.getIncoming() if x.getName()})[:3]})
        else:
            top.append({"where": "edge", "teleports": c, "street": net.getEdge(e).getName()})
    tot = len(L)
    out = {"seed": 1, "window": "am", "total": tot, "by_reason": dict(reason), "distinct_edges": len(lane), "top10_detail": top,
           "top10_share": sum(c for _, c in lane.most_common(10)) / tot if tot else 0,
           "top10_laurindo": sum(1 for t in top if t.get("street") == "Rua Conselheiro Laurindo")}
    (OUT / "m4_teleports.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def extra() -> dict:
    a = pd.read_csv(OUT / "m4_active_runs.csv")
    g = lambda s: a[a.scenario == s].set_index("seed")
    b, c, d = g("asis_act"), g("bike_only"), g("tobe_act")
    pr = lambda x: {"diff": float((x.car_delay_s - b.car_delay_s).mean()), "p": float(st.ttest_rel(x.car_delay_s, b.car_delay_s).pvalue)}
    res = json.loads((OUT / "m4_results.json").read_text())
    n = sum(1 for w in ("am", "pm") for s in res[w] if s != "asis" for c_ in res[w][s] if res[w][s][c_].get("p_paired") is not None)
    out = {"active_paired": {"bike_only_vs_asis_car_delay": pr(c), "tobe_act_vs_asis_car_delay": pr(d)}, "n_tests": n}
    (OUT / "m4_extra.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    print(teleports()["total"], extra())
