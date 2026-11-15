#!/bin/sh
# Recalcula tudo com as saídas novas (fila, harmonoise, 1 h) e os cenários novos. Roda em ~1 h em 12 núcleos.
set -e
cd "$(dirname "$0")/.."
uv run python -c "from src.cps import simrun, common; simrun.simulate('am', routes=common.SIM/'routes_asis_am.rou.xml')" &
uv run python -c "from src.cps import simrun, common; simrun.simulate('pm', routes=common.SIM/'routes_asis_pm.rou.xml')" &
uv run sumo -c sim/asis_am.sumocfg --no-warnings false --output-prefix diag_ --duration-log.disable true > sim/work/warnings_asis_am.log 2>&1 &
wait
uv run python -m src.cps.evaluate run > sim/work/final_eval.log 2>&1
uv run python -m src.cps.evaluate sweep > sim/work/final_sweep.log 2>&1
uv run python -m src.cps.evaluate summary > sim/work/final_summary.log 2>&1
uv run python -m src.cps.baseline > sim/work/final_baseline.log 2>&1
echo done > sim/work/final.done
