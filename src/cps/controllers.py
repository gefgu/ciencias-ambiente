"""Controle semafórico adaptativo (M3) — lógica pura, independente de SUMO e de MQTT.

Estado de entrada por interseção (vem de sensores virtuais) -> comando ('hold' | 'extend' | 'switch').
Malha fechada: o erro é a diferença de pressão entre as fases (fila nas faixas com vermelho − fila nas faixas com verde);
um controlador PI sobre esse erro decide estender ou encerrar o verde; prioridade ao ônibus (BRT) por regra.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Params:
    min_green: float = 8.0
    max_green: float = 50.0
    step: float = 5.0         # período de decisão (s) = período de amostragem dos sensores
    extend: float = 5.0       # extensão de verde por decisão (s)
    kp: float = 1.0
    ki: float = 0.15
    theta: float = 1.0        # banda morta do PI (veículos de pressão)
    ki_clamp: float = 6.0     # anti-windup
    bus_extend_max: float = 10.0
    bus_switch: bool = True
    bus_targeted: bool = False  # prioridade condicional: só encerra o verde se a próxima fase verde serve o ônibus
    bus_only: bool = False    # só prioridade ao ônibus; o resto fica com a lógica base (actuated)


@dataclass
class State:
    """Medidas de uma interseção no instante k."""
    phase: int
    t_in_phase: float
    is_green_phase: bool
    q_green: float            # veículos parados/lentos nas faixas servidas pela fase atual
    q_red: float              # idem, nas faixas sem verde
    bus_on_green: bool = False   # ônibus se aproximando em faixa com verde
    bus_on_red: bool = False     # ônibus se aproximando em faixa com vermelho
    occ_green: float = 0.0       # ocupação média (%) do laço nas faixas com verde
    bus_next_serves: bool = True # a PRÓXIMA fase verde serve a faixa do ônibus que espera?
    co2_gps: float = 0.0         # CO2 instantâneo nas faixas de aproximação (g/s)


@dataclass
class Controller:
    p: Params = field(default_factory=Params)
    integ: float = 0.0
    bus_extended: float = 0.0
    last_phase: int = -1

    def decide(self, s: State) -> tuple[str, float]:
        """Retorna (ação, segundos). Ação 'extend' soma segundos ao verde; 'switch' encerra o verde agora."""
        if s.phase != self.last_phase:
            self.integ, self.bus_extended, self.last_phase = 0.0, 0.0, s.phase
        if not s.is_green_phase:
            return "hold", 0.0
        if s.t_in_phase < self.p.min_green:
            return "hold", 0.0
        if s.bus_on_red and self.p.bus_switch and (s.bus_next_serves or not self.p.bus_targeted) and s.q_green < 3 + s.occ_green / 25:  # só tira o verde se a corrente atual não está carregada
            return "switch", 0.0
        if s.bus_on_green and self.bus_extended < self.p.bus_extend_max and s.t_in_phase < self.p.max_green + self.p.bus_extend_max:
            self.bus_extended += self.p.extend
            return "extend", self.p.extend
        if self.p.bus_only:
            return "hold", 0.0
        e = s.q_red - s.q_green
        self.integ = max(-self.p.ki_clamp, min(self.p.ki_clamp, self.integ + e * self.p.step))
        u = self.p.kp * e + self.p.ki * self.integ
        if s.t_in_phase >= self.p.max_green:
            return "switch", 0.0
        if u > self.p.theta:
            return "switch", 0.0
        if s.q_green > 0 or s.occ_green > 8:   # ainda há demanda no verde: estende
            return "extend", self.p.extend
        return ("switch", 0.0) if s.q_red > 0 else ("hold", 0.0)
