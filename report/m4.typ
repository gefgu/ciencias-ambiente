#import "lib.typ": *

#let R = json("figures/m4_results.json")
#let SW = json("figures/m4_sweep.json")
#let AC = json("figures/m4_active.json")
#let EX = json("figures/m4_extra.json")
#let TP = json("figures/m4_teleports.json")
#let fix(x, d) = {
  if d == 0 { return str(int(calc.round(float(x)))).replace("-", "−") }
  let s = str(calc.round(float(x), digits: d))
  if not s.contains(".") { s = s + "." + "0" * d } else { let n = s.split(".").at(1).len(); s = s + "0" * (d - n) }
  s.replace(".", ",").replace("-", "−")
}
#let f1(x) = fix(x, 1)
#let f0(x) = {
  let s = str(int(calc.round(float(x))))
  s.clusters().rev().chunks(3).map(c => c.join()).join(".").clusters().rev().join()
}
#let sg(v, d: 0) = if v > 0 { "+" + fix(v, d) } else { fix(v, d) }
#let pm(o, d: 1) = [#fix(o.mean, d) ± #fix(o.ci95, d)]
#let D(w, s, m) = R.at(w).at(s).at(m)
#let dp(w, s, m) = sg(D(w, s, m).delta_pct)
#let pp(w, s, m) = fix(D(w, s, m).p_paired, 2)
#let cell(w, s, m) = {
  let o = D(w, s, m)
  if o.at("delta_pct", default: none) == none { [n/d] } else { [#sg(o.delta_pct)% (#fix(o.p_paired, 2))] }
}

#let ROWS = (
  ("Velocidade média (km/h)", "speed_kmh", 1), ("Veículos concluídos", "finished", 0), ("Teleports", "teleports", 0), ("Fila p95 (m)", "q_p95_m", 0),
  ("Atraso dos concluídos (s)", "delay_s", 0), ("Atraso dos ônibus (s)", "bus_delay_s", 0), ("CO₂ na janela (t)", "CO2_t_window", 1),
  ("CO₂ por veículo-km (g)", "CO2_g_per_vkm", 0), ("NOx na janela (kg)", "NOx_kg_window", 1), ("Leq harmonoise (dB)", "Leq_harm_dba", 1),
  ("Leq CoRTN (dB)", "Leq_cortn_dba", 1), ("Velocidade no eixo da onda verde (km/h)", "corridor_speed_kmh", 1))
#let SC = ("tobe_pi", "tobe", "tobe_fake", "tobe_bus2", "tobe_gw")

#let tbl(w, title) = figure(
  table(columns: (3.3cm, 2.1cm, 1.9cm, 1.9cm, 1.9cm, 1.9cm, 1.9cm), align: (left, right, right, right, right, right, right), inset: (x: 3pt, y: 3.5pt),
    [Indicador], [As-Is], [PI sobre fixos], [Actuated + ônibus], [Ablação ônibus falsos], [Prioridade condicional], [Onda verde],
    ..ROWS.map(r => (r.at(0), pm(D(w, "asis", r.at(1)), d: r.at(2)), ..SC.map(s => cell(w, s, r.at(1))))).flatten()),
  caption: [#title: As-Is em média ± IC 95% (5 réplicas); demais colunas em Δ% médio pareado (valor _p_ do teste _t_ pareado entre parênteses). Dados #ph(body: [provisórios]).],
)

#show: report.with(
  title: "Comparação As-Is × To-Be e viabilidade",
  subtitle: "Resultados da simulação integrada, impacto ambiental e limites da evidência",
  course: "Ciências do Ambiente", program: "Projeto 1", milestone: "Marco 4 · Operar",
  authors: ((name: "Gustavo Henrique Bruno dos Santos", role: "Computação"), (name: "[integrante]", role: "Elétrica e Automação"), (name: "[integrante]", role: "Mecânica")),
  date: "15 de novembro de 2026",
  abstract: [
    Compara o cenário atual (programas _actuated_ do SUMO) com quatro intervenções de controle semafórico e uma ablação, com cinco réplicas por cenário e janela, uma varredura de demanda e métricas de velocidade, fila, emissões e ruído.
    *O controlador PI sobre programas fixos piora a rede de forma robusta; a prioridade ao ônibus (na versão refeita) e a onda verde não mostram ganho consistente.* Os resultados são sensíveis ao nível de demanda, e o As-Is só sai do engarrafamento com cerca de metade da demanda.
    Todas as entradas são #ph(body: [provisórias]), o modelo está calibrado de forma insuficiente e a simulação acústica é aproximada: o documento entrega o método, os intervalos e a lista do que falta medir, não uma previsão para Curitiba.
  ],
)

