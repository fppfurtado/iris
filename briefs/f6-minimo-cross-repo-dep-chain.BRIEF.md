# Problem Brief: F6-mínimo — resolver a cadeia de dependências cross-repo por ref-em-prosa

- Frozen at: 2026-09-09
- Mode: verifiable
- Distilled from dossier: `iris/.throughline/dossiers/f6-minimo-cross-repo-dep-chain.md`
- Brief version: v1
- Status: frozen after approval on 2026-09-09 (operador "Congelar e seguir p/ software-track")
- Amendments: none
- Parent frame: `working-state/programs/contexto-digital-integral/costura-iris-fonte.BRIEF.md — extends`
  (este problema é um CHILD/instância: o Brief-pai deixou o protocolo de identidade cross-store, F6, como
  questão aberta; este frame recorta e constrói o F6 MÍNIMO que serve um cenário concreto.)
- persona-input: operator-proxy (o operador é o end-user do surface agent-context — a superfície é
  consumida por ele via agente por escolha declarada; commissioner e end-user coincidem, falsificável.)

## Problem statement
Dado um item de trabalho cuja prosa carrega refs cross-repo (`token#N`) e/ou âncoras de lista
(`^anchor`), não existe uma composição one-shot que resolva cada ref à sua fonte, busque o ESTADO VIVO
de cada um através dos repos, e sinalize por dado o que trava o item. Importa porque a alternativa é
montar essa cadeia à mão por N superfícies a cada vez (baseline medido: um item cruzando 3 repos custou
4 contextos de repo / 5 fetches + a resolução token→repo), uma fricção recorrente e nomeada como dor real
pelo operador — e porque essa composição é o caso de teste que adjudica, no mérito, o gate earn-or-retire
da camada de contexto (a camada federadora ganha o lugar dela, ou uma fonte cresce o read e a camada
aposenta?).

## Jobs in scope
- J1: Parsear da prosa de um item de trabalho os dois tipos de ref: `token#\d+` (issue cross-repo) e
  `^anchor` (âncora de lista/GTD within-store-de-conhecimento).
- J2: Resolver cada ref à sua fonte respectiva — `token`→repo via o registro de repos (identidade por
  slug, já existente); `^anchor`→item via a fonte de conhecimento já federada — e fan-out sobre AMBOS os
  tipos de fonte, com isolação per-source.
- J3: Buscar o estado VIVO de cada ref (open/closed + título + marcadores de gate/trigger achados na prosa)
  via a fonte que o possui.
- J4: Compor `item ⋈ referenced-nodes` num único resultado e marcar candidatos-a-bloqueador POR DADO (refs
  ainda OPEN + qualquer relação blocked-by/gate explícita parseada da prosa) — deixando o julgamento do
  bloqueador final para o consumidor.
- J5: Rodar o trial sobre 2–3 itens reais de spread cross-repo e comparar contra o baseline de
  hand-assembly, ISOLANDO a fatia cross-fonte da fatia within-single-source, para render o veredito do gate.

## Non-goals (explicitly out of scope)
- N1: Julgamento SEMÂNTICO de "o único que trava o item" — a camada serve o contexto composto; o consumidor
  julga. `Value-rejected: contradiz o papel read-only/compose da camada (não infere, expõe dado).`
- N2: O protocolo de identidade cross-store COMPLETO (F6 inteiro do Brief-pai) — só o slice mínimo.
  `Trigger-source: necessidade validada de relações declaradas entre canônicos além da derivação por
  slug — fires quando um cenário exigir identidade não-inferível do slug compartilhado.`
- N3: Qualquer write-back / mutação de tracker ou fonte — barrado por construção (read-only).
  `Value-rejected: invariante de domínio (nenhum write path existe em nenhuma fonte).`
- N4: Re-decidir a EXISTÊNCIA da camada federadora — este trial MEDE o earn-or-retire; não re-abre o split.
  `Trigger-source: um veredito retire deste próprio gate — fires se a fatia cross-fonte medida for fina o
  bastante que o valor reduza a reads within-single-source foldable.`
- N5: 2ª fonte tipo-banco / corpus institucional (cenário-irmão de maior pull) — VPN-gated, frame próprio.
  `Trigger-source: o operador eleger o frame "database como fonte" — fires quando job/escopo/garantia
  read-only forem framados.`

## Constraints
- C1 (seam rule, ratificada / BR01): a composição CROSS-fonte é job da camada; cada fonte mantém seu read
  within-source. O join por ref-em-prosa fana-out sobre N trackers + registry + a fonte de conhecimento =
  legitimamente cross-fonte. Uma fonte que cresça para fazer composição cross-fonte ao vivo VIRA a camada
  (re-host), não a aposenta.
- C2 (converge, não soma N+1 / BR05): o valor só se justifica se a composição entregar o que nenhuma
  chamada única within-source entrega. É o teste central — e a fatia within-mneme (âncoras) é EXCLUÍDA da
  conta de earn (foldable numa fonte que cresce o read).
