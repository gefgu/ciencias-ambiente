#import "lib.typ": *

#let MQ = json("figures/m3_mqtt.json")
#let BOM = json("figures/m3_bom.json")
#let TU = csv("figures/m3_tuning.csv", row-type: dictionary)
#let AD = json("figures/m3_active_demand.json")
#let NA = json("figures/m2_net_active_stats.json")
#let NT = json("figures/m2_net_tobe_stats.json")
#let fix(x, d) = {
  if d == 0 { return str(int(calc.round(float(x)))) }
  let s = str(calc.round(float(x), digits: d))
  if not s.contains(".") { s = s + "." + "0" * d } else { let n = s.split(".").at(1).len(); s = s + "0" * (d - n) }
  s.replace(".", ",")
}
#let f1(x) = fix(x, 1)
#let f0(x) = {
  let s = str(calc.round(float(x), digits: 0)).replace(regex("\.0$"), "")
  s.clusters().rev().chunks(3).map(c => c.join()).join(".").clusters().rev().join()
}

#show: report.with(
  title: "Controle adaptativo, comunicação MQTT e sensoriamento",
  subtitle: "Algoritmo de controle semafórico com prioridade ao ônibus, malha ciber-física e modos ativos",
  course: "Ciências do Ambiente", program: "Projeto 1", milestone: "Marco 3 · Implementar",
  authors: ((name: "Gustavo Henrique Bruno dos Santos", role: "Computação"), (name: "[integrante]", role: "Elétrica e Automação"), (name: "[integrante]", role: "Mecânica")),
  date: "15 de novembro de 2026",
  abstract: [
    Implementa um controlador PI de fila entre fases com prioridade ao ônibus, a camada MQTT que o fecha com o SUMO, o projeto de sensoriamento e a modelagem de pedestres no Calçadão e de ciclistas.
    *Resultado central, e negativo:* o PI completo não supera a lógica _actuated_ padrão do SUMO. Uma sobreposição só de prioridade ao ônibus pareceu melhorar a rede na semente de sintonia, mas *esse ganho não se confirmou nas cinco réplicas do M4* (era artefato de semente; a regra refeita tem efeito nulo). O código funciona e é testado; o resultado de engenharia é que a intervenção não melhora esta rede.
    Uma onda verde adaptativa foi implementada na Rua Mariano Torres (a Av. Floriano não recebeu semáforos na inferência), e uma variante de prioridade ao ônibus condicional foi adicionada; ambas são avaliadas no M4. O plano de sensores cobre só os dois pontos monitorados, não os 223 semáforos simulados. Todo o conjunto opera sobre a demanda #ph(body: [provisória]) do M2.
  ],
)

= Do M2 ao M3

A revisão crítica do M2 gerou correções que alteram este marco: a execução TraCI agora para em 5400 s, como o As-Is (uma versão anterior corria até o último veículo sair e não era comparável); as saídas
levam o nome do cenário e da semente, de modo que um cenário não sobrescreve o outro; e a sintonia do controlador usa uma semente à parte das réplicas de avaliação.

= Controlador adaptativo

== Lógica

Cada semáforo é amostrado a cada 5 s. As entradas vêm de sensores virtuais: número de veículos parados nas faixas com verde ($q_V$) e com vermelho ($q_R$), ocupação média do laço nas faixas com verde e presença de ônibus a menos de 120 m da linha de retenção.
O erro de malha fechada é a diferença de pressão entre as fases, $e(k) = q_R(k) - q_V(k)$, e o controlador PI calcula

$ u(k) = K_p e(k) + K_i sum_(j<=k) e(j) T_s, quad T_s = 5 "s" $

com integral limitada (anti-windup). Se $u$ ultrapassa a banda morta $theta$ o verde é encerrado; se há demanda no verde, ele é estendido em 5 s; o verde fica entre 8 s (mínimo) e 50 s (máximo).
*Prioridade ao ônibus (BRT):* ônibus em aproximação com vermelho encerra o verde atual se a corrente em verde não está carregada; ônibus com verde recebe até 10 s adicionais por fase. A versão *condicional* (`bus_targeted`) só encerra o verde se a próxima fase verde serve a faixa do ônibus, ignora ônibus parados (em ponto) e faz no máximo um pedido por ônibus e por semáforo.
A lógica está em `src/cps/controllers.py`, sem dependência do SUMO, e tem testes unitários (`tests/test_controllers.py`) para tempo mínimo, amarelo, máximo, prioridade e anti-windup.

== Sintonia e resultado

#figure(image("figures/m3_loop.png", width: 100%), caption: [Malha fechada do controle semafórico: referência de pressão igual entre fases, controlador PI, atuador de fase (TraCI) e planta (SUMO), com sensores e MQTT na realimentação.]) <fig-loop>

