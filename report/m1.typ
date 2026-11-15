#import "lib.typ": *

#let S = json("figures/stats.json")
#let P = csv("figures/pontos.csv", row-type: dictionary)
#let fix(x, d) = { if d == 0 { return str(int(calc.round(float(x)))) }; let s = str(calc.round(float(x), digits: d)); if not s.contains(".") { s = s + "." + "0" * d } else { let n = s.split(".").at(1).len(); s = s + "0" * (d - n) }; s.replace(".", ",") }
#let f1(x) = fix(x, 1)
#let f0(x) = {
  let s = str(calc.round(float(x)))
  s.replace(regex("\.0$"), "").clusters().rev().chunks(3).map(c => c.join()).join(".").clusters().rev().join()
}

#show: report.with(
  title: "Diagnóstico ambiental e caracterização do problema",
  subtitle: "Mobilidade urbana, sustentabilidade e sistemas ciber-físicos no Quadrilátero Central de Curitiba",
  course: "Ciências do Ambiente",
  program: "Projeto 1",
  milestone: "Marco 1 · Conceber",
  authors: (
    (name: "Gustavo Henrique Bruno dos Santos", role: "Computação"),
    (name: "[integrante]", role: "Elétrica e Automação"),
    (name: "[integrante]", role: "Mecânica"),
  ),
  date: "15 de novembro de 2026",
  abstract: [
    Este relatório abre o ciclo CDIO do projeto. Delimita o quadrilátero de estudo, reúne a base geográfica aberta (Overture Maps e IPPUC),
    define os pontos de medição de tráfego e ruído, estabelece uma linha de base preliminar de emissões e propõe a arquitetura lógica de dados
    compartilhados entre as três especialidades. Os dados de campo ainda não foram coletados: contagens, níveis sonoros, telemetria de ônibus
    e fatores de emissão aparecem como valores provisórios, sempre sinalizados com o selo #ph() e prontos para substituição.
  ],
)

= Introdução e escopo

O quadrilátero central de Curitiba concentra um dos maiores gargalos de tráfego da cidade nos horários de pico (06:30–09:00 e 17:00–19:00).
O projeto pede que o consórcio diagnostique o cenário atual (_As-Is_), projete sensoriamento e controle semafórico adaptativo e valide a
solução em simulação microscópica (_To-Be_), medindo a redução de emissões e de ruído. O projeto segue a metodologia CDIO @crawley2014 e usa o SUMO @lopez2018sumo. O Marco 1 (_Conceber_) entrega o
diagnóstico, o mapa viário preliminar e a arquitetura de dados.

#callout(title: "Como ler este documento")[
  Cada número é um de dois tipos. *Dado real*: geometria viária, hierarquia, ciclovias, terminais e o contrato de dados.
  *Dado provisório* #ph(): contagens de veículos, Leq, perfil horário, telemetria de ônibus e fatores de emissão.
  O painel interativo (`app/dashboard.py`) usa os mesmos arquivos e a mesma paleta; basta editar `data/placeholders/*.csv` e regenerar.
]

== Área de estudo

O manual delimita o quadrilátero por seis vias: Av. Pres. Kennedy, Calçadão da Rua XV de Novembro, Av. Mal. Floriano Peixoto,
Alameda Dr. Muricy / Rua Martim Afonso, Rua Mariano Torres e a via Mário Tourinho. Adotamos a leitura literal: o *casco convexo* das geometrias dessas vias.
O resultado cobre #f1(S.area_km2) km², área maior que o centro histórico, porque a Rua Gen. Mário Tourinho (única "Tourinho" na base) fica bem a oeste das demais.

#aviso[
  A via "Av. Mário Tourinho" do manual foi associada à *Rua General Mário Tourinho* da base Overture. Confirmar com a equipe. Se o escopo for reduzido a um núcleo
  central, só muda a função `study_polygon` em `src/m1/geo.py`; o restante do pipeline se adapta.
]

= Diagnóstico do cenário As-Is

== Base geográfica

