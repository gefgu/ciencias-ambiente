import math
import pytest
from src.m1 import noise, emissions
from src.cps import greenwave, simrun
from src.cps.common import window_scale
from src.cps.controllers import Controller, Params, State
from src.cps.evaluate import _egy
from src.cps.sumo_net import repair_orphan_tls


def test_geh_known_values():
    assert simrun.geh(100, 100) == 0
    assert simrun.geh(60, 100) == pytest.approx(math.sqrt(2 * 40 ** 2 / 160))   # ≈ 4,47
    assert simrun.geh(0, 0) == 0


def test_window_scale_flat_profile():
    flat = [1 / 24] * 24
    assert window_scale("am", flat) == pytest.approx(2.5)   # 0,5 + 1 + 1 horas
    assert window_scale("pm", flat) == pytest.approx(2.0)


def test_cortn_flow_and_distance_monotonic():
    a = noise.cortn_l10_1h(1000, 40, 5, 10)
    assert noise.cortn_l10_1h(2000, 40, 5, 10) - a == pytest.approx(10 * math.log10(2), abs=1e-9)   # dobrar o fluxo: +3,01 dB
    assert noise.cortn_l10_1h(1000, 40, 5, 20) < a                                                  # afastar reduz o nível
    assert noise.reduction_db(100, 80) == pytest.approx(-0.969, abs=1e-3)


def test_energy_mean_of_db():
    assert _egy([60, 60]) == pytest.approx(60)
    assert _egy([60, 70]) == pytest.approx(10 * math.log10((1e6 + 1e7) / 2))   # ≈ 67,4 dB, não 65
    assert math.isnan(_egy([]))


def test_emission_speed_factor_reference():
    assert emissions.speed_factor(50) == pytest.approx(1.0)
    assert emissions.speed_factor(10) > 1.5   # para-e-anda penalizado


def test_greenwave_offset_arithmetic():
    offs = greenwave.ideal_offsets([0, 200, 400], 10.0, 90.0)   # 10 m/s
    assert offs == pytest.approx([0, 20, 40])
    assert greenwave.ideal_offsets([1000], 10.0, 90.0)[0] == pytest.approx(10.0)  # 100 s mod 90
    assert greenwave.wrap(80, 90) == pytest.approx(-10)
    assert greenwave.wrap(-80, 90) == pytest.approx(10)


def test_scale_durations_sums_to_cycle_and_keeps_yellow():
    d = [30, 3, 25, 3]
    g = [True, False, True, False]
    out = greenwave.scale_durations(d, g, 90.0)
    assert sum(out) == pytest.approx(90.0)
    assert out[1] == 3 and out[3] == 3


def test_repair_orphan_tls(tmp_path):
    xml = ('<net><junction id="A" type="traffic_light"/><junction id="B" type="traffic_light"/>'
           '<tlLogic id="A" type="actuated"/><connection from="x" to="y" tl="A" linkIndex="0"/>'
           '<connection from="x" to="z" tl="B" linkIndex="1"/></net>')
    f = tmp_path / "n.net.xml"; f.write_text(xml)
    assert repair_orphan_tls(f) == 1
    out = f.read_text()
    assert 'tl="B"' not in out and 'tl="A"' in out
    assert '<junction id="B" type="priority"/>' in out


def test_targeted_bus_priority_requires_next_phase_to_serve_bus():
    base = dict(phase=0, t_in_phase=20, is_green_phase=True, q_green=0, q_red=0, bus_on_red=True)
    plain = Controller(Params(bus_only=True))
    targeted = Controller(Params(bus_only=True, bus_targeted=True))
    assert plain.decide(State(**base, bus_next_serves=False))[0] == "switch"
    assert targeted.decide(State(**base, bus_next_serves=False))[0] == "hold"
    assert targeted.decide(State(**base, bus_next_serves=True))[0] == "switch"


def test_phase_at_pure_function():
    d = [30.0, 3.0, 25.0, 3.0]          # ciclo de 61 s
    assert greenwave.phase_at(d, 0.0) == (0, 30.0)
    k, rem = greenwave.phase_at(d, 31.0)
    assert k == 1 and rem == pytest.approx(2.0)
    k, rem = greenwave.phase_at(d, 33.0 + 10.0)
    assert k == 2 and rem == pytest.approx(15.0)
    assert greenwave.phase_at(d, 61.0 + 5.0) == greenwave.phase_at(d, 5.0)   # periodicidade


def test_phase_at_matches_offset_definition():
    """Com a fase principal começando em s_main, a posição no ciclo em t=0 é (s_main − off) mod C."""
    d = [30.0, 3.0, 25.0, 3.0]
    s_main = sum(d[:2])                  # fase principal = índice 2
    off = 20.0
    k, rem = greenwave.phase_at(d, (s_main - off) % sum(d))
    # o verde principal começa daqui a `off` segundos: tempo restante até o fim da fase atual + durações até o índice 2
    until_main = rem + sum(d[k + 1:2]) if k < 2 else None
    assert until_main == pytest.approx(off)