Os parâmetros foram comparados em grade, em uma única semente de sintonia (distinta das réplicas do M4). *Base da tabela:* medições e regras da época da sintonia (velocidade sobre a simulação inteira de 5400 s e regra básica de prioridade), por isso os valores absolutos não coincidem com os do M4, que usa a hora de demanda e a regra refeita. A @tab-tune traz velocidade média espacial, veículos concluídos, atraso dos concluídos e _teleports_; a primeira linha por velocidade é a melhor.

#figure(
  table(columns: (1fr, auto, auto, auto, auto), align: (left, right, right, right, right),
    [Configuração], [Velocidade (km/h)], [Concluídos], [Atraso (s)], [_Teleports_],
    ..TU.map(r => (r.desc, f1(r.speed_kmh), f0(r.finished), f0(r.delay_finished_s), r.teleports)).flatten()),
  caption: [Sintonia (manhã, semente de sintonia, uma réplica por configuração). "As-Is" é o programa _actuated_ do `netconvert`, o mesmo do M2.],
) <tab-tune>

*O que a tabela mostra.* (1) Substituir os programas _actuated_ por programas fixos, sem controle algum ("controle nulo"), já derruba a velocidade média de cerca de 10,7 para 7,1 km/h: esse é o custo de perder a lógica por detectores do SUMO.
(2) Sobre programas fixos, as variantes do PI ficam em 6,8–7,9 km/h, perto do controle nulo (7,1) e bem abaixo do actuated; só a amostragem de 10 s e o Kp maior ficam claramente acima do nulo. (3) Sobrepor o PI ao actuated piora o resultado (7,3 km/h): as duas lógicas disputam a duração das fases e o PI, ao encerrar verdes em rede saturada, desperdiça tempo perdido em amarelos.
(4) Sobrepor *apenas a prioridade ao ônibus* ao actuated superou a referência *nesta semente*, com a regra básica da época (que repetia pedidos por ônibus). No M4, com cinco sementes e a regra refeita (um pedido por ônibus e semáforo, só em movimento), o efeito é *estatisticamente nulo*. Concluímos que, nesta rede saturada e com semáforos inferidos, *o PI não melhora o actuated padrão* e a prioridade ao ônibus não tem efeito mensurável; a tabela é um registro da sintonia (feita com as regras básicas anteriores ao refinamento), não um resultado de ganho. *Limitações do controlador, que condicionam o resultado negativo.* (a) O termo integral, limitado em 6, contribui no máximo $K_i dot 6 = 0,9$, abaixo da banda morta $theta = 1$, então ele sozinho nunca dispara uma troca; na prática a regra é quase puramente proporcional, e as linhas `ki0` e `theta2` da tabela coincidem. (b) O erro soma veículos parados por faixa, sem normalizar nem subtrair filas a jusante, de modo que não é a pressão do _max-pressure_ e pode estender verde de faixas bloqueadas por fila. (c) O "estender" soma 5 s ao tempo restante a cada decisão; como o restante não encolhe, equivale a segurar a fase até o máximo. (d) Os sensores são idealizados (contagem de parados por faixa e identificação de ônibus pelo simulador), não modelam laços ou câmeras. (e) Segurança: amarelo de 3 s sem vermelho total (herdado do `netconvert`) e verde mínimo de 8 s, que pode ser menor que o tempo de travessia de pedestres; chamadas de pedestre são ignoradas. Na versão básica, a prioridade ao ônibus só avança o ciclo e pode não servir a fase do ônibus nem distinguir ônibus parado em ponto; a versão condicional corrige isso. A conclusão vale, portanto, para _esta implementação_, não para controle adaptativo em geral. A grade é pequena e de uma semente, e os concluídos diferem entre configurações (2.240 a 2.957), de modo que o atraso dos concluídos tem viés de sobrevivência e a velocidade espacial é a medida mais confiável. O M4 verifica o resultado com cinco sementes e uma ablação da prioridade ao ônibus. Atenção: com rotas de ônibus aleatórias (M2), o efeito da prioridade
é de natureza sistêmica e não deve ser lido como ganho para as linhas reais.

== Onda verde adaptativa

Implementada em `src/cps/greenwave.py` e avaliada no M4 como o cenário `tobe_gw`. Os semáforos do eixo recebem um *ciclo comum* de 90 s (os verdes são reescalados proporcionalmente, com amarelos mantidos e verde mínimo de 5 s); a *fase principal* é a que serve mais ligações do eixo;
e a defasagem ideal do semáforo $i$ é $o_i = (s_i slash v_p) mod C$, com $s_i$ a posição ao longo do eixo e $v_p$ a velocidade de progressão. A parte *adaptativa* reestima $v_p$ a cada 300 s pela velocidade média das arestas do eixo (limitada entre 5,5 e 13,9 m/s)
e desloca cada defasagem em até 8 s por atualização, ajustando a duração restante da fase atual. Os demais semáforos mantêm o _actuated_, *mas os semáforos do eixo perdem a lógica actuated* (passam a programas fixos de ciclo comum): isso confunde o efeito da coordenação com o de perder a atuação, e por isso o M4 inclui um controle com os mesmos programas fixos e defasagens aleatórias. Na versão corrigida, o reajuste só altera fases verdes e a velocidade de progressão vem só de arestas em fluxo livre.

