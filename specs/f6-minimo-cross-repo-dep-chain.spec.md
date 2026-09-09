# Spec: F6-mínimo — resolvedor de cadeia de dependências cross-repo por ref-em-prosa

- Frozen at: 2026-09-09
- Spec version: v1
- Source: Problem Brief `briefs/f6-minimo-cross-repo-dep-chain.BRIEF.md` v1 (frozen 2026-09-09) — PRD skipped
  (feature dentro de produto existente; Vision/PRD dispensados, SP* citam Brief J*/S* direto)
- Status: frozen after approval on 2026-09-09 (operador "Congelar + build agora")
- Amendments: none

## Design

O que EXISTE hoje (a reusar, não reconstruir): `federate()` (fan-out per-source, BR04), `TrackerSource`
(lista issues **OPEN** por repo, escopado pelos `<repo>#<n>` que a query nomeia; emite `has-open-issue`),
`TasksSource` (lista tasks GTD abertas, extrai `<repo>#<n>` do texto → `has-task` pela SLUG do repo),
`repo_refs()` (extrai slugs, **descarta o número**), `compose_repo_issues()` (agrupa satélites SOB repos),
`relevant_repos()` (escopo de apresentação). Superfícies: `iris context` (CLI) + paridade MCP.

O GAP que o F6-mínimo preenche: o caminho atual entrega "todas as issues OPEN dos repos que o item
menciona". O cenário precisa do oposto — o **estado vivo das issues ESPECÍFICAS referenciadas** (incl.
CLOSED: o item flip cita `iris#6`/`iris#19` fechadas, que "todas-open" nunca mostra), keyed no ref
específico `token#N` (não na slug), mais as âncoras `^anchor` within-store, compostas num `item ⋈
referenced-nodes` com candidatos-a-bloqueador por dado.

### Architecture
Nova composição irmã de `compose_repo_issues`, NÃO uma substituição — o join keyed-no-ref-específico é um
eixo distinto do join agrupa-satélites-sob-repo. Arranjo escolhido: **estender por adição** (novo parser
de refs + novo modo de fetch específico no tracker + nova `compose_referenced_nodes` + novo verbo CLI/MCP),
mantendo o caminho `context` intacto — **sobre** (a) reescrever `compose_repo_issues` p/ ambos os modos
(perde: acopla dois joins de eixos diferentes num só, contra BR01/clareza) e (b) um repo/módulo novo
(perde: é a mesma bounded-context da composição cross-fonte, ceremony sem ganho). Fluxo:
`item-text → parse refs (token#N + ^anchor) → resolve cada ref à sua fonte (tracker fetch-específico /
tasks lookup) → federate → compose_referenced_nodes → blocker-view (CLI/MCP)`.

### Data model
- `Node(kind="issue")` ganha estado open/closed via o campo `roles` já existente (`roles=["open"]` |
  `["closed"]`) — sem novo campo (mínimo). Idem para `kind="task"` (âncora resolvida: `["open"]`/`["done"]`).
- Nova relação `references` (`Relation(from_=<item-id>, type="references", to=<node-id>)`) como carrier do
  join keyed-no-ref — distinta de `has-open-issue`/`has-task` (que são agrupa-sob-repo).
- Novo resultado composto `ReferencedChain` (frozen): `item` (o texto/id de origem), `resolved: list[Node]`
  (refs resolvidos c/ estado), `unresolved: list[str]` (refs cujo fetch falhou/BR04 = **unknown**, nunca
  clear), `blocker_candidates: list[Node]` (subconjunto de `resolved` OPEN e/ou marcado gate/blocked-by).

### Interfaces / contracts
- `parse_refs(text) -> list[Ref]` onde `Ref` = `(kind: "issue"|"anchor", slug|None, number|anchor)`.
  Estende o regex existente `_REPO_REF` p/ **capturar o número**; adiciona `_ANCHOR_REF` p/ `\^[a-z0-9]+`.
- `compose_referenced_nodes(item_text, result: FederationResult) -> ReferencedChain`. Puro, read-only.
- CLI: `iris chain "<item-text-or-ref>"`; MCP: tool `chain` em paridade (mesma composição + apresentação).

### Cross-cutting
- BR04 (isolação): um ref cujo fetch falha → `unresolved` (unknown), NUNCA omitido nem marcado clear —
  a guarda de failure-mode (nunca afirmar falso "nada trava").
- BR03 read-only; BR02 source-agnostic (fetch específico usa a mesma config/CLI declarada, sem instância).
- Telemetria: registrar o request `chain` (como `context`/`ground` já fazem) p/ o audit do dogfood.