- C3 (read-only + identity-mediated + source-agnostic / BR03·BR06·BR02): sem write path; join por identidade
  resolvida (token→repo, âncora→item), nunca coincidência posicional; nenhum adaptador nomeia instância
  privada (a concreta vive só na config privada).

## Success criteria
- S1 — verificável (DISCRIMINANTE earn/retire): isolando os refs `token#N` cross-repo dos `^anchor`
  within-store, a composição one-shot resolve o estado vivo (open/closed + gate) de cada issue através de N
  forges — valor que nenhum read within-store da fonte incumbente reproduz. EARN se essa fatia cross-fonte
  carrega valor real de blocker-resolution (atribuída à camada por C1/BR01). NÃO-EARN/retire-adjacent se os
  itens reais raramente cruzam ≥2 domínios-de-fonte ao vivo (o valor reduz a âncoras foldable).
- S2 — verificável (baseline): sobre 2–3 itens reais, a composição reproduz o conjunto de refs + estados +
  candidato-a-bloqueador que o hand-assembly produziu, em 1 chamada vs as N superfícies enumeradas.
- S3 — validade externa (registrado, não gate): com n=2–3 selecionados pela propriedade cross-fonte, um
  veredito EARN lê-se como "ganha no caso maximamente cross-fonte", não "ganha tipicamente".

## Key facts and provenance
- F1: A fonte de conhecimento incumbente expõe, para um ref, apenas seu GRAFO DE CITAÇÃO estático
  within-store ("quais docs mencionam este ref"; "quais docs este ref cita"), categoricamente distinto do
  ESTADO VIVO (open/closed) de cada issue buscado dos forges. — basis: probe direto do `backlinks` da fonte
  sobre uma âncora e um issue-ref, 2026-09-09. (Prova de não-redundância vs chamada-única.)
- F2: O modelo de domínio já deriva a ligação item→repo a partir de refs `<repo>#<número>` na prosa (por
  identidade, não campo carregado), e já compõe `repo ⋈ open-issues` / `repo ⋈ referencing-tasks` (arm-a
  shipado). O F6-mínimo reusa esses mecanismos, keyado no ref ESPECÍFICO em prosa, não em "todas as issues
  de um repo". — basis: docs/domain.md (Task, Identity/BR06, Composition), 2026-09-06.
- F3: O chain real de um item mistura `^anchor` within-store (foldable numa fonte que cresce o read) COM
  `token#N` de N repos (cross-fonte ao vivo). Compor os dois num único blocker-view é cross-fonte — nenhuma
  fonte única cruza ≥2 domínios ao vivo — logo folding de âncoras reforça o caso cross-source, não o
  reintroduz como miragem within-single-source. — basis: exemplo do operador + análise de costura, 2026-09-09.
- F4: O braço retire (a incumbente absorve transporte+composição, aposentando a camada) NÃO é adjudicado por
  "a incumbente só lê o próprio store" (propriedade trocável, e contradiz a definição de retire do Brief-pai):
  por C1/BR01 ratificado, composição cross-fonte ao vivo é definitionalmente job da camada, então a
  incumbente crescendo para fazê-la VIRA a camada. O trial não constrói um comparador incumbente-com-forge;
  isola a fatia cross-fonte e a atribui pela regra ratificada. — basis: blind-critic J6 + reframe, 2026-09-09.
- F5: O baseline de hand-assembly de um item cruzando 3 repos = 4 contextos de repo / 5 fetches de issue +
  a resolução token→repo. — basis: probe enumerado sobre o item `^dogfd1`, 2026-09-09.

## Deliberate exclusions (from the dossier)
- Candidatos R0/R2/R3/R4 da regra de costura e o log de adjudicação — working garbage herdado do Brief-pai
  (a regra ratificada é BR01/C1).
- O comparador "incumbente-crescida-com-forge" — NÃO construído deliberadamente; substituído pela atribuição
  por C1/BR01 (F4). `Value-rejected: construí-lo re-provaria a camada sob outro nome (viola a premissa de
  que composição cross-fonte é job da camada); a discriminação vem de isolar a fatia cross-fonte, não de
  construir o rival.`

## Solution-space status (NOT a solution)
- Vehicle: committed (software — extensão fina da camada de contexto existente; o trial adjudica se a camada
  earn ou retire, não se software é o veículo).
- Settled when: o gate earn-or-retire conclui — earn (a fatia cross-fonte isolada carrega valor real de
  blocker-resolution) ou retire-adjacent (os itens reais quase não cruzam ≥2 domínios-de-fonte ao vivo).
  Teste de refutação mais barato JÁ RODADO em parte (F1: `backlinks` ≠ estado vivo cross-forge); o restante
  = rodar a composição vs hand-assembly sobre 2–3 itens reais.

## Open questions carried forward
- O protocolo de identidade cross-store COMPLETO (F6 do Brief-pai) — declaração/consulta de relações entre
  canônicos além da derivação por slug; este Brief só entrega o slice mínimo (N2).
- Se o veredito for EARN no caso maximamente cross-fonte (S3), qual a frequência TÍPICA de itens
  cross-fonte-ao-vivo no fluxo real — a validação externa que n=2–3 selecionado não fecha.