*Limites.* (1) O eixo do manual, a Av. Mal. Floriano Peixoto, *não recebeu nenhum semáforo* na inferência do `netconvert`; usamos a Rua Mariano Torres (uma das seis vias do contorno, com 17 semáforos inferidos). (2) Ciclo, fases e posição dos semáforos são inferidos, então a coordenação não corresponde à operação real. (3) Há uma única direção de progressão (a defasagem não é bidirecional) e as velocidades em engarrafamento ficam abaixo do mínimo de progressão.
(4) A aritmética de defasagem e de reescala de verdes tem testes (`tests/test_models.py`); o efeito no tráfego aparece no M4.

= Comunicação MQTT

A malha fecha por mensagens, no formato do contrato do M1 (validado por `pydantic` a cada publicação):

#table(columns: (auto, 1fr), [Tópico], [Conteúdo],
  [`cps/curitiba/{id}/sensors/{sensor}`], [Mensagem do contrato (estado do laço, fila estimada em metros e CO₂ instantâneo das faixas, vindo do modelo de emissões)],
  [`cps/curitiba/{id}/state`], [Estado completo da interseção para o controlador (filas, ocupação, ônibus, fase)],
  [`cps/curitiba/{id}/signal/cmd`], [Comando do controlador: `hold`, `extend` + segundos ou `switch`],
  [`cps/curitiba/bus/{linha}/priority`], [Reservado para pedido de prioridade de ônibus (a implementar com dados da URBS)])

O nó de sensores, o controlador e o atuador são três clientes MQTT distintos (`src/cps/mqtt_bridge.py`), e o broker de produção é o Eclipse Mosquitto (`sim/mosquitto.conf`). Nesta máquina não havia Mosquitto nem Docker;
os testes usaram um broker MQTT 3.1.1 em Python (`amqtt`), com o mesmo protocolo. Cada troca leva um número de sequência: o atuador descarta respostas atrasadas de trocas anteriores, e uma troca sem resposta no prazo deixa a fase em `hold` (estado seguro). Os soquetes usam `TCP_NODELAY` para que a latência medida não seja dominada por Nagle e ACK atrasado. O teste de integração (`src/cps/mqtt_demo.py`) rodou #MQ.sim_seconds s de simulação com #MQ.tls_controlled.len() semáforos próximos aos pontos de medição:
#f0(MQ.msgs_published) mensagens publicadas, #f0(MQ.commands_received) comandos recebidos com #MQ.stale_discarded respostas atrasadas descartadas e #MQ.timeouts _timeouts_, e latência de ida e volta mediana de #f1(MQ.latency_ms_median) ms (p95 #f1(MQ.latency_ms_p95) ms), em localhost. Só os #MQ.tls_controlled.len() semáforos controlados são convertidos para programa fixo; os demais seguem _actuated_.

#aviso[
  O teste mostra que a malha fecha pelo broker e mede a latência local; ele *não* prova que as decisões via MQTT são idênticas às em processo (não há teste de equivalência), nem avalia perda de mensagens, QoS ou rede real. A troca é síncrona e bloqueante por interseção (até 2 s de espera), o que não escala para os 223 semáforos; um desenho de produção seria assíncrono e com o controlador no próprio gabinete. Não há TLS nem controle de acesso (`allow_anonymous`), só aceitável em laboratório.
]

= Sensoriamento IoT

*Dimensionamento.* Cada aproximação monitorada recebe um laço de presença na linha de retenção e um laço de avanço, posicionado conforme a fila de projeto (veículos acumulados em 1 min de vermelho, 7,5 m cada, limitado a 20–120 m);
cada cruzamento recebe uma câmera IP de contagem (processada por uma unidade de visão, como Raspberry Pi ou Jetson, e não pelo ESP32) e um medidor de nível sonoro de classe 2 (IEC 61672) com calibrador a 10 m do bordo (um microfone MEMS comum não atende à classe 2). Os laços e o medidor ligam-se a um nó ESP32 que publica no broker.
A amostragem de 5 s é a do controlador. Os #BOM.aproximacoes itens do plano são *arestas de aproximação* (em #BOM.pontos pontos com tráfego motorizado, P01 e P04), e não os 223 semáforos que o controlador comanda na simulação; o plano soma #BOM.lacos_indutivos laços, #BOM.cameras_contagem câmeras, #BOM.sensores_ruido_classe2 microfones e #BOM.nos_ESP32 nós,
com tráfego de #BOM.msgs_por_s mensagens/s e cerca de #BOM.kbit_s kbit/s, folgado para qualquer rede celular ou Wi-Fi. O tamanho de mensagem (420 B) é estimado e deve ser medido no nó real. A regra de posição do laço de avanço, que usa só a fila de projeto de 1 min de vermelho, resulta no piso de 20–35 m em todas as linhas e é, na prática, uma constante; o projeto real deve posicioná-lo pelo tempo de passagem e pela zona de dilema (da ordem de 40–50 m a 50 km/h).

