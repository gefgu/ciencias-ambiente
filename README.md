# Projeto 1 — Mobilidade Urbana e Sustentabilidade (Quadrilátero Central de Curitiba)

Ciências do Ambiente, UTFPR. Marcos M1–M4 do ciclo CDIO.

## Estado (leia primeiro)

- **Nenhum dado de campo existe ainda.** Contagens de veículos, pedestres e ciclistas, níveis de ruído, perfil horário,
  telemetria de ônibus (URBS), semáforos e fatores de emissão são **provisórios** (`data/placeholders/`, geradores sintéticos
  com semente fixa). Os relatórios marcam esses valores com o selo *PROVISÓRIO*.
- **Os resultados são um teste de método, não previsão para Curitiba.** A rede simulada opera saturada.
- **Resultado do M4 (negativo):** em 5 sementes por janela, nem o controlador PI nem a prioridade ao ônibus melhoraram o cenário
  As-Is (`actuated` do SUMO); ambos reduziram a velocidade média e elevaram as emissões na simulação.
- **Calibração GEH (M2):** critério de 85% *não atendido* (manhã 76,5%, tarde 82,4%), sobre contagens sorteadas e só 2 pontos com aproximação motorizada.
- **Onda verde adaptativa: não implementada.** Esquemas elétricos: apenas diagrama em blocos.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `src/m1/` | Pipeline de dados: Overture Maps + IPPUC, pontos de medição, ruído (CoRTN), emissões preliminares, contrato JSON |
| `src/cps/` | SUMO: rede, demanda, calibração GEH, baseline, controladores, MQTT, sensoriamento, avaliação |
| `app/dashboard.py` | Painel Streamlit do M1 |
| `report/` | Relatórios Typst `m1.typ` … `m4.typ` (+ `lib.typ`, `refs.bib`) |
| `sim/` | Cenário SUMO (`net*.net.xml`, `vtypes.add.xml`, `routes_asis_*`, `*.sumocfg`) e `mosquitto.conf` |
| `data/placeholders/` | **CSVs a substituir pelos dados de campo** |
| `tests/` | `pytest` (controlador e contrato) |

## Como rodar

```
uv sync
make data && make dashboard        # M1
make net && make calibrate && make baseline   # M2
make tune && make mqtt             # M3
make evaluate && make active       # M4 (cerca de uma hora de CPU)
make report-m1 report-m2 report-m3 report-m4  # PDFs em report/
make test
```

Para trocar os dados provisórios pelos medidos: edite `data/placeholders/field_counts.csv`, `noise_leq.csv` e `hourly_profile.csv`,
rode `make calibrate baseline` e regenere os relatórios.

## Pendências principais

Contagens e Leq de campo; semáforos reais; linhas e telemetria da URBS (precisa de chave); onda verde; teste com Mosquitto e hardware;
decisão sobre o polígono de estudo (casco convexo de 30 km² vs núcleo) e a via "Mário Tourinho".
