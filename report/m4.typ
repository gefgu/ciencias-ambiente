#import "lib.typ": *

#let R = json("figures/m4_results.json")
#let AC = json("figures/m4_active.json")
#let EX = json("figures/m4_extra.json")
#let fix(x, d) = {
  if d == 0 { return str(int(calc.round(float(x)))) }
  let s = str(calc.round(float(x), digits: d))
  if not s.contains(".") { s = s + "." + "0" * d } else { let n = s.split(".").at(1).len(); s = s + "0" * (d - n) }
  s.replace(".", ",")
}
#let f1(x) = fix(x, 1)
#let f2(x) = fix(x, 2)
#let f0(x) = {
  let s = str(calc.round(float(x), digits: 0)).replace(regex("\.0$"), "")
  s.clusters().rev().chunks(3).map(c => c.join()).join(".").clusters().rev().join()
}
#let pm(o, d: 1) = [#fix(o.mean, d) ± #fix(o.ci95, d)]
#let pc(o) = if o.at("delta_pct", default: none) == none { [n/d] } else {
  let v = o.delta_pct
  let s = if v > 0 { "+" } else { "" }
  [#s#fix(v, 1)%]
}
#let pv(o) = if o.at("p_paired", default: none) == none { [n/d] } else if o.p_paired < 0.001 { [< 0,001] } else { [#fix(o.p_paired, 3)] }

// linhas da tabela de comparação (To-Be × As-Is) para uma janela
#let rows(w) = {
  let items = (
    ("Atraso médio dos concluídos (s)", "delay_s", 0), ("Velocidade média espacial (km/h)", "speed_kmh", 1), ("Veículos concluídos", "finished", 0),
    ("Teleports", "teleports", 0), ("Atraso médio dos ônibus (s)", "bus_delay_s", 0), ("CO₂ na janela (t)", "CO2_t_window", 1),
    ("CO₂ por veículo-km (g/km)", "CO2_g_per_vkm", 0), ("NOx na janela (kg)", "NOx_kg_window", 1), ("CO na janela (kg)", "CO_kg_window", 0),
    ("MP escapamento (kg)", "PMx_kg_window", 2), ("Leq médio estimado (dB)", "Leq_mean_dba", 1))
  items.map(it => {
    let a = R.at(w).asis.at(it.at(1))
    let b = R.at(w).tobe.at(it.at(1))
    let c = R.at(w).tobe_pi.at(it.at(1))
    let d = R.at(w).tobe_fake.at(it.at(1))
    (it.at(0), pm(a, d: it.at(2)), pm(b, d: it.at(2)), pc(b), pv(b), pc(c), pc(d))
  }).flatten()
}

#show: report.with(
  title: "Comparação As-Is × To-Be e viabilidade",
  subtitle: "Resultados da simulação integrada, impacto ambiental e limites da evidência",
  course: "Ciências do Ambiente", program: "Projeto 1", milestone: "Marco 4 · Operar",
  authors: ((name: "Gustavo Henrique Bruno dos Santos", role: "Computação"), (name: "[integrante]", role: "Elétrica e Automação"), (name: "[integrante]", role: "Mecânica")),
  date: "15 de novembro de 2026",
  abstract: [
    Compara o cenário atual (programas _actuated_ do SUMO) com duas intervenções, com cinco réplicas por cenário e janela e testes pareados por semente: (i) um controlador PI sobre programas fixos e
    (ii) o _actuated_ com prioridade ao ônibus, mais uma ablação. *Neste modelo, e com estas implementações, nenhuma intervenção melhorou o cenário atual:* o PI reduziu a velocidade média de forma robusta
    e elevou as emissões; a prioridade ao ônibus reduziu a velocidade (significativa na tarde, fraca na manhã) e elevou o CO₂ de modo estatisticamente fraco. O modelo é um cenário saturado, com demanda #ph(body: [provisória]),
    semáforos inferidos e rotas de ônibus aleatórias, e várias métricas exigidas (fila, simulação acústica) não foram calculadas; o resultado não prevê o que ocorreria em Curitiba.
  ],
)

