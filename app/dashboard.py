"""M1 · Conceber — Painel de diagnóstico: Quadrilátero Central de Curitiba.

Run:  uv run streamlit run app/dashboard.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from src.m1 import contract, data, theme as T
from src.m1.noise import NBR10151
from src.m1.emissions import speed_factor

st.set_page_config(page_title="M1 · Mobilidade Curitiba", page_icon="🚌", layout="wide")

st.markdown(
    f"""<style>
    .block-container {{padding-top: 1.6rem; max-width: 1280px;}}
    h1 {{letter-spacing: -0.02em; font-weight: 700;}}
    .kpi {{background:#fff; border:1px solid #E5E3DA; border-radius:10px; padding:14px 16px;}}
    .kpi .v {{font-size:1.7rem; font-weight:700; color:{T.INK}; line-height:1.1;}}
    .kpi .l {{font-size:.78rem; color:{T.MUTED}; text-transform:uppercase; letter-spacing:.05em;}}
    .ph {{display:inline-block; background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; border-radius:999px;
          padding:1px 10px; font-size:.75rem; font-weight:600;}}
    .real {{display:inline-block; background:#CCFBF1; color:#115E59; border:1px solid #5EEAD4; border-radius:999px;
          padding:1px 10px; font-size:.75rem; font-weight:600;}}
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Carregando camadas…")
def get():
    return data.load()


d = get()
pts: pd.DataFrame = d["points"]


def kpi(col, value, label):
    col.markdown(f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)


def style(fig, h=360):
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=T.INK, size=13), legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(gridcolor="#E5E3DA", zeroline=False)
    fig.update_yaxes(gridcolor="#E5E3DA", zeroline=False)
    return fig


# ---------- header + sidebar ----------
st.title("Mobilidade Urbana · Quadrilátero Central de Curitiba")
st.caption("Ciências do Ambiente · UTFPR · Marco 1 (Conceber) — diagnóstico do cenário As-Is")

with st.sidebar:
    st.header("Controles")
    win = st.radio("Janela de pico", ["manha", "tarde"], format_func=lambda x: {"manha": "Manhã 06:30–09:00", "tarde": "Tarde 17:00–19:00"}[x])
    v_kmh = st.slider("Velocidade média na rede (km/h)", 8, 50, 18 if win == "manha" else 15, key=f"v_{win}",
                      help="Alimenta CoRTN e fator de emissão. Substituir pelo valor medido/simulado.")
    st.subheader("Camadas do mapa")
    L = {k: st.checkbox(lbl, v) for k, lbl, v in [("sv", "Sistema viário (IPPUC)", True), ("ciclo", "Ciclovias", True),
                                                   ("calc", "Calçadão", True), ("term", "Terminais", True), ("pts", "Pontos de medição", True),
                                                   ("bus", "Telemetria de ônibus (sintética)", False)]}
    st.divider()
    st.markdown('<span class="ph">PLACEHOLDER</span> contagens, Leq, perfil horário, telemetria e fatores de emissão. '
                '<span class="real">REAL</span> geometria (Overture, IPPUC).', unsafe_allow_html=True)
    st.caption("Edite `data/placeholders/*.csv` após as medições em campo.")

s = d["stats"]
c = st.columns(4)
kpi(c[0], f"{s['area_km2']:.1f} km²", "Área de estudo (hull das 6 vias)")
kpi(c[1], f"{s['n_segments']:,}".replace(",", "."), "Segmentos viários (Overture)")
kpi(c[2], f"{s['ciclo_km']:.0f} km", "Ciclovias oficiais (IPPUC)")
kpi(c[3], f"{s['n_points']}", "Pontos de medição candidatos")
st.write("")

tab_map, tab_traf, tab_env, tab_arch = st.tabs(["🗺️ Mapa", "🚗 Tráfego", "🔊 Ruído e emissões", "🧩 Arquitetura e roadmap"])

# ---------- MAPA ----------
with tab_map:
    layers = [pdk.Layer("GeoJsonLayer", json.loads(d["area"].to_json()), stroked=True, filled=True, get_fill_color=[15, 118, 110, 22],
                        get_line_color=[15, 118, 110, 230], line_width_min_pixels=2)]
    if L["sv"]:
        sv = d["sistema_viario"].copy()
        sv["color"] = sv["SIST_VIARI"].map(lambda k: [int(T.CLASS_COLORS.get(k, "#D1D5DB")[i:i + 2], 16) for i in (1, 3, 5)] + [200])
        sv["w"] = sv["SIST_VIARI"].map({"CENTRAL": 6, "PRIORITÁRIA": 5, "SETORIAL 1": 4, "SETORIAL 2": 3, "COLETORA 1": 2.5}).fillna(1.2)
        layers.append(pdk.Layer("GeoJsonLayer", json.loads(sv[["NMVIA", "SIST_VIARI", "color", "w", "geometry"]].to_json()), get_line_color="properties.color",
                                get_line_width="properties.w", line_width_units="pixels", pickable=True))
    if L["ciclo"]:
        layers.append(pdk.Layer("GeoJsonLayer", json.loads(d["ciclovias"][["geometry"]].to_json()), get_line_color=[77, 124, 15, 230], line_width_min_pixels=2))
    if L["calc"]:
        layers.append(pdk.Layer("GeoJsonLayer", json.loads(d["calcadao"][["NOME", "geometry"]].to_json()), get_fill_color=[124, 58, 237, 200], stroked=False, pickable=True))
    if L["term"]:
        t = d["terminais"].copy(); t["lon"], t["lat"] = t.geometry.x, t.geometry.y
        layers.append(pdk.Layer("ScatterplotLayer", t[["EQUIPAMENT", "lon", "lat"]], get_position=["lon", "lat"], get_radius=130, get_fill_color=[37, 99, 235, 230], pickable=True))
    if L["bus"]:
        b = d["bus_fixes"].dropna(subset=["kmh"]).copy()
        b["color"] = b.kmh.map(lambda v: [185, 28, 28, 200] if v < 5 else ([217, 119, 6, 200] if v < 20 else [15, 118, 110, 200]))
        layers.append(pdk.Layer("ScatterplotLayer", b[["matched_lng", "matched_lat", "color", "kmh"]], get_position=["matched_lng", "matched_lat"], get_radius=14, get_fill_color="color"))
    if L["pts"]:
        p = pts.copy(); p["r"] = p[f"vph_{win}"] / 8 + 80
        layers.append(pdk.Layer("ScatterplotLayer", p[["name", "point_id", "lat", "lon", "r", f"vph_{win}", "leq_dba"]], get_position=["lon", "lat"], get_radius="r",
                                get_fill_color=[185, 28, 28, 190], get_line_color=[255, 255, 255], stroked=True, line_width_min_pixels=2, pickable=True))
    view = pdk.ViewState(latitude=-25.4416, longitude=-49.274, zoom=11.4)
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_style="light",
                             tooltip={"html": "<b>{name}{NMVIA}{NOME}{EQUIPAMENT}</b><br/>{SIST_VIARI}", "style": {"fontSize": "12px"}}), height=620)
    st.caption("Legenda: vias por hierarquia (preto = Central, laranja = Prioritária, azul = Setoriais, cinza = Coletoras); "
               "círculos vermelhos = pontos de medição (raio ∝ veículos/h de pico, valor placeholder); azul = terminais; roxo = Calçadão.")
    with st.expander("Pontos de medição candidatos"):
        st.dataframe(pts[["point_id", "name", "lat", "lon"]], hide_index=True, width="stretch")