= Resumo executivo

- *Escopo.* Pipeline aberto e reproduzível (Overture/IPPUC → SUMO → calibração GEH → emissões, poeira, ruído e fila) e intervenções de controle semafórico avaliadas com 5 sementes por janela, mais uma varredura de demanda (50% a 100%).
- *PI sobre programas fixos:* velocidade média #dp("am", "tobe_pi", "speed_kmh")% na manhã e #dp("pm", "tobe_pi", "speed_kmh")% na tarde (_p_ = #pp("am", "tobe_pi", "speed_kmh") e #pp("pm", "tobe_pi", "speed_kmh")), CO₂ por veículo-km #dp("am", "tobe_pi", "CO2_g_per_vkm")% e #dp("pm", "tobe_pi", "CO2_g_per_vkm")%, e #dp("am", "tobe_pi", "teleports")% de _teleports_ na manhã. É a única intervenção com efeito robusto, e é negativo.
- *Prioridade ao ônibus (regra refeita: um pedido por ônibus e semáforo, só ônibus em movimento):* velocidade #dp("am", "tobe", "speed_kmh")% e #dp("pm", "tobe", "speed_kmh")% (_p_ = #pp("am", "tobe", "speed_kmh") e #pp("pm", "tobe", "speed_kmh")): *efeito estatisticamente nulo*. A ablação com ônibus falsos dá resultado do mesmo tipo (#dp("am", "tobe_fake", "speed_kmh")% na manhã), logo nada indica que a detecção de ônibus seja o mecanismo.
- *Onda verde adaptativa (Rua Mariano Torres):* a fila p95 cai #dp("am", "tobe_gw", "q_p95_m")% e os _teleports_ #dp("am", "tobe_gw", "teleports")% na manhã, mas a *velocidade no eixo cai #dp("am", "tobe_gw", "corridor_speed_kmh")%* e o ruído harmonoise sobe #sg(D("am", "tobe_gw", "Leq_harm_dba").delta_mean, d: 1) dB. Resultado misto; a implementação não entregou a progressão esperada.
- *Por que confiar pouco.* Demanda, semáforos, linhas de ônibus e perfil horário são provisórios; a calibração GEH não atingiu 85%; os _teleports_ se concentram em poucas arestas (#TP.distinct_edges arestas, #f0(100 * TP.top10_share)% nas dez piores, oito na Rua Conselheiro Laurindo); e o resultado depende do nível de demanda (ver a varredura).
- *Não feito.* Medição de campo, linhas reais da URBS, semáforos reais, pedestres no controle, CO₂e e CO₂ biogênico.

= O que mudou em relação à versão anterior deste relatório

Uma versão anterior concluía que a prioridade ao ônibus *piorava* a rede (velocidade −11% a −17%). Aquele resultado vinha de duas fontes que esta versão corrige. (1) A regra antiga encerrava o verde repetidamente para o mesmo ônibus, inclusive ônibus parado em ponto, e
avançava o ciclo sem verificar se a próxima fase serve o ônibus; a regra refeita faz um pedido por ônibus e semáforo, ignora ônibus parados e tem uma variante condicional. (2) A contabilidade mudou: totais, velocidade e ruído usam agora só a hora de demanda (0–3600 s), e não a simulação inteira de 5400 s,
e o fator $k$ não multiplica mais o escoamento. Por isso o As-Is aparece aqui com velocidade média de cerca de #f1(D("am", "asis", "speed_kmh").mean) km/h e não mais 10,6 km/h. A lição é que a conclusão "intervenção piora a rede" dependia do detalhe da regra, o que reforça que os resultados de controle desta rede saturada têm baixa resolução.
O PI sobre programas fixos continua pior em todas as versões.

= Desenho do experimento

Mesma rede, mesmas rotas e mesmas cinco sementes (pareamento por semente), 5400 s por rodada (1 h de demanda mais 30 min de escoamento), nas duas janelas de pico. Cenários: *As-Is*, programas _actuated_ do `netconvert` (o do M2); *PI sobre fixos*, o controlador PI do M3 (amostragem de 10 s) sobre programas fixos;
*Actuated + ônibus*, prioridade ao ônibus sobreposta ao _actuated_; *Ablação*, a mesma regra aplicada a 1 em cada 30 veículos que não são ônibus (o contador também sorteia ônibus, uma imprecisão pequena), para testar o mecanismo; *Prioridade condicional*, que só encerra o verde se a próxima fase serve o ônibus;
*Onda verde*, ciclo comum e defasagens adaptativas na Rua Mariano Torres. Os parâmetros do PI e das regras foram escolhidos na sintonia do M3 (semente 11, fora das réplicas). Métricas: velocidade média espacial e veículos-km (do `edgeData` de 0–3600 s), veículos concluídos, _teleports_, fila (`queue-output`, percentil 95 ponderado por amostras),
atraso dos concluídos, emissões HBEFA, ruído (CoRTN com vazão horária e piso de 20 km/h, e harmonoise do SUMO; aproximações somadas e pontos combinados por média energética de dB) e velocidade no eixo da onda verde. Médias com IC de 95% (_t_, 4 g.l.); diferenças pareadas por semente.

= Resultados

#tbl("am", [Pico da manhã])
#tbl("pm", [Pico da tarde])

#figure(image("figures/m4_trafego.png", width: 100%), caption: [Velocidade média, fila p95 e _teleports_ (barras de erro: IC 95%).]) <fig-traf>
#figure(image("figures/m4_emis.png", width: 100%), caption: [CO₂ e NOx na janela e CO₂ por veículo-km (barras de erro: IC 95%).]) <fig-emis4>
#figure(image("figures/m4_ruido.png", width: 100%), caption: [Leq estimado por CoRTN (vazão horária, piso de 20 km/h) e por harmonoise, em P01 e P04.]) <fig-ruido4>

== Como ler

- *Estatística.* Foram feitos #EX.n_tests testes _t_ pareados com 5 pares, sem correção para múltiplas comparações e sem checagem de normalidade (com cinco pares, o teste de Wilcoxon não passa de _p_ = 0,0625). Os valores _p_ são descritivos; as conclusões apoiam-se em vários indicadores concordantes.
- *Fila.* O PI reduz a fila p95 (#dp("am", "tobe_pi", "q_p95_m")%) *e* reduz a vazão (#dp("am", "tobe_pi", "finished")% de concluídos): fila menor com menos veículos servidos não é melhora. A onda verde reduz a fila e os _teleports_ sem perder viagens concluídas (#dp("am", "tobe_gw", "finished")%), mas a velocidade no eixo cai.
- *Emissões.* Seguem a velocidade e a vazão (HBEFA responde à cinemática). Os valores absolutos de CO₂ (cerca de 700 a 900 g/km) e de CO são várias vezes os típicos da literatura para frotas leves porque a rede está engarrafada e os fatores são europeus; servem para comparar cenários, não para citar. Atraso dos concluídos e dos ônibus têm viés de sobrevivência.
- *Ruído.* O CoRTN com piso de velocidade só enxerga a vazão e praticamente não muda entre cenários. O harmonoise, que cobre baixas velocidades, sobe com a onda verde (#sg(D("am", "tobe_gw", "Leq_harm_dba").delta_mean, d: 1) dB), compatível com mais aceleração e frenagem no eixo. É um nível por aresta, sem propagação a receptores; não é uma simulação acústica completa, e não há medição de campo para validar.
- *Poeira.* A ressuspensão (AP-42, premissas assumidas) é proporcional aos veículos-km e acompanha a vazão; uma queda nela significa menos veículos-km percorridos, não benefício.

= Varredura de demanda

O As-Is é saturado e instável com 100% da demanda. Para dar resolução à comparação, o As-Is e as duas versões da prioridade ao ônibus foram simulados com 50%, 70% e 85% da demanda (3 sementes cada; o ponto de 100% usa as mesmas 3 sementes das réplicas principais).

#figure(
  table(columns: (auto, auto, auto, auto, auto), align: (left, right, right, right, right),
    [Demanda], [Velocidade As-Is (km/h)], [Velocidade To-Be (km/h)], [_Teleports_ As-Is], [_Teleports_ To-Be],
    ..("0.5", "0.7", "0.85", "1.0").map(k => ([#fix(float(k) * 100, 0)%], pm(SW.at(k).asis.speed_kmh), pm(SW.at(k).tobe.speed_kmh), pm(SW.at(k).asis.teleports, d: 0), pm(SW.at(k).tobe.teleports, d: 0))).flatten()),
  caption: [Varredura de demanda (manhã, média ± IC 95%, 3 sementes). To-Be = _actuated_ + prioridade ao ônibus.],
)
#figure(image("figures/m4_sweep.png", width: 100%), caption: [Velocidade, _teleports_ e fila p95 por nível de demanda (IC 95%, 3 sementes).]) <fig-sweep>

Com 50% da demanda a rede flui (cerca de 35 km/h, nenhum _teleport_) e As-Is e To-Be são indistinguíveis: a prioridade ao ônibus não tem efeito mensurável. Entre 70% e 100% a rede entra num regime instável em que as sementes divergem (os IC chegam a ±17 km/h com 3 sementes): algumas rodadas travam e outras não, de modo que *a comparação não tem resolução*,
mesmo quando a média do To-Be parece melhor (como em 70%). Dizer que a prioridade ao ônibus "ajuda" ou "atrapalha" nessa faixa seria superinterpretar o ruído. A versão condicional coincide com a básica em dois dos três níveis, indicando que sua condição quase nunca restringiu a decisão.

= Diagnóstico de congestionamento

Uma rodada do As-Is com avisos ligados registrou #TP.total _teleports_ (#f0(TP.by_reason.jam) por congestionamento, #f0(TP.by_reason.yield) por _yield_ e #f0(TP.by_reason.at("wrong lane")) por faixa errada), concentrados em #TP.distinct_edges arestas; #f0(100 * TP.top10_share)% ocorrem nas dez piores,
das quais oito na Rua Conselheiro Laurindo (duas faixas, com vários semáforos inferidos), e as demais na Rua Brasílio Itiberê e na Rua Chile. O engarrafamento do As-Is é, portanto, um defeito *localizado* da rede e da demanda sorteada, não sobrecarga uniforme. Corrigir esses eixos com dados reais (contagens, fases) é o passo que mais ganharia resolução.

= Modos ativos

A comparação usa redes com pedestres, ciclovias e as faixas exclusivas de bicicleta propostas, com demanda de pedestres e ciclistas #ph(body: [provisória]) e três réplicas. Três cenários separam os efeitos: *As-Is ativo* (_actuated_ padrão), *só faixas de bicicleta* e *To-Be ativo* (faixas mais prioridade ao ônibus).

#figure(
  table(columns: (1fr, auto, auto, auto), align: (left, right, right, right),
    [Indicador], [As-Is ativo], [Só faixas de bicicleta], [To-Be ativo],
    [Atraso médio dos veículos motorizados (s)], [#pm(AC.asis_act.car_delay_s, d: 0)], [#pm(AC.bike_only.car_delay_s, d: 0)], [#pm(AC.tobe_act.car_delay_s, d: 0)],
    [Pedestres concluídos], [#pm(AC.asis_act.persons, d: 0)], [#pm(AC.bike_only.persons, d: 0)], [#pm(AC.tobe_act.persons, d: 0)],
    [Perda de tempo média dos pedestres (s)], [#pm(AC.asis_act.ped_timeloss_s, d: 1)], [#pm(AC.bike_only.ped_timeloss_s, d: 1)], [#pm(AC.tobe_act.ped_timeloss_s, d: 1)],
    [Ciclistas concluídos], [#pm(AC.asis_act.bikes, d: 0)], [#pm(AC.bike_only.bikes, d: 0)], [#pm(AC.tobe_act.bikes, d: 0)],
    [Velocidade média dos ciclistas (km/h)], [#pm(AC.asis_act.bike_speed_kmh)], [#pm(AC.bike_only.bike_speed_kmh)], [#pm(AC.tobe_act.bike_speed_kmh)],
    [Perda de tempo média dos ciclistas (s)], [#pm(AC.asis_act.bike_delay_s, d: 0)], [#pm(AC.bike_only.bike_delay_s, d: 0)], [#pm(AC.tobe_act.bike_delay_s, d: 0)]),
  caption: [Modos ativos (manhã, 3 réplicas, média ± IC 95%). Demanda #ph(body: [provisória]). Rotas inválidas em uma variante são descartadas pelo SUMO.],
)

*Resultado:* sem efeito mensurável das faixas de bicicleta nem do controle sobre pedestres e ciclistas (médias praticamente iguais), com possível custo para os veículos motorizados: o teste pareado (n = 3, sem correção) dá +#fix(EX.active_paired.bike_only_vs_asis_car_delay.diff, 0) s de atraso para só faixas (_p_ = #fix(EX.active_paired.bike_only_vs_asis_car_delay.p, 3)),
mas a rede com faixas tem mais semáforos inferidos (256 contra 233), o que confunde o efeito, e o As-Is ativo é outra rede que o As-Is principal. Era esperado: as rotas dos ciclistas são pré-calculadas e não desviam para as novas faixas, os pedestres usam calçadas e travessias do modelo padrão e o controlador não vê pedestres. O experimento não permite concluir sobre faixas de bicicleta.

= Viabilidade para Curitiba e limites

#table(columns: (auto, 1fr), [Aspecto], [Avaliação],
  [Controlador PI], [Piorou a rede em todas as versões; não se justifica implantar. Exigiria sintonia com dados reais, semáforos reais, sensores reais (não idealizados) e modelagem de pedestres.],
  [Prioridade ao ônibus], [Tecnicamente simples (detecção por GPS/transponder da URBS e comando de fase), mas *sem efeito mensurável* nesta rede e com rotas de ônibus aleatórias; só vale reavaliar com as linhas reais e corredores exclusivos.],
  [Onda verde], [Reduziu fila e _teleports_ mas reduziu a velocidade no eixo e elevou o ruído harmonoise; implementação sobre semáforos inferidos e um só sentido. Exige fases reais e coordenação bidirecional.],
  [Faixas de bicicleta], [Desenho sem estudo de largura de via, estacionamento, desapropriação, custo e segurança; hipótese, não recomendação.],
  [Comunicação e sensoriamento], [Latência e tráfego de mensagens são desprezíveis frente ao período de 5 s, em localhost. Falta teste em rede real e custo de instalação e manutenção.],
  [Evidência], [Todas as entradas quantitativas são provisórias e a rede opera em regime instável acima de ~50% da demanda. O resultado vale como teste de método e não como estimativa de benefício.],
)

*Para que o relatório final tenha valor de engenharia faltam:* (1) contagens de veículos, pedestres e ciclistas e medições de Leq; (2) fases e localização dos semáforos (e a Av. Floriano, que ficou sem semáforos na inferência); (3) itinerários e telemetria reais da URBS; (4) calibração com tempos de viagem e filas; (5) fatores de emissão e frota locais, CO₂e e CO₂ biogênico; (6) correção dos gargalos localizados do As-Is e revisão do polígono de estudo.

= Perguntas esperadas da banca

#table(columns: (1fr, 2fr), [Pergunta], [Resposta honesta],
  [As intervenções reduziram as emissões?], [Não. O PI as aumentou de forma robusta; prioridade ao ônibus e onda verde não mostraram redução consistente. Não afirmamos benefício.],
  [Por que o resultado mudou entre versões?], [A regra de prioridade ao ônibus foi refeita (um pedido por ônibus e semáforo) e a contabilidade corrigida (1 h de demanda). Mostra que as conclusões em rede saturada dependem de detalhes de implementação, e é por isso que há réplicas, ablação e varredura.],
  [O modelo está calibrado?], [O procedimento GEH foi executado, mas o critério de 85% não foi atingido (manhã 76,5%, tarde 82,4%), sobre contagens sorteadas e só dois pontos com aproximação motorizada.],
  [Por que o PI foi pior que o _actuated_?], [Provável combinação de perda da lógica por detectores ao converter para programas fixos, sensores idealizados, erro de fila sem normalização e rede saturada; não isolamos qual domina.],
  [Qual é a contribuição?], [Um pipeline aberto e reproduzível, um teste de método com réplicas, ablação, varredura de demanda e diagnóstico de gargalos, relato do resultado negativo e uma lista objetiva do que falta medir.],
)

#bibliography("refs.bib", style: "associacao-brasileira-de-normas-tecnicas", title: [Referências])
