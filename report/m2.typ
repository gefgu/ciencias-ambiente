#import "lib.typ": *

#let B = json("figures/m2_baseline.json")
#let CA = json("figures/m2_calibration_am.json")
#let CP = json("figures/m2_calibration_pm.json")
#let NS = json("figures/m2_net_stats.json")
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
#let N = (str(NS.edges), str(NS.junctions), str(NS.tls))

#show: report.with(
  title: "Cenário As-Is calibrado e memorial de cálculo ambiental",
  subtitle: "Simulação microscópica no SUMO, calibração GEH e linha de base de emissões e ruído",
  course: "Ciências do Ambiente", program: "Projeto 1", milestone: "Marco 2 · Desenhar",
  authors: ((name: "Gustavo Henrique Bruno dos Santos", role: "Computação"), (name: "[integrante]", role: "Elétrica e Automação"), (name: "[integrante]", role: "Mecânica")),
  date: "15 de novembro de 2026",
  abstract: [
    Constrói o modelo microscópico As-Is no SUMO a partir da malha aberta (Overture e IPPUC), calibra a demanda pela estatística GEH e calcula emissões, poeira e ruído nas janelas de pico.
    O procedimento é completo e reproduzível, mas as contagens que o alimentam são #ph(body: [provisórias]) e o modelo opera em congestionamento severo. Os números deste documento descrevem
    a *rede simulada do núcleo central* com demanda sorteada: são um teste do método, não um inventário do Quadrilátero.
  ],
)

= Do M1 ao M2

O M1 foi revisado criticamente antes deste marco e o M2 também. Mudanças do M1: pontos de medição restritos a cruzamentos reais (cinco); classe viária por moda; limites e alcance do CoRTN revistos;
resultados provisórios deixaram de ser apresentados como achados. Mudanças do M2, resposta à segunda revisão: contagens atribuídas só às aproximações que _chegam_ ao cruzamento; emissões e distância percorrida
medidas no mesmo período e para todos os veículos; fator de extensão à janela alinhado às horas que definem o volume; parâmetros do AP-42 revistos; linha de base de ruído incluída; arquivos do cenário portáveis.
Duas decisões de escopo seguem em aberto: o polígono de estudo e a via Mário Tourinho. A simulação usa um *núcleo central* de cerca de 16 km² (bounding box de 4,0 × 3,9 km), que contém P01 a P04; P05 fica fora. Só P01 e P04 têm aproximações motorizadas (ver limitações).

= Modelo As-Is

== Rede viária

A malha vem do pipeline do M1 (Overture Maps, com a geometria real das vias) e é convertida em XML plano do SUMO @lopez2018sumo por `src/cps/sumo_net.py`, depois processada pelo `netconvert`.
Classes, faixas e velocidade: tronco (3 faixas, 60 km/h), primária e secundária (2, 50 km/h), terciária (1, 40 km/h), residencial e demais (1, 30 km/h ou menos).
Resultado: #N.at(0) arestas, #N.at(1) nós e *#N.at(2) semáforos*.

#aviso[
  Não há dados públicos de localização e fases dos semáforos. O `netconvert` os infere por geometria (`--tls.guess`) e a quantidade depende muito do limiar: 738 com o padrão, 223 com 110, 5 com 150.
  Adotamos 110 por dar densidade plausível para um centro urbano, mas é *premissa*, e todos os semáforos usam o programa _actuated_ padrão. O levantamento de campo é a principal pendência estrutural.
]

== Demanda e frota

Não há matriz origem-destino. A demanda vem de (i) rotas candidatas (viagens aleatórias entre arestas periféricas, mais viagens forçadas a passar por cada aresta monitorada) e (ii) a ferramenta `routeSampler`,
que escolhe o subconjunto de rotas que melhor reproduz as contagens. Os veículos são sorteados na frota de classes HBEFA3 embutidas no SUMO: carro a gasolina/flex, carro a diesel, "moto", ônibus e caminhão.
A build usada não tem classe de motocicleta; as motos usam a de carro a gasolina, o que superestima o CO₂ e provavelmente subestima CO e HC. *Os ônibus seguem rotas aleatórias*, sem as linhas da URBS, portanto
nenhum resultado específico de ônibus tem significado antes de carregar os itinerários reais. Bicicletas e pedestres entram no M3.