# ---------- TRÁFEGO ----------
with tab_traf:
    st.markdown('<span class="ph">PLACEHOLDER</span> contagens por ponto até as medições manuais de VPD.', unsafe_allow_html=True)
    a, b = st.columns([3, 2])
    with a:
        fig = go.Figure()
        for m in data.MODES:
            fig.add_bar(x=pts.point_id, y=pts.vpd_total * pts[f"share_{m}"], name=T.MODE_LABELS[m], marker_color=T.MODE_COLORS[m],
                        hovertext=pts.name)
        fig.update_layout(barmode="stack", title="Volume diário (VPD) por ponto e modal", yaxis_title="veículos/dia")
        st.plotly_chart(style(fig), width="stretch")
    with b:
        tot = {m: float((pts.vpd_total * pts[f"share_{m}"]).sum()) for m in data.MODES}
        fig = go.Figure(go.Pie(labels=[T.MODE_LABELS[m] for m in tot], values=list(tot.values()), hole=.58,
                               marker_colors=[T.MODE_COLORS[m] for m in tot], textinfo="percent"))
        fig.update_layout(title="Divisão modal (todos os pontos)")
        st.plotly_chart(style(fig), width="stretch")
    h = d["hourly"]
    fig = go.Figure(go.Scatter(x=h.hora, y=h.fracao_vpd * 100, mode="lines+markers", line=dict(color=T.TEAL, width=3), name="% do VPD"))
    for x0, x1 in [(6.5, 9), (17, 19)]:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=T.AMBER, opacity=.18, line_width=0)
    fig.update_layout(title="Perfil horário do tráfego (faixas = janelas de pico)", xaxis_title="hora do dia", yaxis_title="% do VPD", xaxis=dict(dtick=2))
    st.plotly_chart(style(fig, 300), width="stretch")
    st.subheader("Ônibus: indicador de para-e-anda")
    st.markdown('<span class="ph">PLACEHOLDER</span> telemetria sintética sobre geometria real, map-matching com <code>fastmob</code>. '
                'Trocar por posições reais da URBS (requer chave de acesso).', unsafe_allow_html=True)
    k = d["bus_kpis"].groupby("window")[["vel_media_kmh", "pct_parado"]].mean().reset_index()
    cc = st.columns(len(k))
    for col, r in zip(cc, k.itertuples()):
        kpi(col, f"{r.vel_media_kmh:.1f} km/h · {r.pct_parado:.0f}% parado", r.window)

