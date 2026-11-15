"""Projeto de sensoriamento IoT (M3): dimensionamento, lista de materiais e esquemáticos (figuras para o relatório)."""
from __future__ import annotations
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import pandas as pd
import src.m1.figures  # rcParams
from src.m1 import theme as T
from .common import OUT, ROOT

FIG = ROOT / "report" / "figures"
# Premissas de projeto (fundamentadas em dimensionamento, ver relatório M3)
V_APPROACH = 50 / 3.6      # m/s
HEADWAY_STOP = 2.0         # s entre veículos parados (saturação ~1800 veic/h/faixa)
VEH_SPACE = 7.5            # m por veículo na fila (comprimento + folga)
SAMPLE_S = 5               # período de amostragem = período de decisão do controlador
MSG_BYTES = 420            # ESTIMADO (payload JSON do contrato + cabeçalho MQTT); medir no nó real


def plan() -> pd.DataFrame:
    cal = pd.read_csv(OUT / "m2_geh_am.csv")
    rows = []
    for r in cal.itertuples():
        q_design = max(r.obs_vph / 3600 * 60, 4)  # veículos na fila em 1 min de vermelho
        queue_m = q_design * VEH_SPACE
        rows.append({"ponto": r.point_id, "aresta": r.edge, "laco_stopline_m": 0, "laco_avanco_m": round(min(max(queue_m, 20), 120), 0),
                     "fila_projeto_veic": round(q_design, 1)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "m3_sensing_plan.csv", index=False)
    per_pt = df.groupby("ponto").size()
    bom = {"lacos_indutivos": int(2 * len(df)), "cameras_contagem": int(len(per_pt)), "sensores_ruido_classe2": int(len(per_pt)),
           "nos_ESP32": int(len(per_pt)), "pontos": int(len(per_pt)), "aproximacoes": int(len(df)),
           "msgs_por_s": round(2 * len(per_pt) / SAMPLE_S, 2), "kbit_s": round(2 * len(per_pt) / SAMPLE_S * MSG_BYTES * 8 / 1000, 2)}
    (OUT / "m3_bom.json").write_text(json.dumps(bom, indent=1))
    return df


def loop_fig():
    fig, ax = plt.subplots(figsize=(7.2, 2.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 3.2)
    def box(x, y, w, h, t, c):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=c + "22", ec=c, lw=1.4))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=6.2, color=T.INK)
    def arr(x1, y1, x2, y2, t="", dy=0.12):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, color=T.INK, lw=1))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, t, ha="center", fontsize=6.5, color=T.MUTED)
    box(0.1, 1.9, 1.5, .9, "Referência\nfila verde =\nfila vermelha", T.MUTED)
    ax.add_patch(plt.Circle((2.2, 2.35), .2, fc="white", ec=T.INK)); ax.text(2.2, 2.35, "Σ", ha="center", va="center", fontsize=9)
    box(2.9, 1.9, 1.7, .9, "Controlador PI\nu = Kp·e + Ki∫e\n+ regra do ônibus", T.TEAL)
    box(5.3, 1.9, 1.6, .9, "Atuador de fase\nTraCI / sinal\n(estende | encerra)", T.AMBER)
    box(7.4, 1.9, 2.5, .9, "Planta: tráfego\nSUMO (fila, ocupação,\nônibus na aproximação)", T.BLUE)
    box(5.3, .2, 1.6, .9, "Sensores virtuais\nlaço + câmera\n(Wokwi/Node-RED)", T.PURPLE)
    box(2.9, .2, 1.7, .9, "Broker MQTT\nMosquitto\n(…/sensors, …/cmd)", T.GREEN)
    arr(1.7, 2.35, 2.0, 2.35); arr(2.4, 2.35, 2.9, 2.35, "e(k)"); arr(4.6, 2.35, 5.3, 2.35, "u(k)"); arr(6.9, 2.35, 7.4, 2.35, "fase")
    arr(8.7, 1.9, 6.9, 0.85, "q, ocupação", dy=.2); arr(5.3, .65, 4.6, .65, "JSON"); arr(2.9, .65, 2.2, .65, ""); arr(2.2, .65, 2.2, 2.15, "")
    ax.text(2.0, 1.25, "realimentação", fontsize=6.2, color=T.MUTED, rotation=90, ha="right")
    fig.savefig(FIG / "m3_loop.png"); plt.close(fig)