## Task plan
- F6-T1: **Parser de refs.** Estender `_repos.py` (ou novo `refs.py`) com `parse_refs(text)` que extrai
  `token#N` **preservando o número** e `^anchor`, first-seen order, dedup. — serves Brief:J1 — acceptance
  (EARS): "WHEN o texto contém `iris#5`, `agent-kit#1464` e `^dogfd1`, the SYSTEM SHALL retornar os três
  Refs tipados com (slug,number) e (anchor) corretos; AND a heading `## x` ou `PR #32` NÃO gera Ref." —
  deliverable: teste de regressão persistido — depends on: —
- F6-T2: **Estado open/closed + fetch específico no tracker.** Modo do `TrackerSource` que, dados os
  `token#N` da query, faz fetch da issue ESPECÍFICA por número (incl. CLOSED) e carrega o estado em
  `roles`; emite `Relation(item, "references", ident#number)`. — serves Brief:J2,J3 — acceptance (EARS):
  "WHEN a query nomeia `iris#6` (fechada), the SYSTEM SHALL emitir um Node issue `iris#6` com
  `roles=['closed']`; IF o fetch de um ref falha, THEN the SYSTEM SHALL degradar aquele ref (nota), não
  sinkar a federação (BR04)." — deliverable: (a) teste persistido c/ runner injetado (sem gh real);
  **(b) reconciliação de domínio** — `docs/domain.md` é feito FALSO por esta task (Issue "Only OPEN issues
  are modeled" → Issue pode carregar estado de lifecycle `roles` [open|closed] QUANDO referida
  especificamente; registrar a relação `references` e a composição `item ⋈ referenced-nodes` no vocabulário)
  — atualizar como deliverable (regra doc-contract-falso). — depends on: F6-T1
- F6-T3: **Resolução de âncora (modo done-inclusive NOVO).** Resolver `^anchor` → o item GTD com estado
  (`open`/`done`) e marcadores gate/trigger parseados do texto. ATENÇÃO (achado blind J1): `TasksSource`
  lista SÓ tasks abertas — resolver uma âncora `done` exige um modo de fetch NOVO (mesma forma do
  fetch-closed do tracker), não um lookup do read incumbente. — serves Brief:J2,J3 — acceptance (EARS):
  "WHEN o texto referencia `^dogfd1` e ele está na lista GTD com um marcador gate, the SYSTEM SHALL
  resolvê-lo a um Node task com `roles=['open']` e o marcador gate capturado; WHEN referencia uma âncora
  RESOLVIDA (done), the SYSTEM SHALL emitir o Node task com `roles=['done']`; WHERE a âncora não é achada,
  the SYSTEM SHALL marcá-la unresolved (unknown)." — deliverable: (a) teste persistido; (b) reconciliação
  domain.md (Task "Only OPEN tasks are modeled" → lifecycle `roles` [open|done] quando referida). — depends on: F6-T1
- F6-T4: **Composição `compose_referenced_nodes` + marcação de bloqueador por dado.** Compõe o
  `ReferencedChain`; marca `blocker_candidates` = refs resolvidos OPEN e/ou com relação gate/blocked-by na
  prosa; refs com fetch falho → `unresolved` (NÃO clear). — serves Brief:J4 — acceptance (EARS): "WHEN o
  chain tem `iris#6` closed, `^dogfd1` open+gate e `iris#5` open, the SYSTEM SHALL listar `^dogfd1` e
  `iris#5` como blocker_candidates e `iris#6` como resolved-não-bloqueador; IF um ref é unresolved, THEN
  the SYSTEM SHALL NÃO afirmar 'nada trava'." — deliverable: teste persistido — depends on: F6-T2, F6-T3
- F6-T5: **Superfície `iris chain` (CLI) + paridade MCP + IA do blocker-view.** Verbo novo; apresenta
  candidatos-a-bloqueador em DESTAQUE, separando "resolvido por dado" de "unknown (fonte falhou)" e do
  julgamento-do-agente; telemetria `chain`. — serves Brief:J4 (IA/failure-mode) — acceptance (EARS): "WHEN
  `iris chain '<item>'` roda, the SYSTEM SHALL emitir o blocker-view com os candidatos-a-bloqueador
  primeiro e uma seção `unknown` distinta; AND a tool MCP `chain` SHALL retornar a mesma composição." —
  deliverable: teste CLI+MCP persistido + doc user-facing (README/usage: o novo verbo) — depends on: F6-T4