#table(columns: (4.2cm, 1fr, 3.6cm), align: (left, left, left),
  [Fonte], [Conteúdo usado], [Itens],
  [Overture Maps @overture2026], [Segmentos viários e conectores (release 2026-10-21.0), base da malha para o SUMO], [#f0(S.n_segments)],
  [IPPUC @ippuc2026geo], [Sistema viário classificado (Lei 15.511/2019 @curitiba2019lei15511), ciclovias, ciclorrotas, Calçadão, terminais e bairros], [#S.n_terminais terminais, #f0(S.n_ciclorrotas) ciclorrotas],
  [IPPUC], [Ciclovias oficiais no polígono], [#f1(S.ciclo_km) km],
)

A Overture Maps substitui o Overpass/OpenStreetMap como fonte da malha: a base é distribuída em GeoParquet, com consulta por _bounding box_, e traz o grafo
de conectores já pronto. Os dados do IPPUC (SIRGAS 2000 / UTM 22S) fornecem a hierarquia viária oficial, que a Overture não tem.
O mapa preliminar está na @fig-mapa.

#figure(image("figures/mapa.png", width: 100%),
  caption: [Mapa viário preliminar: sistema viário IPPUC por hierarquia, ciclovias, Calçadão, terminais e pontos de medição candidatos. Fonte: IPPUC e Overture Maps.]) <fig-mapa>

== Pontos de medição

Os pontos candidatos são os cruzamentos reais entre as vias do contorno e do núcleo (distância ≤ 150 m entre as geometrias), calculados em
`src/m1/traffic.py`. Cinco pontos resultaram (@tab-pontos); P01–P04 ficam no eixo central e P05 na ponta oeste do casco. As travessias com o Calçadão da XV (P02–P04) são exclusivas de pedestres e ônibus em parte do trecho, então o fluxo motorizado ali vem da via transversal. O cruzamento Floriano × Muricy foi descartado por não haver encontro real das geometrias.

#figure(
  table(columns: (auto, 1fr, auto, auto, auto), align: (left, left, right, right, right),
    [ID], [Cruzamento], [VPD #ph()], [pico manhã (v/h) #ph()], [pico tarde (v/h) #ph()],
    ..P.map(r => (r.point_id, r.name, f0(r.vpd_total), f0(r.vph_manha), f0(r.vph_tarde))).flatten()),
  caption: [Pontos de medição candidatos e volumes provisórios.],
) <tab-pontos>

== Tráfego

As contagens manuais de VPD ainda serão feitas. Os valores atuais seguem uma ordem de grandeza por classe viária e um perfil horário bimodal genérico
(@fig-trafego), com a divisão modal em torno de #f0(S.mix.carros * 100)% carros, #f0(S.mix.motos * 100)% motos, #f0(S.mix.onibus * 100)% ônibus,
#f0(S.mix.caminhoes * 100)% caminhões e #f0(S.mix.bicicletas * 100)% bicicletas #ph(). O que muda com os dados reais é o conteúdo, não o formato.

#figure(image("figures/trafego.png", width: 100%), caption: [Volume diário por ponto e modal (esq.) e perfil horário com as janelas de pico sombreadas (dir.). Dados provisórios.]) <fig-trafego>

*Telemetria de ônibus.* A API de posição de veículos da URBS exige código de acesso, que a equipe deve solicitar. Enquanto isso, o pipeline gera traços GPS sintéticos
sobre a geometria real de três corredores (Floriano, Mariano Torres e Muricy), aplica o mapeador de mapas (_map-matching_ HMM/Viterbi) da biblioteca
`fastmob` @santos2026fastkit e calcula velocidade média e fração do tempo parado. No pico da manhã a velocidade média é #f1(S.bus.at("Pico manhã (06:30–09:00)").vel_media_kmh) km/h
(#f1(S.bus.at("Pico manhã (06:30–09:00)").pct_parado)% do tempo parado); à tarde, #f1(S.bus.at("Pico tarde (17:00–19:00)").vel_media_kmh) km/h
(#f1(S.bus.at("Pico tarde (17:00–19:00)").pct_parado)%); no entrepico, #f1(S.bus.at("Entrepico (10:00–16:00)").vel_media_kmh) km/h #ph().
Esses valores são consequência direta das premissas do gerador sintético (velocidade de cruzeiro e probabilidade de parada por janela), de modo que não são resultado; servem só para validar o pipeline (@fig-onibus).

#figure(image("figures/onibus.png", width: 100%), caption: [Indicadores de para-e-anda dos ônibus por janela. Telemetria sintética processada com `fastmob`.]) <fig-onibus>

= Diagnóstico ambiental

== Ruído

A avaliação segue a ABNT NBR 10151:2019 @abnt2019noise. Para área mista com atividades comerciais e administrativas, o limite diurno é *60 dB(A)*. O protocolo de campo mede o
nível equivalente ($L_(upright("eq"))$) e o ruído residual (sem o tráfego pesado, quando possível) nos pontos P01 a P05, com medidor de classe 1 ou 2 (IEC 61672) e calibrador acústico; aplicativos de celular servem apenas como verificação preliminar e não atendem à norma. Os limites da norma aplicam-se ao nível corrigido (RLAeq, com correções tonais e impulsivas), não ao $L_(upright("eq"))$ bruto; a fonte avaliada é o tráfego, e o residual é o nível medido sem ela (na prática, de madrugada ou em ponto de referência semelhante). Verificar também a legislação municipal de ruído, que pode fixar limites por zona.

Como estimativa teórica, usamos o modelo CoRTN @cortn1988 em sua forma básica:

$ L_(10,1"h") = 42,2 + 10 log_(10) q + 33 log_(10)(v + 40 + 500/v) + 10 log_(10)(1 + (5p)/v) - 68,8 - 10 log_(10) (d'/13,5) \
 d' = sqrt((d+3,5)^2 + h^2) $

com $q$ em veículos/h, $v$ em km/h, $p$ a porcentagem de veículos pesados, $d$ a distância ao *bordo* mais próximo da pista e $h$ a altura do receptor em relação à fonte (0,7 m para microfone a 1,2 m). Adotamos $L_(upright("eq")) approx L_(10) - 3$ dB, regra prática do próprio método.
O modelo pressupõe tráfego fluindo e seu termo de velocidade não é validado abaixo de cerca de 20 km/h, faixa em que operam o para-e-anda e os semáforos do centro; omite também rampa, superfície e reflexão. Serve, portanto, apenas como comparação de primeira ordem, e o M2 substitui essa estimativa por simulação.
Com os volumes provisórios e 18 km/h, a estimativa a 10 m do bordo da pista fica em torno de 68–70 dB(A) (@fig-ruido). Os valores de Leq da figura são *provisórios por construção* (sorteados entre 68 e 77 dB) e não constituem resultado: a comparação com o limite de 60 dB só terá valor depois da medição em campo.
A redução esperada por suavizar o fluxo tem duas partes: o termo de volume ($10 log_(10)(q_2/q_1)$, cerca de 1 dB para −20% de veículos) e a diminuição do para-e-anda, que o M4 quantificará na simulação.

#figure(image("figures/ruido.png", width: 100%), caption: [$L_(upright("eq"))$ e ruído residual provisórios, estimativa CoRTN e limite da NBR 10151 por ponto.]) <fig-ruido>

== Emissões (linha de base preliminar)

A taxa de emissão por quilômetro de via é $E = q dot k(v) dot sum_c s_c f_c$, com $s_c$ a participação de cada classe, $f_c$ o fator em g/km a 50 km/h e $k(v)$ um
fator de correção em U que penaliza baixas velocidades. Os fatores de #ph(body: [ordem de grandeza]) e a curva de correção em U não têm fonte própria e servem só para dimensionar o problema; o M2 os substitui por saídas do SUMO com as classes HBEFA @notter2019hbefa, com a
frota ajustada às estatísticas locais (flex, diesel comercial, híbridos e elétricos). A @fig-emis mostra a linha de base da manhã. Material particulado (_poeira_) tem ainda a parcela de ressuspensão da via, não coberta pelo escapamento; ela será estimada no M2 com o método para vias pavimentadas da US EPA (AP-42, cap. 13.2.1), e a pegada de carbono do período de pico será calculada no memorial do M2.

#figure(image("figures/emissoes.png", width: 100%), caption: [Taxa de emissão provisória no pico da manhã, por poluente e ponto (kg/h por km de via, 18 km/h).]) <fig-emis>

= Levantamento topológico e SIG

O fluxo previsto até o SUMO é: (1) baixar segmentos e conectores da Overture por _bounding box_; (2) recortar no polígono de estudo;
(3) enriquecer com a hierarquia IPPUC; (4) converter para a malha do SUMO com `netconvert`; (5) revisar semáforos, conversões e faixas no QGIS. No M1 foram cumpridos os passos 1 a 3. O grafo roteável usado na telemetria
(#f0(S.n_nodes_core) nós no núcleo central) é construído sobre os mesmos segmentos e serve para o _map-matching_.

#table(columns: (auto, 1fr), [Pendência], [Ação],
  [SUMO e QGIS não instalados], [Instalar para o M2 (`netconvert`, `sumo-gui`, `TraCI`)],
  [Semáforos e fases reais], [Levantar em campo ou solicitar ao órgão gestor; a Overture não traz fases],
  [Tamanho do casco], [Se o SUMO ficar pesado, adotar um núcleo reduzido (decisão de escopo)],
  [Telemetria URBS], [Obter código de acesso à API de posição de veículos],
)

= Arquitetura lógica de dados compartilhados

Os subsistemas trocam mensagens JSON conforme o contrato do manual: a simulação de hardware (Automação) publica ocupação e presença; o gerenciador semafórico
(Computação) e o modelo de emissões (Mecânica) consomem. A validação usa `pydantic` (`src/m1/contract.py`).

#figure(
  raw(lang: "json", block: true, "{\n  \"timestamp\": \"2026-08-21T17:30:00Z\",\n  \"intersection_id\": \"cruzamento_rua_xv_floriano\",\n  \"sensors\": [{\"sensor_id\": \"sensor_indutivo_lane_1\",\n               \"state\": \"occupied\", \"vehicle_speed_kmh\": 14.5}],\n  \"instantaneous_metrics\": {\"queue_length_meters\": 32.0,\n                            \"co2_grams_per_second\": 12.4}\n}"),
  caption: [Mensagem do contrato de integração (validada no código).], kind: raw, supplement: [Listagem])

Fluxo: *Sensores virtuais* (Wokwi/Node-RED) → *Mosquitto* → *Controlador TraCI/Python* → *SUMO* → *emissões e ruído* → *painel*. Árvore de tópicos MQTT preliminar (a fechar no M3):

```
cps/curitiba/{intersection_id}/sensors/{sensor_id}   # ocupação e velocidade
cps/curitiba/{intersection_id}/metrics               # fila, CO2 instantâneo
cps/curitiba/{intersection_id}/signal/cmd            # comando de fase
cps/curitiba/bus/{line}/priority                     # prioridade BRT
```

= Roadmap CDIO e processo

#table(columns: (auto, 1fr, auto), align: (left, left, left),
  [Marco], [Entregável e critério], [Status],
  [M1 Conceber], [Este relatório, mapa preliminar, arquitetura de dados], [em andamento],
  [M2 Desenhar], [As-Is calibrado: GEH < 5 em ≥ 85% das vias monitoradas @fhwa2004toolbox; memorial de emissões], [pendente],
  [M3 Implementar], [Controle TraCI/Python, tópicos MQTT, esquemáticos de sensoriamento], [pendente],
  [M4 Operar], [Comparação As-Is × To-Be, viabilidade, defesa], [pendente],
)

*Por especialidade no M1.* Computação: malha SIG, pipeline de dados e contrato JSON (feito). Automação: dimensionar e posicionar sensores nos P01–P05 (pendente).
Mecânica: protocolo de medição de Leq e frota local (pendente). Todo o código reside em um repositório único, conforme o manual.

*Próximos passos imediatos:* (1) campo: contagens de VPD e Leq nos cinco pontos; (2) solicitar chave da API da URBS; (3) confirmar o escopo do polígono e a via Mário Tourinho;
(4) instalar SUMO e gerar a primeira malha; (5) trocar os CSVs provisórios pelos medidos e regenerar o painel e este relatório.

#bibliography("refs.bib", style: "associacao-brasileira-de-normas-tecnicas", title: [Referências])
