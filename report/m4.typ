#import "lib.typ": *

#let R = json("figures/m4_results.json")
#let SW = json("figures/m4_sweep.json")
#let AC = json("figures/m4_active.json")
#let RB = json("figures/m4_realbus.json")
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
#let pv(o) = if o.at("p_paired", default: none) == none { "n/d" } else { fix(o.p_paired, 2) }
#let cell(w, s, m) = {
  let o = D(w, s, m)
  if o.at("delta_pct", default: none) == none { [n/d] } else { [#sg(o.delta_pct)% (#pv(o))] }
}

#let ROWS = (
  ("Velocidade média (km/h)", "speed_kmh", 1), ("Veículos inseridos", "inserted", 0), ("Veículos concluídos", "finished", 0), ("Teleports", "teleports", 0), ("Fila p95 (m)", "q_p95_m", 0),
  ("Atraso dos concluídos (s)", "delay_s", 0), ("Atraso dos ônibus (s)", "bus_delay_s", 0), ("CO₂ na janela (t)", "CO2_t_window", 1),
  ("CO₂ por veículo-km (g)", "CO2_g_per_vkm", 0), ("NOx na janela (kg)", "NOx_kg_window", 1), ("Leq harmonoise (dB)", "Leq_harm_dba", 1),
  ("Leq CoRTN (dB)", "Leq_cortn_dba", 1), ("Velocidade no eixo, sentido da onda (km/h)", "corridor_speed_fwd_kmh", 1), ("Velocidade no eixo, sentido oposto (km/h)", "corridor_speed_rev_kmh", 1))