= Resumo executivo

- *O que foi feito.* Pipeline aberto e reproduzível (Overture/IPPUC → SUMO → calibração GEH → emissões, poeira e ruído) e duas intervenções de controle semafórico, avaliadas contra o cenário atual com 5 réplicas por janela.
- *Resultado.* O PI sobre programas fixos piorou a rede (velocidade −24% na manhã e −30% na tarde; CO₂ +19% e +25%). A prioridade ao ônibus sobre o _actuated_ também a piorou (velocidade −11% e −17%; CO₂ +5% e +10%, com significância fraca na manhã). *Não houve redução de emissões.*
- *Por que confiar pouco.* Demanda, semáforos, linhas de ônibus e perfil horário são provisórios; a calibração GEH não atingiu 85%; o As-Is está saturado (cerca de 13% dos veículos carregados ainda na rede ao fim e 210 a 230 _teleports_ por hora de demanda); e uma sintonia com uma única semente sugeria o contrário, o que mede a instabilidade do modelo.
- *Não calculado.* Comprimento de fila; simulação acústica (só uma estimativa CoRTN em dois pontos); CO₂e e CO₂ biogênico; onda verde.
- *O que falta para valer como engenharia.* Contagens e Leq de campo, fases dos semáforos, itinerários da URBS, e um As-Is calibrado que não esteja em gargalo (ver a lista ao final).

= Desenho do experimento

Três cenários (mais a ablação), mesma rede, mesmas rotas e mesmas cinco sementes (pareamento por semente), simulados por 5400 s (1 h de demanda mais 30 min de escoamento) nas duas janelas de pico:
*As-Is*, programas _actuated_ do `netconvert`, o mesmo do M2; *To-Be PI*, o controlador PI do M3 sobre programas fixos (parâmetros: amostragem de 10 s, os demais padrão);
*To-Be*, o _actuated_ original com prioridade ao ônibus sobreposta; e uma *ablação*, a mesma regra aplicada a 1 em cada 30 veículos que não são ônibus, para testar se algum efeito vem da detecção de ônibus ou só do encerramento forçado de verdes. Os dois To-Be foram escolhidos na sintonia do M3 (uma semente à parte, 11), de modo que a avaliação aqui usa sementes independentes. As emissões usam as classes HBEFA3 do SUMO;
o ruído, o CoRTN a 10 m com velocidade de piso 20 km/h. Estimativas por média e intervalo de confiança de 95% (_t_ de Student, 4 graus de liberdade); a diferença para o As-Is é pareada por semente.

= Resultado principal

Com cinco sementes por janela, *as duas intervenções pioraram as métricas de rede* neste modelo. O PI sobre programas fixos reduz a velocidade média espacial em cerca de 24% (manhã) e 30% (tarde) e eleva o CO₂ em 19% e 25%, com significância razoável (_p_ ≤ 0,025).
A prioridade ao ônibus sobre o _actuated_ reduz a velocidade em 11% (manhã, _p_ = 0,07) e 17% (tarde, _p_ = 0,02) e conclui menos viagens (−5% e −10%); o CO₂ sobe 5% (manhã, _p_ = 0,16, não significativo) e 10% (tarde, _p_ = 0,05). Os _teleports_ crescem de 38% a 68%, conforme o cenário e a janela.
O atraso médio dos ônibus que concluem a viagem cai cerca de 19% e 18%, e na tarde o atraso médio dos concluídos cai 16%, mas ambos têm viés de sobrevivência: os cenários concluem menos viagens. A ablação, que aplica a mesma regra a 1 em cada 30 veículos que não são ônibus,
produz queda de atraso de ônibus igual ou maior (−25% e −24%) e velocidade e CO₂ semelhantes à do To-Be: a queda de atraso *não se deve à detecção de ônibus*, e sim ao encerramento forçado de verdes, e a regra não distingue o veículo que a aciona.