# ---------- RUÍDO E EMISSÕES ----------
with tab_env:
    st.markdown('<span class="ph">PLACEHOLDER</span> Leq medido e fatores de emissão; <b>CoRTN</b> é estimativa de primeira ordem.', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        area = st.selectbox("Tipo de área (NBR 10151)", list(NBR10151), index=1)
        lim = NBR10151[area][0]
        cortn = data.cortn_table(pts, win, v_kmh)
        fig = go.Figure()
        fig.add_bar(x=pts.point_id, y=pts.leq_dba, name="Leq medido", marker_color=T.BLUE, hovertext=pts.name)
        fig.add_bar(x=pts.point_id, y=pts.residual_dba, name="Ruído residual", marker_color="#9CA3AF")
        fig.add_scatter(x=pts.point_id, y=cortn.values, name="CoRTN (10 m)", mode="markers", marker=dict(color=T.AMBER, size=12, symbol="diamond"))
        fig.add_hline(y=lim, line=dict(color=T.RED, dash="dash"), annotation_text=f"Limite diurno {lim} dB", annotation_position="top left")
        fig.update_layout(barmode="group", title="Níveis sonoros por ponto", yaxis=dict(title="dB(A)", range=[40, 85]))
        st.plotly_chart(style(fig), width="stretch")
        exc = (pts.leq_dba - lim)
        st.metric("Pontos acima do limite", f"{int((exc > 0).sum())} de {len(pts)}", f"excesso médio {exc[exc > 0].mean():.1f} dB" if (exc > 0).any() else None, delta_color="inverse")
    with b:
        em = data.emissions_table(pts, win, v_kmh)
        poll = st.selectbox("Poluente", ["CO2", "NOx", "CO", "PM25"], format_func=lambda x: {"CO2": "CO₂", "PM25": "MP2,5"}.get(x, x))
        fig = go.Figure(go.Bar(x=em.point_id, y=em[poll], marker_color=T.TEAL, hovertext=em.name))
        fig.update_layout(title=f"Taxa de emissão baseline (kg/h por km de via, v = {v_kmh} km/h)", yaxis_title="kg/h·km")
        st.plotly_chart(style(fig), width="stretch")
        st.caption(f"Fator de velocidade a {v_kmh} km/h = {speed_factor(v_kmh):.2f}× a emissão a 50 km/h. "
                   "Fatores de emissão são ordens de grandeza; o M2 usa PHEMlight/HBEFA no SUMO.")
    st.info("**Efeito de suavização do fluxo (ilustrativo).** O M4 estimará a redução de ruído por simulação. "
            "Regra de bolso: reduzir o volume em 20% abate ≈ 1 dB (10·log₁₀ 0,8); o ganho maior vem de menos para-e-anda.")

# ---------- ARQUITETURA ----------
with tab_arch:
    a, b = st.columns([3, 2])
    with a:
        st.subheader("Arquitetura lógica de dados compartilhados")
        st.graphviz_chart("""digraph G { rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#0F766E", fillcolor="#F0FDFA"];
          sensores [label="Sensores virtuais\\n(Wokwi / Node-RED)\\n[Automação]"]; mqtt [label="Broker MQTT\\n(Mosquitto)", fillcolor="#FEF3C7", color="#D97706"];
          ctrl [label="Controlador de tráfego\\nTraCI / Python\\n[Computação]"]; sumo [label="SUMO\\n(As-Is / To-Be)", fillcolor="#DBEAFE", color="#2563EB"];
          emis [label="Emissões e ruído\\nPHEMlight / CoRTN\\n[Mecânica]"]; dash [label="Painel\\nStreamlit", fillcolor="#EDE9FE", color="#7C3AED"]; gis [label="GIS\\nOverture / IPPUC / QGIS"];
          gis -> sumo [label="malha"]; sensores -> mqtt [label="JSON"]; mqtt -> ctrl; ctrl -> sumo [label="TraCI"]; sumo -> emis; emis -> dash; ctrl -> dash; sumo -> sensores [label="ocupação", style=dashed]; }""")
    with b:
        st.subheader("Contrato de dados (JSON)")
        st.code(json.dumps(contract.EXAMPLE, indent=2, ensure_ascii=False), language="json")
        st.caption("Validado com pydantic (`src/m1/contract.py`).")
        st.subheader("Tópicos MQTT (preliminar)")
        st.code("\n".join(contract.TOPICS), language="text")
    st.subheader("Roadmap CDIO")
    rm = pd.DataFrame({"Marco": ["M1 Conceber", "M2 Desenhar", "M3 Implementar", "M4 Operar"],
                       "Entregável": ["Relatório de diagnóstico + mapa preliminar + arquitetura de dados", "Cenário As-Is calibrado (GEH<5 em ≥85% das vias) + memorial de emissões",
                                      "Controle TraCI, MQTT, esquemáticos de sensoriamento", "Comparação As-Is × To-Be, viabilidade, defesa"],
                       "Status": ["▶ em andamento", "○", "○", "○"]})
    st.dataframe(rm, hide_index=True, width="stretch")