- F6-T6: **Rodar o trial → veredito ^dogfd1.** Rodar `iris chain` sobre 2–3 itens reais de spread
  cross-repo; ISOLAR a fatia cross-fonte (`token#N`) da within-mneme (`^anchor`); comparar ao baseline de
  hand-assembly. — serves Brief:J5,S1,S2,S3 — acceptance (eval strategy): rubric = {reproduz o conjunto
  refs+estados+candidato-a-bloqueador do hand-assembly; a fatia cross-fonte carrega valor que nenhum read
  within-store reproduz (F1 do Brief) E é atribuída à camada por C1/BR01 — a composição cross-fonte ao vivo
  é job da camada, o que licencia não construir um comparador incumbente-com-forge (Brief F4/S1)} +
  held-out set = 2–3 itens reais + **baseline de hand-assembly capturado POR ITEM do trial** (o
  ^dogfd1: 4 contextos/5 fetches é o de UM item, Brief F5 — capturar os demais no trial) + grader =
  comparação manual ao baseline per-item + target bar = EARN se a fatia cross-fonte carrega blocker-value
  real; retire-adjacent se reduz a âncoras foldable. **O veredito registrado (nota
  `iris-dogfood-publish-hold-decision-state` §VEREDITO + task `^dogfd1`) SHALL carregar a qualificação S3:
  um EARN com n=2–3 selecionado lê-se como "ganha no caso maximamente cross-fonte", NÃO "ganha
  tipicamente".** — depends on: F6-T5

## Coverage check (every in-scope Brief J*/S* -> ≥1 task)
- Brief:J1 -> F6-T1
- Brief:J2 -> F6-T2, F6-T3
- Brief:J3 -> F6-T2, F6-T3
- Brief:J4 -> F6-T4, F6-T5
- Brief:J5 -> F6-T6
- Brief:S1, S2, S3 -> F6-T6 (o trial verifica S1/S2; S3 = a qualificação obrigatória do veredito registrado)
- (nenhuma task sem J*/S* = sem scope creep)

## Deliberate exclusions (from the Brief)
- Brief:N1 (julgamento semântico do bloqueador) — EXCLUÍDO; F6-T4 marca candidatos por DADO, o agente julga.
- Brief:N2 (protocolo F6 completo) — DEFERIDO. `Trigger-source: cenário que exija identidade não-inferível
  do slug — fires quando um ref não resolver por (slug,number)/anchor.`
- Brief:N5 (fonte tipo-banco/TJPA) — fora. `Trigger-source: operador eleger o frame database-como-fonte.`
- CLOSED-state para TASKS/âncoras além de open/done — só o mínimo (open/done); estados GTD mais ricos não
  entram. `Value-rejected: o cenário só precisa distinguir gate-ativo de resolvido.`

## Risks / unknowns
- R1: o fetch específico por número (incl. closed) depende do CLI de forge suportar `issue view N --json
  state` uniformemente (gh sim; glab a confirmar). Mitigação: F6-T2 injeta runner; o mapeamento JSON é
  config (BR02) — se glab divergir, é config, não código. Confirmar no trial (itens são gh hoje).
- R2: a fatia cross-fonte pode ser fina nos itens reais (invalidator do Brief) — é PRECISAMENTE o que
  F6-T6 mede; um resultado retire-adjacent é veredito válido, não falha de build.

## Assumptions & invalidators
- A1 (tech bet): estender o tracker p/ fetch específico é mais barato que uma fonte nova — invalidado se o
  modo específico exigir um fluxo de auth/scope incompatível com o list-open atual (então: fonte separada).
- A2: `roles` como carrier de estado serve sem novo campo — invalidado se o consumo precisar de estado
  tipado além de string (então: campo `state` no Node).

## Open questions
- Nome do verbo: `chain` (adotado) vs `blockers` vs estender `context` com modo-ref. Resolvido: `chain`
  (verbo novo, não sobrecarrega `context` cujo eixo é agrupa-sob-repo). Reversível no build se soar mal.
- [carregada do Brief] Frequência TÍPICA de itens cross-fonte-ao-vivo no fluxo real — a validação externa
  que n=2–3 selecionado não fecha (Brief open-question). NÃO resolvida por este Spec; se o veredito for
  EARN, é o próximo passo de validação. `Trigger-source: um veredito EARN em F6-T6 — fires quando earn
  demandar generalização além do caso maximamente cross-fonte.`

## Domain reconciliation (achado blind J1 — mudança de contrato durável registrada)
Este Spec MUDA o domain.md (contrato durável), não só o distila. As mudanças (deliverables de F6-T2/T3/T4):
Issue/Task ganham estado de lifecycle em `roles` (open|closed / open|done) QUANDO referidos
especificamente; nova relação `references`; nova composição `item ⋈ referenced-nodes`. Registrado aqui p/
o freeze não passar silencioso sobre "Only OPEN modeled". A atualização do domain.md acontece no build.
