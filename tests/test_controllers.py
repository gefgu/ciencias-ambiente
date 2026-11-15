from src.cps.controllers import Controller, Params, State


def st(**k):
    d = dict(phase=0, t_in_phase=20, is_green_phase=True, q_green=0, q_red=0, bus_on_green=False, bus_on_red=False, occ_green=0)
    d.update(k)
    return State(**d)


def test_hold_before_min_green():
    assert Controller().decide(st(t_in_phase=3, q_red=10))[0] == "hold"


def test_hold_in_yellow():
    assert Controller().decide(st(is_green_phase=False, q_red=10))[0] == "hold"


def test_switch_when_red_queue_dominates():
    assert Controller().decide(st(q_green=0, q_red=8, occ_green=0))[0] == "switch"


def test_extend_when_green_busy():
    assert Controller().decide(st(q_green=6, q_red=1, occ_green=30))[0] == "extend"


def test_max_green_forces_switch():
    assert Controller().decide(st(t_in_phase=60, q_green=9, q_red=1))[0] == "switch"


def test_bus_on_red_switches_if_green_light_load():
    assert Controller().decide(st(bus_on_red=True, q_green=1))[0] == "switch"


def test_bus_on_red_does_not_steal_heavy_green():
    assert Controller().decide(st(bus_on_red=True, q_green=12, occ_green=60))[0] != "switch"


def test_bus_extension_bounded():
    """A prioridade ao ônibus soma no máximo bus_extend_max segundos por fase (extensões posteriores vêm da regra de demanda)."""
    c = Controller()
    for i in range(6):
        c.decide(st(bus_on_green=True, t_in_phase=20 + i, q_green=5, q_red=1))
    assert c.bus_extended <= c.p.bus_extend_max


def test_integral_antiwindup():
    c = Controller()
    for _ in range(200):
        c.decide(st(q_green=5, q_red=3.5, occ_green=20))
    assert abs(c.integ) <= c.p.ki_clamp