*O que isso não diz.* (1) A conclusão vale para *estas implementações neste modelo*, e não para controle adaptativo ou prioridade ao ônibus em geral. Em `tobe.py` a prioridade ao ônibus encerra o verde atual avançando o ciclo, o que pode não servir a fase do ônibus e pode truncar verdes repetidamente; ela se aplica a todos os 223 semáforos e a todas as aproximações, e não a corredores exclusivos como as canaletas de Curitiba;
a ablação mostra, portanto, que a *atuação* é pouco seletiva, e não que prioridade ao ônibus bem projetada falharia. (2) O As-Is está em saturação instável: a mesma regra de prioridade deu +14% de velocidade na semente de sintonia e −11% a −17% nas cinco réplicas, uma oscilação de cerca de 25 pontos que mede a sensibilidade do modelo; comparar controladores dentro de uma rede em engarrafamento tem pouca resolução.
(3) Teleports e veículos retidos entram nas métricas de formas diferentes entre cenários, e o corte em 5400 s deixa de fora as emissões futuras dos veículos ainda na rede, o que favorece o cenário que retém mais.

= Resultados de tráfego, emissões e ruído

#let tbl(w, title) = figure(
  table(columns: (4.3cm, 2.4cm, 2.4cm, 1.5cm, 1.3cm, 1.5cm, 1.6cm), align: (left, right, right, right, right, right, right), inset: (x: 4pt, y: 4pt),
    [Indicador], [As-Is], [To-Be], [Δ To-Be], [_p_], [Δ PI fixo], [Δ ônibus falsos],
    ..rows(w)),
  caption: [#title: média ± IC 95% (5 réplicas). To-Be = _actuated_ + prioridade ao ônibus. Δ é a diferença média pareada em % da média do As-Is; _p_ é do teste _t_ pareado do To-Be; "PI fixo" é o PI sobre programas fixos; "ônibus falsos" é a ablação. Dados #ph(body: [provisórios]).],
)
#tbl("am", [Pico da manhã])
#tbl("pm", [Pico da tarde])

#figure(image("figures/m4_trafego.png", width: 100%), caption: [Atraso, velocidade média e atraso dos ônibus por cenário (barras de erro: IC 95%).]) <fig-traf>
#figure(image("figures/m4_emis.png", width: 100%), caption: [CO₂ e NOx na janela e CO₂ por veículo-km (barras de erro: IC 95%).]) <fig-emis4>
#figure(image("figures/m4_ruido.png", width: 100%), caption: [Leq médio estimado nos pontos monitorados.]) <fig-ruido4>

== Como ler