#figure(image("figures/m3_sensors.png", width: 100%), caption: [Esquema de uma aproximação: câmera de contagem, laço de avanço, laço de presença, microfone e linha de retenção.]) <fig-sens>
#figure(image("figures/m3_eletrico.png", width: 100%), caption: [Diagrama elétrico em blocos de um nó de interseção: laço e cartão detector, nó ESP32, câmera e unidade de visão, medidor de ruído, comunicação e alimentação.]) <fig-ele>

O @fig-ele traz o diagrama elétrico em blocos de um nó. É uma referência de projeto, e não um esquema de fabricação (não traz cartão de laço específico, lista de componentes nem dimensionamento de proteção). O plano por aproximação está em `data/processed/m3_sensing_plan.csv`. A virtualização do hardware (Wokwi/Node-RED) não foi feita: o nó sensor é simulado em Python (`MqttBridge.exchange`), com as mesmas mensagens que um ESP32 enviaria. O dimensionamento dos laços depende das contagens e das filas reais.

= Modos ativos

Foram geradas duas variantes da rede (`src/cps/sumo_net.py`): *ativa*, com pedestres, ciclovias, calçadas e travessias (#NA.edges arestas, #NA.tls semáforos), e *To-Be*, que acrescenta faixas exclusivas de bicicleta nas vias de apoio (Rua Mariano Torres, Alameda Dr. Muricy, Rua Martim Afonso e Av. Pres. Kennedy, nos trechos secundários/terciários/primários: #NT.edges arestas, #NT.tls semáforos).
Para preservar os identificadores das arestas da rede base (e assim as rotas do M2), as variantes ativas não fundem trechos; as rotas ainda têm saltos onde a base fundiu e são reparadas com o `duarouter`. Sem fusão, a inferência de semáforos muda (limiar 107: #NA.tls semáforos na rede ativa; a de bicicleta tem #NT.tls porque as faixas alteram a valência dos nós), o que confunde parte da comparação e é tratado no M4 com um cenário só de faixas de bicicleta.

A demanda de modos ativos é #ph(body: [provisória]): #f0(AD.persons_routed) pedestres e #f0(AD.bikes_routed) ciclistas por hora. A rede de pedestres derivada de dados abertos é fragmentada: de #f0(AD.persons_requested_total) pares sorteados só #f0(AD.persons_routable) tinham caminho,
e mantivemos #f0(AD.persons_requested) deles, o que enviesa a demanda para pares conectados. Parte da fragmentação é nossa: as pistas de veículos proíbem pedestres (não há calçadas ao longo das vias), então só há caminho onde existem calçadas e travessias mapeadas. As faixas de bicicleta são uma *proposta*, modelada como faixa *adicional* (não retira espaço de carros, hipótese otimista), inclui vias primárias, e as rotas de ciclistas são pré-calculadas, de modo que não desviam para as novas faixas; largura, estacionamento e desapropriação ficam para o estudo de viabilidade. O comportamento de travessia no Calçadão é o padrão do SUMO (modelo _striping_); não foi calibrado.

= Reprodutibilidade e pendências

`make test` roda os testes; `python -m src.cps.tune`, `python -m src.cps.evaluate` e `python -m src.cps.active_eval` reproduzem a sintonia e a avaliação. A sintonia leva cerca de uma hora de CPU.

#table(columns: (auto, 1fr), [Pendência], [Ação],
  [Mosquitto e hardware], [Repetir o teste com Mosquitto e nós reais (ESP32/Wokwi); medir latência, perda e QoS],
  [Equivalência], [Teste automático comparando decisões via MQTT e em processo],
  [Onda verde], [Refazer com fases, ciclos e posições reais dos semáforos e em ambos os sentidos; usar a Av. Floriano],
  [Pedestres no controle], [O controlador não vê pedestres esperando; incluir demanda de travessia na pressão das fases],
  [Linhas da URBS], [Prioridade de ônibus só vale com os itinerários e a telemetria reais],
  [Sintonia], [Refazer com contagens reais, grade maior e várias sementes; testar outros algoritmos (ex.: max-pressure com aprendizado de fase) contra o actuated],
)

#bibliography("refs.bib", style: "associacao-brasileira-de-normas-tecnicas", title: [Referências])
