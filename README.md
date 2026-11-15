# Projeto 1 — Mobilidade Urbana e Sustentabilidade (Quadrilátero Central de Curitiba)

Ciências do Ambiente, UTFPR. Marcos M1–M4 do ciclo CDIO.

## Estado (leia primeiro)

- **Nenhum dado de campo existe ainda.** Contagens de veículos, pedestres e ciclistas, níveis de ruído, perfil horário,
  telemetria de ônibus (URBS), semáforos e fatores de emissão são **provisórios** (`data/placeholders/`, geradores sintéticos
  com semente fixa). Os relatórios marcam esses valores com o selo *PROVISÓRIO*.
- **Os resultados são um teste de método, não previsão para Curitiba.** A rede simulada opera saturada.
- **Resultado do M4:** o controlador PI sobre programas fixos fica mais lento que o As-Is em 10 de 10 pares semente-janela (robusto no sinal; só 1 dos 36 testes primários sobrevive à correção FDR). A prioridade ao ônibus (regra refeita) tem efeito nulo e quase não atua; a variante condicional é idêntica à básica por construção. A onda verde (Rua Mariano Torres) piora o atraso e, contra um controle de programas fixos sem coordenação, também os *teleports*; a queda de velocidade no eixo vem de trocar o *actuated* por programas fixos. O As-Is só flui até ~60% da demanda (varredura). Uma versão anterior do relatório concluía o oposto para a prioridade ao ônibus; a mudança vem de uma regra refeita e de contabilidade corrigida (ver M4).
- **Calibração GEH (M2):** critério de 85% *não atendido* (manhã 76,5%, tarde 82,4%), sobre contagens sorteadas e só 2 pontos com aproximação motorizada.
- **Onda verde:** implementada na Rua Mariano Torres (a Av. Floriano não recebeu semáforos na inferência), um sentido, sobre semáforos inferidos; não superou o controle. Esquemas elétricos: apenas diagrama em blocos.
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
| `tests/` | `pytest` (22 testes: controlador, contrato, GEH, CoRTN, onda verde, reparo de semáforos) |

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

Contagens e Leq de campo; semáforos reais; telemetria ao vivo da URBS (precisa de chave; o GPS histórico de 12/11/2026 é real e aberto, `make` via `src/m1/urbs_real.py`); onda verde; teste com Mosquitto e hardware;
decisão sobre o polígono de estudo (casco convexo de 30 km² vs núcleo) e a via "Mário Tourinho".