def sensor_fig():
    fig, ax = plt.subplots(figsize=(7.2, 2.6)); ax.set_xlim(-130, 30); ax.set_ylim(-9, 9); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((-130, -3.2), 160, 6.4, fc="#D1D5DB", ec="none"))
    ax.plot([-130, 30], [0, 0], color="white", ls=(0, (6, 6)), lw=1)
    ax.add_patch(Rectangle((0, -3.2), 3, 6.4, fc=T.INK, ec="none")); ax.text(1.5, 5, "linha de\nretenção", ha="center", fontsize=7)
    for x, t in [(-4, "laço de presença\n(2×6 m)"), (-60, "laço de avanço\n(dim. pela fila)")]:
        ax.add_patch(Rectangle((x - 1, -3), 2, 6, fc=T.PURPLE + "55", ec=T.PURPLE)); ax.text(x, -6.5, t, ha="center", va="top", fontsize=7)
    ax.add_patch(Rectangle((-105, 4), 3, 3, fc=T.BLUE, ec="none")); ax.text(-103.5, 8.5, "câmera de contagem\n(cobre 40 m)", ha="center", fontsize=7)
    ax.annotate("", xy=(-65, 5.2), xytext=(-103, 5.2), arrowprops=dict(arrowstyle="<->", color=T.BLUE, lw=1)); ax.text(-84, 6.0, "campo", ha="center", fontsize=6.5, color=T.BLUE)
    ax.add_patch(plt.Circle((-20, 5.5), 1.3, fc=T.AMBER, ec="none")); ax.text(-20, 8.2, "microfone cl. 2\n(10 m do bordo)", ha="center", fontsize=7)
    for x in (-40, -48, -56): ax.add_patch(Rectangle((x, -1.6), 4.5, 1.9, fc=T.TEAL, ec="none"))
    fig.savefig(FIG / "m3_sensors.png"); plt.close(fig)


def electrical_fig():
    """Diagrama elétrico em blocos de um nó de interseção (referência de projeto, não um esquema de fabricação)."""
    fig, ax = plt.subplots(figsize=(7.2, 3.6)); ax.axis("off"); ax.set_xlim(0, 15); ax.set_ylim(0, 6.6)
    def box(x, y, w, h, t, c, fs=5.6):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=c + "22", ec=c, lw=1.2))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=T.INK)
    def line(xs, ys, c=T.INK, lab=None, lx=None, ly=None):
        ax.plot(xs, ys, color=c, lw=1.1, solid_capstyle="round")
        if lab: ax.text(lx, ly, lab, fontsize=5.2, color=T.MUTED, ha="center")
    # linha 1: laço -> cartão -> ESP32 -> roteador
    box(0.2, 4.6, 2.6, 1.4, "Laço indutivo\n3–4 espiras,\ncabo blindado", T.PURPLE)
    box(3.8, 4.6, 3.0, 1.4, "Cartão detector\nde laço (oscilador +\nsaída optoacoplada)", T.PURPLE)
    box(7.8, 4.6, 3.0, 1.4, "Nó de borda ESP32\nGPIO: presença\nUART: medidor de ruído", T.TEAL)
    box(11.8, 4.6, 3.0, 1.4, "Roteador 4G /\nswitch PoE\n→ broker MQTT", T.GREEN)
    line([2.8, 3.8], [5.3, 5.3], lab="indutância", lx=3.3, ly=5.45)
    line([6.8, 7.8], [5.3, 5.3], lab="3,3 V", lx=7.3, ly=5.45)
    line([10.8, 11.8], [5.3, 5.3], lab="Ethernet", lx=11.3, ly=5.45)
    # linha 2: câmera -> unidade de visão ; medidor de ruído
    box(0.2, 2.2, 2.6, 1.4, "Câmera IP\n(contagem por visão)", T.BLUE)
    box(3.8, 2.2, 3.0, 1.4, "Unidade de visão\n(RPi/Jetson):\ncontagem → MQTT", T.BLUE)
    box(7.8, 2.2, 3.0, 1.4, "Medidor de nível\nsonoro classe 2\n(IEC 61672) + calibrador", T.AMBER)
    line([2.8, 3.8], [2.9, 2.9], lab="RTSP", lx=3.3, ly=3.05)
    line([9.3, 9.3], [3.6, 4.6], c=T.AMBER, lab="UART", lx=9.75, ly=4.05)
    line([5.3, 5.3], [3.6, 4.05], c=T.BLUE); line([5.3, 13.3], [4.05, 4.05], c=T.BLUE, lab="MQTT sobre Ethernet", lx=11.6, ly=3.85)
    line([13.3, 13.3], [4.05, 4.6], c=T.BLUE)
    # base: alimentação e gabinete
    box(0.2, 0.2, 6.6, 1.2, "Alimentação: fonte do gabinete 24 Vcc → conversores 5 V / 3,3 V\nDPS (surto) e fusível em cada ramal", T.MUTED)
    box(7.8, 0.2, 7.0, 1.2, "Gabinete IP65 aterrado; blindagem do laço aterrada em um só ponto\nCLP/controlador de semáforo na outra ponta do broker", T.MUTED)
    fig.savefig(FIG / "m3_eletrico.png"); plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    print(plan().groupby("ponto").size().to_dict()); loop_fig(); sensor_fig(); electrical_fig(); print(open(OUT / "m3_bom.json").read())