- *Estatística.* Foram feitos #EX.n_tests testes _t_ pareados com 5 pares cada, sem correção para múltiplas comparações e sem checagem de normalidade (com cinco pares, o teste de Wilcoxon não passa de _p_ = 0,0625); os valores _p_ são descritivos, não confirmatórios, e as conclusões se apoiam nos casos em que vários indicadores concordam. O valor _p_ da tabela é de um teste _t_ pareado com 5 pares; ele ignora que a incerteza dominante não é a semente de simulação e sim a demanda sorteada, os semáforos inferidos e as rotas de ônibus aleatórias. Um _p_ baixo diz que a diferença é estável ao trocar a semente, não que se repetirá na cidade.
- *Emissões.* Os percentuais seguem os de velocidade e de viagens concluídas, porque as classes HBEFA3 respondem à cinemática: o To-Be emite mais CO₂ na janela porque a rede fica mais lenta e retém veículos que continuam emitindo. A tabela traz CO₂ por veículo-km além do total para separar _fluxo_ de _intensidade_.
- *Magnitude das emissões.* Os valores absolutos de CO₂ (cerca de 950 a 1.400 g/km) e de CO (cerca de 30 g/km) são várias vezes os típicos da literatura para frotas leves, porque o modelo está engarrafado, as motos usam a classe de carros e os fatores são europeus. Servem para comparar cenários, não para citar. O fator $k$ de extensão à janela multiplica uma simulação que já inclui 30 min de escoamento.
- *Atraso dos concluídos e ônibus.* Os cenários concluem números diferentes de viagens (2.500 a 2.900), então o atraso médio dos concluídos tem viés de sobrevivência; a velocidade espacial e os concluídos são mais confiáveis.
- *Ruído.* O CoRTN, com piso de velocidade de 20 km/h, só capta a mudança de volume nas aproximações, não o fim do para-e-anda. As diferenças de Leq são pequenas por construção e não sustentam conclusão sobre mitigação acústica; isso exige modelo de fonte que cubra baixas velocidades e medição em campo (M1).
- *Poeira.* A ressuspensão (AP-42, parâmetros assumidos) é proporcional aos veículos-km: MP2,5 de #fix(EX.dust.am.asis.pm25_kg, 2) kg (As-Is) contra #fix(EX.dust.am.tobe.pm25_kg, 2) kg (To-Be) na manhã, e #fix(EX.dust.pm.asis.pm25_kg, 2) contra #fix(EX.dust.pm.tobe.pm25_kg, 2) kg na tarde. A queda de poeira nas intervenções é *artefato de congestionamento*: com menos veículos-km percorridos (a rede anda menos), há menos ressuspensão; não é benefício.
- *Fila e acústica não calculadas.* O comprimento de fila exigido pelo manual não foi extraído (exigiria saída `queue-output` ou detectores por aresta) e *não há simulação acústica*: o ruído é o CoRTN em 2 pontos (P01 e P04) com piso de 20 km/h, enquanto a rede anda a 8 a 11 km/h, de modo que ele só reflete a vazão; o "Leq médio" é a média aritmética de dois níveis em dB, e a vazão horária usa o `entered` de 5400 s, aproximação grosseira. O `harmonoise` do SUMO é a melhora natural.

= Modos ativos

A comparação usa redes que incluem pedestres, ciclovias e as faixas exclusivas de bicicleta propostas, com demanda de pedestres e ciclistas #ph(body: [provisória]) e três réplicas. Três cenários separam os efeitos:
*As-Is ativo* (pedestres e ciclovias, _actuated_ padrão), *só faixas de bicicleta* (rede com as faixas, _actuated_ padrão) e *To-Be ativo* (faixas mais prioridade ao ônibus).

