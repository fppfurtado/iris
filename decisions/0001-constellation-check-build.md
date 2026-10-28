# 0001 — Build decisions for the constellation membership check

- Date: 2026-10-28
- Context: the build of `specs/constellation-membership-check.spec.md` (v1, iris#48). These are the choices
  the frozen Spec left open, resolved while building. They bind the code; a Spec amendment may supersede them.

## D1 — Dimension coverage travels as `scope` nodes

The composer must know which dimensions ran — which forge host+orgs were read, and whether on-disk roots
were scanned — to bound its forge comparisons and to report `skipped`. A federation result carries only
nodes, relations and free-text notes, so the sources emit one `Node(kind="scope")` per configured forge org
(`forge-repos`) and per configured root (constellation, universe reads only), with `attrs.dimension`
(`forge` | `roots`) and `attrs.read`. An org or root that is configured but unread shows as
`read = false`, distinct from one that is absent.

- Over parsing the per-source notes: notes are prose, keyed by an instance name the config chooses.
- Over passing the config to the composer: the composer would re-derive what the sources already know.
- Consequence: every existing consumer filters `kind == "repo"`, so scope nodes are invisible to it.

## D2 — `iris check` queries the `universe` kind alone

The Spec's architecture sketch shows `federate(kinds={nodes, universe})`. The command asks for
`{universe}` only: constellation and `forge-repos` both produce it, and a `nodes` kind would also route the
query to the `tracker` and `tasks` sources (BR07), whose results the check discards.

## D3 — Host aliases are applied by the composer

`[check.host_aliases]` lives in the `[check]` table, which a source does not receive (a source gets only
its own options). The slug helper takes an alias map, the sources emit slugs without aliasing, and
`compose_membership` maps every slug's host through the aliases before joining. The effect on every join is
the one the Spec requires; the alias-mapped slug is not stored on the node.

## D4 — `uncloned` needs every configured root read

A forge repo cloned outside the registry is found only by the roots scan, so with no roots configured — or
a configured root unreadable — `uncloned` would report repos that are in fact cloned. In that case the kind
is not computed and `skipped` names the roots dimension, which keeps the exit code at 2 rather than reporting
false drift.

## D5 — `duplicate-identity` ignores the `local:<basename>` fallback

Two checkouts without an `origin` remote and with the same directory name share the fallback slug
`local:<basename>` without being one repo. The fallback is not an identity, so it does not fire
`duplicate-identity`.

## D6 — Resource consumers are live members

`dangling-dependency` and `one-end-only` read the `dependsOn` refs of live members only: an archived repo
cannot update its descriptor, and its declarations no longer describe a live coupling.
