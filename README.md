# Projeto 1 — Mobilidade Urbana e Sustentabilidade (Quadrilátero Central de Curitiba)

Ciências do Ambiente, UTFPR. Marcos M1–M4 do ciclo CDIO.

## Estado (leia primeiro)

- **Nenhum dado de campo existe ainda.** Contagens de veículos, pedestres e ciclistas, níveis de ruído, perfil horário,
  telemetria de ônibus (URBS), semáforos e fatores de emissão são **provisórios** (`data/placeholders/`, geradores sintéticos
  com semente fixa). Os relatórios marcam esses valores com o selo *PROVISÓRIO*.
- **Os resultados são um teste de método, não previsão para Curitiba.** A rede simulada opera saturada.
- **Resultado do M4:** o controlador PI sobre programas fixos piora a rede de forma robusta (velocidade −16% a −17%). A prioridade ao ônibus (regra refeita) e a onda verde (Rua Mariano Torres) não mostram ganho consistente; a onda verde reduz fila e *teleports* mas reduz a velocidade no eixo. O As-Is só deixa de engarrafar com ~50% da demanda (varredura). Uma versão anterior do relatório concluía o contrário para a prioridade ao ônibus; a mudança vem de uma regra refeita e de contabilidade corrigida (ver M4).
- **Calibração GEH (M2):** critério de 85% *não atendido* (manhã 76,5%, tarde 82,4%), sobre contagens sorteadas e só 2 pontos com aproximação motorizada.
- **Onda verde:** implementada na Rua Mariano Torres (a Av. Floriano não recebeu semáforos na inferência); fase/ciclo/posição dos semáforos são inferidos. Esquemas elétricos: apenas diagrama em blocos.
- **Fila e ruído:** fila (`queue-output`) e ruído por CoRTN e harmonoise estão no M2/M4; harmonoise é um nível por aresta, sem propagação a receptores.

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
make evaluate && make sweep && make summary && make active   # M4 (cerca de 1,5 h de CPU em 12 núcleos)
make report-m1 report-m2 report-m3 report-m4  # PDFs em report/
make test
```

Para trocar os dados provisórios pelos medidos: edite `data/placeholders/field_counts.csv`, `noise_leq.csv` e `hourly_profile.csv`,
rode `make calibrate baseline` e regenere os relatórios.

## Pendências principais

Contagens e Leq de campo; semáforos reais; linhas e telemetria da URBS (precisa de chave); onda verde; teste com Mosquitto e hardware;
decisão sobre o polígono de estudo (casco convexo de 30 km² vs núcleo) e a via "Mário Tourinho".
