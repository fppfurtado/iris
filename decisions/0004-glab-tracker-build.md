# 0004 — Build decisions for the forge-per-host tracker (iris#81)

- Date: 2026-11-19
- Context: the build of `specs/spec-repo-issues-federation.md` v3 (SP-T8, SP-T9), `specs/f6-minimo-cross-repo-dep-chain.spec.md`
  v1.1 (F6-T7) and `specs/item-inbound-context.spec.md` v3 (SP-T13). These are the choices the frozen Specs left
  open, resolved while building. They bind the code; a Spec amendment may supersede them.

## D1 — The tracker keeps `_command` and `_map` as names for the top-level settings

The settings moved to one per-repo resolution (`_settings`), but `tests/test_s2_proof.py` proves "no forge
baked in" by reading `src._command == []` and `src._map == {}`. The Spec requires the existing tests to pass
unchanged, so both names stay as aliases of the top-level values rather than the test being rewritten.

## D2 — Unserved and unmapped notes are aggregated, one line per host or raw value

`N repo(s) unserved (<host>): no \`command\` for this host`, `chain: N ref(s) unserved (<host>): no \`view\`
command for this host`, `chain: state '<raw>' not mapped (N ref(s))`. A `local:` slug reports as the host
`no forge host`. One line per host keeps a large registry's note readable; the count says how many it covers.

## D3 — A `forges` key is normalised like the slug host: lowercased, port dropped

`forge_slug` drops the port and lowercases the host, so a key written `Host:2222` must match the same slug. The
key is stored by the normalised host; a second key with the same host is the duplicate the Spec ignores.

## D4 — SP-T13's CLI assertions sit beside the MCP ones

The Spec names `tests/test_cli_commands.py` for SP-T13's CLI checks. They are in `tests/test_mcp_adapter.py`
instead, in the same tests as the MCP checks, because that module already fakes both surfaces' passes with one
helper and the point of SP-T13 is that both render the composer's one value (parity).
