#!/bin/sh
set -e
cd "$(dirname "$0")/.."
uv run python - <<'PY' > sim/work/round2.log 2>&1
from concurrent.futures import ProcessPoolExecutor
from src.cps import evaluate as E
jobs = [(s, w, k, 1.0, f"{s}_s{k}") for w in ("am", "pm") for s in ("tobe_gw", "tobe_fixed90") for k in E.SEEDS]
jobs += [(s, "am", k, 0.6, f"sw0.6_{s}_s{k}") for s in E.SWEEP_SCENS for k in (1, 2, 3)]
jobs += [(s, w, 1, 1.0, f"{s}_s1") for s in ("tobe", "tobe_bus2") for w in ("am", "pm")]
with ProcessPoolExecutor(10) as ex:
    out = list(ex.map(E._one, jobs))
E._save_decisions(out)
print(len(out))
PY
uv run python -m src.cps.evaluate summary > sim/work/round2_summary.log 2>&1
uv run python -m src.cps.extras > sim/work/round2_extras.log 2>&1
uv run python -m src.cps.baseline > sim/work/round2_baseline.log 2>&1
echo done > sim/work/round2.done