#figure(
  table(columns: (1fr, auto, auto, auto), align: (left, right, right, right),
    [Indicador], [As-Is ativo], [Só faixas de bicicleta], [To-Be ativo],
    [Atraso médio dos veículos motorizados (s)], [#pm(AC.asis_act.car_delay_s, d: 0)], [#pm(AC.bike_only.car_delay_s, d: 0)], [#pm(AC.tobe_act.car_delay_s, d: 0)],
    [Pedestres concluídos], [#pm(AC.asis_act.persons, d: 0)], [#pm(AC.bike_only.persons, d: 0)], [#pm(AC.tobe_act.persons, d: 0)],
    [Perda de tempo média dos pedestres (s)], [#pm(AC.asis_act.ped_timeloss_s, d: 1)], [#pm(AC.bike_only.ped_timeloss_s, d: 1)], [#pm(AC.tobe_act.ped_timeloss_s, d: 1)],
    [Ciclistas concluídos], [#pm(AC.asis_act.bikes, d: 0)], [#pm(AC.bike_only.bikes, d: 0)], [#pm(AC.tobe_act.bikes, d: 0)],
    [Velocidade média dos ciclistas (km/h)], [#pm(AC.asis_act.bike_speed_kmh)], [#pm(AC.bike_only.bike_speed_kmh)], [#pm(AC.tobe_act.bike_speed_kmh)],
    [Perda de tempo média dos ciclistas (s)], [#pm(AC.asis_act.bike_delay_s, d: 0)], [#pm(AC.bike_only.bike_delay_s, d: 0)], [#pm(AC.tobe_act.bike_delay_s, d: 0)]),
  caption: [Modos ativos (manhã, 3 réplicas, média ± IC 95%). Demanda #ph(body: [provisória]). Rotas inválidas em uma variante são descartadas pelo SUMO, então o número de ciclistas e carros concluídos pode diferir.],
)

*Resultado:* não há efeito mensurável das faixas de bicicleta nem do controle sobre pedestres e ciclistas (médias praticamente iguais), e há indício de custo para os veículos motorizados. Isso era esperado: as rotas dos ciclistas são pré-calculadas e não desviam para as novas faixas, os pedestres usam calçadas e travessias do modelo padrão, e o controlador não vê pedestres. O atraso dos veículos motorizados é maior nas redes com faixas (cerca de 655 e 685 s contra 577 s): o teste pareado (n = 3, sem correção) dá +#fix(EX.active_paired.bike_only_vs_asis_car_delay.diff, 0) s para só faixas (_p_ = #fix(EX.active_paired.bike_only_vs_asis_car_delay.p, 3)), compatível com o custo das faixas para os veículos, mas a rede com faixas tem mais semáforos inferidos (256 contra 233), o que confunde o efeito. O As-Is ativo é uma rede diferente da do As-Is principal (233 contra 223 semáforos; atraso de 577 s contra 471 s), então os dois não são comparáveis entre si. O experimento *não permite concluir* sobre faixas de bicicleta; só mostra que o modelo roda e quais mudanças de modelagem são necessárias (escolha de rota de ciclistas, pedestres no controle, calçadas ao longo das vias).

= Viabilidade para Curitiba e limites

#table(columns: (auto, 1fr), [Aspecto], [Avaliação],
  [Prioridade ao ônibus], [Tecnicamente simples (detecção por GPS/transponder da URBS e comando de fase), mas *não melhorou* a rede nesta implementação e com rotas de ônibus aleatórias; só vale reavaliar com as linhas reais.],
  [Controlador PI], [Piorou a rede e não se justifica implantar. Exigiria sintonia com dados reais, semáforos reais, coordenação por eixo (onda verde, não implementada) e modelagem de pedestres.],
  [Faixas de bicicleta], [Proposta de desenho sem estudo de largura de via, estacionamento, desapropriação, custo e segurança; é hipótese a ser avaliada, não recomendação.],
  [Comunicação e sensoriamento], [Latência e tráfego de mensagens são desprezíveis frente ao período de 5 s, em localhost. Falta teste em rede real e custo de instalação e manutenção.],
  [Evidência], [Todas as entradas quantitativas são provisórias. O resultado vale como teste de método e não como estimativa de benefício.],
)

*Para que o relatório final tenha valor de engenharia faltam:* (1) contagens de veículos, pedestres e ciclistas, e medições de Leq; (2) fases e localização dos semáforos; (3) itinerários e telemetria reais da URBS; (4) calibração com tempos de viagem; (5) fatores de emissão e frota locais; (6) revisão do polígono de estudo.

= Perguntas esperadas da banca

#table(columns: (1fr, 2fr), [Pergunta], [Resposta honesta],
  [As intervenções reduziram as emissões?], [Não neste modelo: as duas aumentaram o CO₂ e reduziram a velocidade média. Não afirmamos benefício.],
  [O modelo está calibrado?], [O procedimento GEH foi executado, mas o critério de 85% não foi atingido (manhã 76,5%, tarde 82,4%), sobre contagens sorteadas e só dois pontos com aproximação motorizada.],
  [Por que não há dados de campo?], [Não houve coleta nesta etapa; todos os insumos quantitativos estão marcados como provisórios e são substituíveis por `make calibrate`.],
  [Por que o PI foi pior que o _actuated_?], [Provável combinação de: perda da lógica por detectores ao converter para programas fixos, sensores idealizados, erro de fila sem normalização e rede saturada. Não provamos qual fator domina.],
  [E a onda verde?], [Não foi implementada; é a principal lacuna de controle frente ao manual.],
  [Qual é a contribuição?], [Um pipeline aberto e reproduzível, um teste de método com réplicas, ablação e relato do resultado negativo, e uma lista objetiva do que falta medir.],
)

#bibliography("refs.bib", style: "associacao-brasileira-de-normas-tecnicas", title: [Referências])
