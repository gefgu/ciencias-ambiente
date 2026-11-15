#!/bin/sh
set -e
cd "$(dirname "$0")/.."
uv run python -m src.cps.calibrate am > sim/work_cal_am.log 2>&1
uv run python -m src.cps.calibrate pm > sim/work_cal_pm.log 2>&1