#let SC = ("tobe_pi", "tobe", "tobe_gw", "tobe_fixed90")
// Leq: diferença em dB (Δ% de dB não tem sentido); demais: Δ%
#let cellx(w, s, m) = {
  let o = D(w, s, m)
  if o.at("delta_pct", default: none) == none { [n/d] }
  else if m.starts-with("Leq") { [#sg(o.delta_mean, d: 1) dB (#pv(o))] }
  else { [#sg(o.delta_pct)% (#pv(o))] }
}

#let tbl(w, title) = figure(
  table(columns: (3.5cm, 2.1cm, 2.2cm, 2.2cm, 2.2cm, 2.4cm), align: (left, right, right, right, right, right), inset: (x: 3pt, y: 3.5pt),
    [Indicador], [As-Is], [PI sobre fixos], [Actuated + ônibus], [Onda verde], [Controle: fixo 90 s],
    ..ROWS.map(r => (r.at(0), pm(D(w, "asis", r.at(1)), d: r.at(2)), ..SC.map(s => cellx(w, s, r.at(1))))).flatten()),
  caption: [#title: As-Is em média ± IC 95% (5 réplicas); demais colunas em Δ% médio pareado (Leq em dB), com o valor _p_ do teste _t_ pareado entre parênteses. "Controle: fixo 90 s" são os mesmos programas fixos da onda verde, com defasagens aleatórias. Dados #ph(body: [provisórios]).],
)

#let SR = csv("figures/m4_sweep_runs.csv", row-type: dictionary)
#let sv(sc, s, k) = {
  let r = SR.filter(x => calc.abs(float(x.scale) - sc) < 0.001 and x.scenario == s and int(float(x.seed)) == k)
  if r.len() == 0 { [—] } else { [#fix(float(r.first().speed_kmh), 1)] }
}
#let DEC = json("figures/m4_decisions.json")

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

- *Escopo.* Pipeline aberto e reproduzível (Overture/IPPUC → SUMO → calibração GEH → emissões, poeira, ruído e fila) e intervenções de controle semafórico avaliadas com 5 sementes por janela, uma varredura de demanda (50% a 100%) e um controle para a onda verde.
- *PI sobre programas fixos:* a velocidade média fica abaixo da do As-Is em #R._sign.tobe_pi.n_slower de #R._sign.tobe_pi.n_pairs pares semente-janela (teste do sinal _p_ = #fix(R._sign.tobe_pi.p_sign, 3)); média #dp("am", "tobe_pi", "speed_kmh")% na manhã e #dp("pm", "tobe_pi", "speed_kmh")% na tarde, CO₂ por veículo-km #dp("am", "tobe_pi", "CO2_g_per_vkm")% e #dp("pm", "tobe_pi", "CO2_g_per_vkm")%. Depois da correção de Benjamini–Hochberg sobre os 36 testes dos desfechos primários, só os veículos concluídos na tarde (#dp("pm", "tobe_pi", "finished")%) permanecem significativos; a conclusão é robusta no sinal, não em cada valor _p_.
- *Prioridade ao ônibus (regra refeita):* efeito estatisticamente nulo (velocidade #dp("am", "tobe", "speed_kmh")% e #dp("pm", "tobe", "speed_kmh")%; mais lenta em só #R._sign.tobe.n_slower de #R._sign.tobe.n_pairs pares). A regra tomou poucas decisões de troca de fase (#DEC.tobe_s1_am.switch na manhã da semente 1, contra #DEC.tobe_s1_am.extend extensões de verde); a variante "condicional" tomou *exatamente as mesmas* decisões, porque em 201 dos 223 semáforos há só duas fases verdes e a condição nunca restringe. A ablação com ônibus falsos dá resultado do mesmo tipo.
- *Onda verde adaptativa (Rua Mariano Torres):* *piora* a rede de forma consistente (mais lenta em #R._sign.tobe_gw.n_slower de #R._sign.tobe_gw.n_pairs pares; atraso dos concluídos #dp("am", "tobe_gw", "delay_s")% e #dp("pm", "tobe_gw", "delay_s")%; #dp("pm", "tobe_gw", "inserted")% de veículos inseridos na tarde). A queda de velocidade no eixo (#dp("am", "tobe_gw", "corridor_speed_kmh")%) vem principalmente de trocar o _actuated_ por programas fixos: o controle sem coordenação cai quase o mesmo (#dp("am", "tobe_fixed90", "corridor_speed_kmh")%), e a coordenação, medida contra esse controle, ainda aumenta o atraso e os _teleports_ (ver abaixo).
- *Por que confiar pouco.* Demanda, semáforos, linhas de ônibus e perfil horário são provisórios; a calibração GEH não atingiu 85%; a rede só flui até cerca de 60% da demanda e é instável acima disso; os _teleports_ se concentram em poucas arestas; e os testes são descritivos (n = 5).
- *Não feito.* Medição de campo, linhas reais da URBS, semáforos reais, pedestres no controle, CO₂e e CO₂ biogênico, onda verde nos dois sentidos.

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

== Ablação e variante condicional

#figure(
  table(columns: (3.8cm, 2.3cm, 2.3cm, 2.3cm, 2.3cm), align: (left, right, right, right, right), inset: (x: 3pt, y: 3.5pt),
    [Indicador (Δ% vs As-Is)], [Manhã: ablação], [Manhã: condicional], [Tarde: ablação], [Tarde: condicional],
    ..(("Velocidade média", "speed_kmh"), ("Veículos concluídos", "finished"), ("CO₂ por veículo-km", "CO2_g_per_vkm"), ("Fila p95", "q_p95_m")).map(r => (r.at(0), cell("am", "tobe_fake", r.at(1)), cell("am", "tobe_bus2", r.at(1)), cell("pm", "tobe_fake", r.at(1)), cell("pm", "tobe_bus2", r.at(1)))).flatten()),
  caption: [Ablação (regra aplicada a 1 em cada 30 veículos que não são ônibus) e prioridade condicional, em Δ% médio pareado (valor _p_ entre parênteses).],
)

A *prioridade condicional é idêntica à básica por construção*: em 201 dos 223 semáforos há exatamente duas fases verdes e a próxima fase verde sempre serve a aproximação que está no vermelho; nas rodadas verificadas (semente 1, as duas janelas) o número de decisões coincide ao inteiro. A ablação dá resultado do mesmo tipo que a prioridade verdadeira, de modo que nada atribui qualquer efeito à detecção de ônibus.
As decisões da semente 1 foram #DEC.tobe_s1_am.switch trocas e #DEC.tobe_s1_am.extend extensões de verde na manhã (#DEC.tobe_s1_pm.switch e #DEC.tobe_s1_pm.extend na tarde), em 223 semáforos e 5400 s: a regra dispara pouco, e "sem efeito" significa em boa parte "quase não atuou".

== Onda verde contra o controle de programas fixos

A onda verde substitui os programas _actuated_ do eixo por programas fixos de 90 s; por isso a comparação justa é contra *os mesmos programas fixos sem coordenação* (defasagens aleatórias). Diferença onda verde menos controle, em médias pareadas (_p_ do teste _t_):

#figure(
  table(columns: (auto, auto, auto, auto, auto), align: (left, right, right, right, right),
    [Indicador], [Onda verde (manhã)], [Controle (manhã)], [Diferença], [_p_],
    ..(("Velocidade média (km/h)", "speed_kmh", 1), ("Atraso dos concluídos (s)", "delay_s", 0), ("Teleports", "teleports", 0), ("Veículos inseridos", "inserted", 0), ("Velocidade no eixo, sentido da onda (km/h)", "corridor_speed_fwd_kmh", 1), ("Velocidade no eixo, sentido oposto (km/h)", "corridor_speed_rev_kmh", 1)).map(r => (r.at(0), fix(R._wave_vs_fixed.am.at(r.at(1)).gw, r.at(2)), fix(R._wave_vs_fixed.am.at(r.at(1)).fixed, r.at(2)), sg(R._wave_vs_fixed.am.at(r.at(1)).diff, d: r.at(2)), fix(R._wave_vs_fixed.am.at(r.at(1)).p, 2))).flatten()),
  caption: [Efeito da coordenação (onda verde menos controle de programas fixos com defasagens aleatórias), manhã, 5 sementes pareadas.],
)

A coordenação, tal como implementada, *não ajuda*: contra o controle ela piora o atraso e os _teleports_ e não melhora a velocidade no sentido favorecido. Há razões prováveis: os programas dos semáforos do eixo são todos de duas fases (42 s/3 s/42 s/3 s), de modo que o reescalonamento do ciclo quase não muda as durações e a onda se reduz a defasagens
entre semáforos de uma rede em engarrafamento (onde a progressão a 40 km/h não existe), e a onda só favorece um sentido; vários semáforos do eixo ficam a 0–1 m um do outro (nós duplicados, não cruzamentos distintos). O controle, por sua vez, *reduziu* os _teleports_ do As-Is pela metade (#dp("am", "tobe_fixed90", "teleports")%), o que sugere que programas fixos nesse eixo dosam a entrada na Rua Conselheiro Laurindo; é um achado sobre o modelo, não uma recomendação.

== Como ler

- *Estatística.* Os desfechos primários foram declarados a priori (velocidade média, veículos concluídos e CO₂ por veículo-km), com #R._primary.len() testes _t_ pareados (6 cenários × 2 janelas × 3 desfechos) e correção de Benjamini–Hochberg sobre todos eles: só #R._primary.filter(x => x.q_bh < 0.05).len() sobrevive a _q_ < 0,05. Os demais #EX.n_tests testes da tabela são exploratórios, sem correção, com 5 pares e sem checagem de normalidade (o teste de Wilcoxon não passa de _p_ = 0,0625 com 5 pares). Por isso as conclusões usam também o teste do sinal sobre os 10 pares semente-janela e a concordância entre indicadores.
- *Fila.* O PI e a onda verde reduzem a fila p95 em parte porque servem menos veículos: o PI conclui #dp("am", "tobe_pi", "finished")% de viagens e a onda verde insere #dp("am", "tobe_gw", "inserted")% de veículos na manhã (demanda retida na borda da rede). Fila menor com menos veículos servidos não é melhora.
- *Emissões.* Seguem a velocidade e a vazão (HBEFA responde à cinemática). Os valores absolutos de CO₂ (cerca de 700 a 900 g/km) e de CO são várias vezes os típicos da literatura para frotas leves porque a rede está engarrafada e os fatores são europeus; servem para comparar cenários, não para citar. Atraso dos concluídos e dos ônibus têm viés de sobrevivência.
- *Ruído.* Os níveis são mostrados como diferença em dB (um Δ% de dB não tem sentido). O CoRTN com piso de velocidade só enxerga a vazão e praticamente não muda entre cenários. O harmonoise sobe cerca de 1,2 a 1,6 dB nos dois cenários com os semáforos do eixo da Rua Mariano Torres em programa fixo (onda verde e controle), e quase nada nos demais; inclusive no controle sem coordenação (#sg(D("am", "tobe_fixed90", "Leq_harm_dba").delta_mean, d: 1) dB): mais provavelmente reflete mais veículos-segundo em fila nas arestas do que aceleração e frenagem. É um nível de fonte por aresta, sem propagação a receptores; P04 (Rua XV × Rua Mariano Torres) fica no eixo da onda e P01 não. Não é uma simulação acústica completa e não há medição de campo.
- *Poeira.* A ressuspensão (AP-42, premissas assumidas) é proporcional aos veículos-km; uma queda nela significa menos veículos-km percorridos, não benefício.

= Prioridade ao ônibus com demanda de ônibus real

Os dados abertos da URBS (espelho da UFPR/C3SL, `dadosabertos.c3sl.ufpr.br/curitibaurbs`) incluem o GPS de todos os ônibus. Usamos a quinta-feira 12/11/2026: no horário de pico passam
#RB.n_real_buses.am ônibus (manhã) e #RB.n_real_buses.pm (tarde) pela área, com map-matching na rede e horário real de partida. O sorteio provisório usava só 131 por hora: a demanda real de ônibus é cerca de cinco vezes maior, e a rede fica mais congestionada (velocidade média 14,2 contra 15,4 km/h).

#table(columns: (auto, auto, auto, auto), align: (left, right, right, right),
  [*Janela*], [*Velocidade do ônibus no SUMO*], [*Velocidade real (GPS)*], [*Correlação de postos*],
  [Manhã], [#calc.round(RB.validation.am.sim_kmh, digits: 1) km/h], [#calc.round(RB.validation.am.real_kmh, digits: 1) km/h], [#calc.round(RB.validation.am.spearman, digits: 2)],
  [Tarde], [#calc.round(RB.validation.pm.sim_kmh, digits: 1) km/h], [#calc.round(RB.validation.pm.real_kmh, digits: 1) km/h], [#calc.round(RB.validation.pm.spearman, digits: 2)])

O SUMO é cerca de 40% mais rápido que o GPS: o real inclui paradas de embarque, que o modelo não representa (limitação). A prioridade ao ônibus, com 5 sementes por janela, continua sem efeito mensurável sobre o ônibus:
variação da velocidade do ônibus de #calc.round(RB.am.tobe_rb.bus_speed_kmh.diff, digits: 1) km/h na manhã (p = #calc.round(RB.am.tobe_rb.bus_speed_kmh.p, digits: 2)) e #calc.round(RB.pm.tobe_rb.bus_speed_kmh.diff, digits: 1) km/h na tarde (p = #calc.round(RB.pm.tobe_rb.bus_speed_kmh.p, digits: 2)).
Com ônibus reais a regra dispara bem mais (cerca de 1.300 extensões e 110 trocas por hora), mas o resultado não muda. A variante condicional repete a básica, como esperado. O sinal de menos teleports (−63 na manhã, p = 0,09) não é significativo.

= Varredura de demanda

O As-Is é saturado e instável com 100% da demanda. Para dar resolução à comparação, o As-Is e as duas versões da prioridade ao ônibus foram simulados com 50%, 60%, 70% e 85% da demanda (3 sementes cada; o ponto de 100% usa as mesmas 3 sementes das réplicas principais).

#figure(
  table(columns: (auto, auto, auto, auto, auto), align: (left, right, right, right, right),
    [Demanda], [Velocidade As-Is (km/h)], [Velocidade To-Be (km/h)], [_Teleports_ As-Is], [_Teleports_ To-Be],
    ..("0.5", "0.6", "0.7", "0.85", "1.0").map(k => ([#fix(float(k) * 100, 0)%], pm(SW.at(k).asis.speed_kmh), pm(SW.at(k).tobe.speed_kmh), pm(SW.at(k).asis.teleports, d: 0), pm(SW.at(k).tobe.teleports, d: 0))).flatten()),
  caption: [Varredura de demanda (manhã, média ± IC 95%, 3 sementes). To-Be = _actuated_ + prioridade ao ônibus.],
)
#figure(
  table(columns: (auto, auto, auto, auto, auto, auto, auto), align: (left, right, right, right, right, right, right), inset: (x: 3pt, y: 3pt),
    [Demanda], [As-Is s1], [As-Is s2], [As-Is s3], [To-Be s1], [To-Be s2], [To-Be s3],
    ..(0.5, 0.6, 0.7, 0.85, 1.0).map(sc => ([#fix(sc * 100, 0)%], sv(sc, "asis", 1), sv(sc, "asis", 2), sv(sc, "asis", 3), sv(sc, "tobe", 1), sv(sc, "tobe", 2), sv(sc, "tobe", 3))).flatten()),
  caption: [Velocidade média (km/h) por semente, por nível de demanda: a instabilidade entre 70% e 100% vem de sementes que travam e sementes que não travam.],
)
#figure(image("figures/m4_sweep.png", width: 100%), caption: [Velocidade, _teleports_ e fila p95 por nível de demanda (IC 95%, 3 sementes).]) <fig-sweep>

Com 50% e 60% da demanda a rede flui (cerca de 34 a 35 km/h, nenhum _teleport_ a 50%) e As-Is e To-Be são indistinguíveis. Entre 70% e 100% a rede entra num regime instável em que as sementes divergem: em 70%, por exemplo, uma ou mais sementes do As-Is travam enquanto outras não, e os IC chegam a ±17 km/h com 3 sementes; por isso a média do To-Be parece melhor em 70% e pior em 85%, sem que haja resolução para dizer qual vale.
*A rede só tem resolução até cerca de 60% da demanda*, onde a prioridade ao ônibus não tem efeito mensurável. A versão condicional é idêntica à básica em 50%, 60% e 100% e difere ligeiramente em 70% e 85% (sementes em que a trajetória divergiu), o que é coerente com a identidade por construção descrita acima mais o caos numérico próximo da saturação.

= Diagnóstico de congestionamento

Uma rodada do As-Is (semente 1, manhã) com avisos ligados registrou #TP.total _teleports_ (#f0(TP.by_reason.jam) por congestionamento, #f0(TP.by_reason.yield) por _yield_ e #f0(TP.by_reason.at("wrong lane")) por faixa errada), concentrados em #TP.distinct_edges arestas; #f0(100 * TP.top10_share)% ocorrem nas dez piores, das quais #TP.top10_laurindo
são arestas da Rua Conselheiro Laurindo (duas faixas, com vários semáforos inferidos) e as demais na Rua Brasílio Itiberê, na Rua Chile e numa junção entre a Chile e a Laurindo. O engarrafamento do As-Is é, portanto, um defeito *localizado* da rede e da demanda sorteada (uma única semente analisada), não sobrecarga uniforme. Corrigir esses eixos com dados reais (contagens, fases) é o passo que mais ganharia resolução.

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
  [Onda verde], [Pior que o As-Is e que o controle de programas fixos em atraso e _teleports_; implementação sobre semáforos inferidos e um só sentido. Exige fases reais, coordenação bidirecional e comparação com o _actuated_ coordenado.],
  [Faixas de bicicleta], [Desenho sem estudo de largura de via, estacionamento, desapropriação, custo e segurança; hipótese, não recomendação.],
  [Comunicação e sensoriamento], [Latência e tráfego de mensagens são desprezíveis frente ao período de 5 s, em localhost. Falta teste em rede real e custo de instalação e manutenção.],
  [Evidência], [Todas as entradas quantitativas são provisórias e a rede opera em regime instável acima de ~50% da demanda. O resultado vale como teste de método e não como estimativa de benefício.],
)

*Para que o relatório final tenha valor de engenharia faltam:* (1) contagens de veículos, pedestres e ciclistas e medições de Leq; (2) fases e localização dos semáforos (e a Av. Floriano, que ficou sem semáforos na inferência); (3) itinerários e telemetria reais da URBS; (4) calibração com tempos de viagem e filas; (5) fatores de emissão e frota locais, CO₂e e CO₂ biogênico; (6) correção dos gargalos localizados do As-Is e revisão do polígono de estudo.

= Perguntas esperadas da banca

#table(columns: (1fr, 2fr), [Pergunta], [Resposta honesta],
  [As intervenções reduziram as emissões?], [Não. O PI as aumentou (robusto no sinal); a prioridade ao ônibus não teve efeito e a onda verde piorou o atraso; nenhuma mostrou redução. Não afirmamos benefício.],
  [Por que o resultado mudou entre versões?], [A regra de prioridade ao ônibus foi refeita (um pedido por ônibus e semáforo) e a contabilidade corrigida (1 h de demanda). Mostra que as conclusões em rede saturada dependem de detalhes de implementação, e é por isso que há réplicas, ablação e varredura.],
  [O modelo está calibrado?], [O procedimento GEH foi executado, mas o critério de 85% não foi atingido (manhã 76,5%, tarde 82,4%), sobre contagens sorteadas e só dois pontos com aproximação motorizada.],
  [Por que o PI foi pior que o _actuated_?], [Provável combinação de perda da lógica por detectores ao converter para programas fixos, sensores idealizados, erro de fila sem normalização e rede saturada; não isolamos qual domina.],
  [Qual é a contribuição?], [Um pipeline aberto e reproduzível, um teste de método com réplicas, ablação, varredura de demanda e diagnóstico de gargalos, relato do resultado negativo e uma lista objetiva do que falta medir.],
)

#bibliography("refs.bib", style: "associacao-brasileira-de-normas-tecnicas", title: [Referências])
