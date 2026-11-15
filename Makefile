# Projeto 1 — Mobilidade Urbana (UTFPR). Requer: uv, typst.  `make help` lista os alvos.
.PHONY: help data dashboard report-m1 net calibrate baseline report-m2 tune evaluate active report-m3 report-m4 mqtt test
help:        ; @grep -E '^[a-z0-9-]+:' Makefile | cut -d: -f1 | tr '\n' ' '; echo
# --- M1 ---
data:        ; uv run python -m src.m1.geo && uv run python -m src.m1.layers && uv run python -c "from src.m1 import traffic; traffic.make_placeholders()" && uv run python -m src.m1.urbs
dashboard:   ; uv run streamlit run app/dashboard.py
report-m1:   ; uv run python -m src.m1.figures && cd report && typst compile m1.typ m1.pdf
# --- M2 ---
net:         ; uv run python -m src.cps.sumo_net base && uv run python -m src.cps.sumo_net active && uv run python -m src.cps.sumo_net tobe
calibrate:   ; uv run python -c "from src.cps import vtypes; vtypes.write()" && sim/run_cal.sh
baseline:    ; uv run python -m src.cps.baseline
report-m2:   ; uv run python -m src.cps.figures_m2 && uv run python -m src.cps.report_data && cd report && typst compile m2.typ m2.pdf
# --- M3 ---
tune:        ; uv run python -m src.cps.tune
mqtt:        ; uv run python -m src.cps.mqtt_demo
report-m3:   ; uv run python -m src.cps.sensing && uv run python -m src.cps.report_data && cd report && typst compile m3.typ m3.pdf
# --- M4 ---
evaluate:    ; uv run python -m src.cps.evaluate run && uv run python -m src.cps.evaluate summary
active:      ; uv run python -m src.cps.active_eval
report-m4:   ; uv run python -m src.cps.figures_m4 && uv run python -m src.cps.report_data && cd report && typst compile m4.typ m4.pdf
test:        ; uv run pytest -q