= Calibração GEH

A estatística GEH compara o volume horário simulado $M$ ao observado $C$ em cada aresta monitorada:

$ "GEH" = sqrt((2 (M - C)^2) / (M + C)) $

O critério do manual é *GEH < 5 em pelo menos 85%* das vias monitoradas @fhwa2004toolbox. As aproximações monitoradas são as arestas que chegam a cada cruzamento (fim da aresta a até 35 m do ponto).
O volume simulado é o `entered` do `edgeData`. A cada rodada, o alvo do `routeSampler` é corrigido pela raiz do erro relativo e limitado entre 0,7 e 1,5 vez o observado, o que evita a explosão de demanda vista nas primeiras tentativas.

#figure(
  table(columns: (auto, auto, auto, auto, auto, auto), align: (left, right, right, right, right, right),
    [Janela], [Aprox.], [GEH < 5], [GEH < 5, ponderado por volume], [Simulado ÷ observado], [Critério ≥ 85%],
    [Manhã], [#CA.n_links], [#f1(CA.final_pct_geh_lt5)%], [#f1(CA.weighted_pct_geh_lt5)%], [#f2(CA.sim_over_obs_total)], [#if CA.ok [atendido] else [não atendido]],
    [Tarde], [#CP.n_links], [#f1(CP.final_pct_geh_lt5)%], [#f1(CP.weighted_pct_geh_lt5)%], [#f2(CP.sim_over_obs_total)], [#if CP.ok [atendido] else [não atendido]]),
  caption: [Calibração GEH sobre contagens observadas #ph(body: [provisórias]), em #CA.n_points pontos.],
)

#figure(image("figures/m2_geh.png", width: 100%), caption: [GEH por aproximação (barras vermelhas: GEH ≥ 5). A linha tracejada marca o limiar 5.]) <fig-geh>
#figure(image("figures/m2_scatter.png", width: 100%), caption: [Volume simulado × observado provisório por aproximação (reta: igualdade).]) <fig-scatter>

*Como interpretar.* Este resultado é *fraco como evidência* e não valida o modelo, por quatro razões. (1) O `routeSampler` é ajustado às mesmas contagens usadas depois no GEH, sem aproximações de validação nem
checagem de tempos de viagem. (2) Em fluxos baixos (100–150 veíc/h) o GEH < 5 tolera erros relativos de cerca de ±50%, então o percentual simples superestima o ajuste; por isso a tabela traz também o percentual ponderado por volume
e a razão entre os totais simulado e observado, que mostram onde o modelo fica aquém. (3) A escolha da melhor rodada seleciona o máximo sobre poucas tentativas, e há uma única semente nesta etapa (as réplicas entram no M4). (4) As contagens são sorteadas.
O que o exercício valida é o _encadeamento_ rede, demanda, otimização e medição. Com as contagens reais, o ciclo se repete trocando `data/placeholders/field_counts.csv` e executando `make calibrate`.
A calibração deve incluir ainda tempos de viagem e filas observados, não só volumes.

= Memorial de cálculo ambiental

== Método

*Contabilidade.* O `edgeData` cobre a simulação inteira (0–5400 s: 1 h de demanda mais 30 min para escoar) e traz, por aresta, a emissão acumulada e a distância percorrida de *todos* os veículos, inclusive os que ainda estão na rede ao final.
Emissões, veículos-km e velocidade média usam, portanto, o mesmo período e a mesma população. Os atrasos vêm só dos veículos concluídos, o que os subestima, e por isso a @tab-base traz também inseridos, concluídos e retidos.

*Escapamento.* O SUMO calcula a cada passo a emissão instantânea de cada veículo com as classes HBEFA3 @notter2019hbefa (função de velocidade e aceleração), de modo que o para-e-anda entra pela cinemática simulada.
A hora simulada é estendida à janela de pico por

$ k_"janela" = (sum_h f_h dot w_h) / macron(f)_"sim" $

em que $f_h$ é a fração do volume diário na hora $h$ (perfil horário #ph(body: [provisório])), $w_h$ o peso da hora na janela (0,5 para 6h–7h, que cobre 06:30–07:00) e $macron(f)_"sim"$ a média das frações das horas
(7h–8h na manhã; 17h–18h na tarde) que definem o volume simulado.

*Ressuspensão (poeira).* O método AP-42 da US EPA (cap. 13.2.1, vias pavimentadas) dá $E = k dot s L^(0,91) dot W^(1,02) dot (1 - P / (4 N))$ em g/VMT, com $k_("MP2,5") = 0,15$ e $k_("MP10") = 0,62$,
$W$ em toneladas curtas, convertido para g/km. Premissas: $s L = 0,03$ g/m² (valor tabelado para ADT > 10.000), $W$ = #f2(B.am.fleet_weight_short_tons) t, derivado da frota simulada com massas médias por classe,
e fator de chuva com $P = 150$ dias com precipitação ≥ 0,254 mm em $N = 365$, a confirmar com dados do INMET. Resultado: #f2(B.am.resuspension_g_per_km.PM25 * 1000) mg/km (MP2,5) e #f2(B.am.resuspension_g_per_km.PM10 * 1000) mg/km (MP10).

*Pegada de carbono.* É a massa de CO₂ de escapamento por janela e por veículo-km, a medida comparável entre cenários no M4. Não há abatimento do CO₂ biogênico do etanol, e não se computam CH₄ e N₂O (CO₂e):
os fatores HBEFA3 são europeus e o combustível brasileiro tem mistura de etanol, então o valor absoluto é aproximado.

*Ruído.* Estimado com o CoRTN @cortn1988 a 10 m do bordo, a partir de fluxo e velocidade simulados nas aproximações de cada ponto, somando as arestas por energia. A velocidade entra com piso de 20 km/h, que é o limite de validade do método;
logo, a estimativa não capta o ganho acústico do para-e-anda e tende a subestimar benefícios de suavização.

== Resultados da linha de base

#figure(
  table(columns: (1fr, auto, auto), align: (left, right, right),
    [Indicador], [Manhã #B.am.label], [Tarde #B.pm.label],
    [Veículos carregados / inseridos / concluídos], [#f0(B.am.loaded) / #f0(B.am.inserted) / #f0(B.am.finished)], [#f0(B.pm.loaded) / #f0(B.pm.inserted) / #f0(B.pm.finished)],
    [Retidos na rede ao fim (em movimento + aguardando entrada)], [#f0(B.am.running_at_end + B.am.waiting_to_enter_at_end)], [#f0(B.pm.running_at_end + B.pm.waiting_to_enter_at_end)],
    [Atraso médio para entrar na rede (s)], [#f0(B.am.depart_delay_s)], [#f0(B.pm.depart_delay_s)],
    [Atraso médio dos concluídos (s, subestimado)], [#f0(B.am.mean_delay_finished_s)], [#f0(B.pm.mean_delay_finished_s)],
    [Velocidade média espacial (km/h)], [#f1(B.am.mean_speed_kmh)], [#f1(B.pm.mean_speed_kmh)],
    [_Teleports_ por congestionamento], [#B.am.teleports], [#B.pm.teleports],
    [Veículos-km (0–5400 s)], [#f0(B.am.veh_km)], [#f0(B.pm.veh_km)],
    [CO₂ na janela (t)], [#f1(B.am.window_kg.CO2 / 1000)], [#f1(B.pm.window_kg.CO2 / 1000)],
    [CO na janela (kg)], [#f0(B.am.window_kg.CO)], [#f0(B.pm.window_kg.CO)],
    [NOx na janela (kg)], [#f1(B.am.window_kg.NOx)], [#f1(B.pm.window_kg.NOx)],
    [MP escapamento (kg)], [#f2(B.am.window_kg.PMx)], [#f2(B.pm.window_kg.PMx)],
    [MP2,5 ressuspensão (kg)], [#f2(B.am.resuspension_window_kg.PM25)], [#f2(B.pm.resuspension_window_kg.PM25)],
    [MP10 ressuspensão (kg)], [#f2(B.am.resuspension_window_kg.PM10)], [#f2(B.pm.resuspension_window_kg.PM10)],
    [CO₂ por veículo-km (g/km)], [#f0(B.am.g_per_vkm.CO2)], [#f0(B.pm.g_per_vkm.CO2)]),
  caption: [Linha de base As-Is (rede simulada do núcleo, demanda #ph(body: [provisória])).],
) <tab-base>

#figure(image("figures/m2_emis.png", width: 100%), caption: [Emissões de escapamento do As-Is por janela (HBEFA3 no SUMO, perfil horário provisório).]) <fig-emis2>

#figure(
  table(columns: (auto, auto, auto, auto), align: (left, right, right, right),
    [Ponto], [Manhã Leq (dB)], [Tarde Leq (dB)], [Limite diurno (dB)],
    ..B.am.noise_leq_dba.keys().map(k => (k, f1(B.am.noise_leq_dba.at(k)), f1(B.pm.noise_leq_dba.at(k)), [60])).flatten()),
  caption: [Leq estimado (CoRTN a 10 m, velocidade com piso de 20 km/h) a partir do fluxo simulado. Estimativa, não medição.],
) <tab-ruido>

== Limitações que afetam a leitura

- *Congestionamento severo.* Só uma parte dos veículos carregados conclui a viagem na janela, há _teleports_ e atraso de entrada de minutos (@tab-base). O CO por quilômetro é alto por refletir marcha lenta e o mapeamento de motos para carro. Os valores absolutos descrevem uma rede travada e não devem ser citados como inventário.
- *Fronteira.* A demanda existe só para viagens que passam pelas aproximações monitoradas dentro do núcleo. Os totais são da rede simulada, não do Quadrilátero inteiro.
- *Pontos no Calçadão e cobertura da calibração.* P02 e P03 ficam sobre o Calçadão da XV, exclusivo de pedestres e ônibus em parte do trecho, e não têm aproximação motorizada que chegue ao ponto; por isso a calibração e o ruído cobrem só P01 e P04 (#CA.n_points pontos). Isso é pouca base para um critério de 85%: com contagens reais convém ampliar os pontos para cruzamentos com tráfego motorizado.
- *Frota local.* O perfil de Curitiba (flex, diesel comercial, híbridos e elétricos) está parametrizado só na divisão carro/moto/ônibus/caminhão; a dos ônibus não vem da URBS.

= Reprodutibilidade e pendências

Os passos rodam por `make net`, `make calibrate` e `make baseline`; as saídas (`data/processed/m2_*`) alimentam este relatório. O cenário (`sim/net.net.xml`, `sim/vtypes.add.xml`, `sim/routes_asis_*.rou.xml`, `sim/asis_*.sumocfg`) usa caminhos relativos e roda com `sumo -c sim/asis_am.sumocfg`.
As saídas ficam em `sim/work/`, ignorada pelo Git.

#table(columns: (auto, 1fr), [Pendência], [Ação],
  [Contagens reais], [Contagem manual de VPD em mais cruzamentos motorizados (hoje só P01 e P04) e reexecução de `make calibrate`; incluir tempos de viagem],
  [Semáforos], [Levantar fases e localização reais; substituir o `--tls.guess`],
  [Linhas de ônibus], [Carregar itinerários da URBS (chave de acesso) no lugar das rotas aleatórias],
  [Polígono de estudo], [Decidir entre casco convexo e núcleo; confirmar a via Mário Tourinho],
  [Motocicletas], [Obter classe HBEFA4 de moto ou calcular as emissões delas fora do SUMO],
  [Fatores brasileiros], [Fatores de emissão do combustível nacional, CO₂e e CO₂ biogênico],
)

#bibliography("refs.bib", style: "associacao-brasileira-de-normas-tecnicas", title: [Referências])
