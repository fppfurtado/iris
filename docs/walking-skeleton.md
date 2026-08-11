# Walking skeleton — the S2 proof

The Phase-1 walking skeleton proves **S2**: an agent obtains the context relevant to a
task in **one interaction**, without landing on multiple surfaces.

## The origin question

> Which repos are tagged `pro-bono`, and what is their state?

Answering this the old way meant visiting several surfaces — the repo manifest, then
each repo's metadata, and so on. iris federates them behind one read-only call.

## One interaction, either surface

CLI:

```
$ iris repos --tag pro-bono
relatorios-h3  [pro-bono]  (service)
```

MCP (any MCP-native harness — verified here with the FastMCP in-memory client):

```
tool: repos   args: {"tag": "pro-bono"}
→ [{"id": "relatorios-h3", "tags": ["pro-bono"], "roles": ["service"], ...}]
```

Both return the **same** answer — the matching repos plus their state (tags/roles, and a
coverage flag for repos lacking `catalog-info.yaml`) — off the same federation core, in a
single interaction.

## What backs it

- `iris.core.federation.federate` composes the declared sources, isolating any one that
  fails so it never sinks the result.
- The CLI (`iris.cli`) and the MCP adapter (`iris.mcp_adapter`) are thin surfaces over
  that one core, so the answer is identical whichever surface an agent uses.
- Verified by `tests/test_s2_proof.py`.
