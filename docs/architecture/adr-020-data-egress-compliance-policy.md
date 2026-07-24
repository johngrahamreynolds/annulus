# Status: Proposed
**Date:** 2026-07-22

## Context

Annulus's stated premise (`README.md`, `vision.md` principle 3) includes local-first
operation for ITAR-restricted environments. `EscalationPolicy`
(`packages/router/src/annulus_router/escalation.py`) and `ModelRouter` implement
binary local→frontier escalation on error or empty response
([ADR-005](adr-005-frontier-escalation.md)), sending whatever `messages` the client
sent — including injected retrieval context
([ADR-004](adr-004-retrieval-tools-agent-loop.md)) — to the configured `frontier`
profile with **no policy check of any kind**.

`config/models.yaml`'s `frontier` profile (`provider: openai`, `model: gpt-4o-mini`)
and the `escalation` block (`on_local_error: true`, `on_empty_response: true`,
`frontier_profile: frontier`) are the entire escalation policy surface today. There is
no "this workspace may not egress," no allowed-destination-host list, no ZDR flag.
`packages/core/src/annulus_core/config.py` has zero fields for egress, ZDR, or
allowed destination hosts (confirmed by grep) across its `gateway` / `trace` /
`router` / `agent` / `retrieval` / `tools` / `models` sub-configs (`config.py:107-113`).
"ZDR" appears only in prose (`README.md:93`, `docs/continue-config.example.yaml:53`)
— never enforced in code.

[ADR-007](adr-007-remote-compute-profiles.md) already separates the Annulus gateway
key from backend profile keys — good precedent this ADR extends — but explicitly
addresses *how* a connection is authenticated, not *what data* may cross a profile
boundary. The review flags this as "arguably the highest-stakes missing decision"
given the ITAR/NASA framing.

## Decision

Add an explicit **egress policy**, evaluated by `ModelRouter`/`EscalationPolicy`
**before** any request leaves the `local` provider tier (before routing to
`lab-gpu`, `frontier`, or any non-`ollama` profile). Policy is per-project
([ADR-022](adr-022-per-project-agent-policy.md) owns the config surface; this ADR
defines the semantics it must express):

- `egress: none | zdr_only | allowed` — `none` disables escalation and remote
  profiles entirely regardless of `router.escalation_enabled`; `zdr_only` restricts
  eligible profiles to those flagged `zdr: true`; `allowed` is today's unrestricted
  behavior (the default, preserving current behavior on upgrade).
- Extend `ModelProfile` (`config.py`) with `zdr: bool = false` and
  `allowed_destinations: list[str] | None` (hostname allowlist for `apiBase`),
  closing the gap that any `apiBase` is currently trusted implicitly.
- `EscalationPolicy.should_escalate` and [ADR-007](adr-007-remote-compute-profiles.md)'s
  tiered ladder must consult the resolved egress policy before selecting a target
  profile; a denied escalation degrades to "return the local result as-is" (never
  silently drops the request) and is traced (`chat.completions` span attribute
  `escalation.denied_reason`).

**Scope:** outbound model-inference calls only (routing tier) for this pass. Future
embedding/graph provider calls ([ADR-009](adr-009-hybrid-retrieval-embeddings.md)/[ADR-010](adr-010-graphrag-lite.md))
and any MCP tool calling an external API must be brought under the same policy —
flagged as a forward-compat requirement, not designed here.

**Non-goals:** no network-level enforcement (egress proxy/firewall) — this is an
application-level gate in the router, trusted at the same boundary as the tool
sandbox; no telemetry/crash-reporting egress policy (Annulus sends none today — an
assumption stated here, not verified network-level); no ITAR *certification* —
Annulus provides the enforcement primitive, classification is a legal/organizational
determination outside this ADR.

## Consequences

**Positive**

- Makes local-first a technically enforced default, not just documented convention —
  the single highest-leverage change for the ITAR/NASA use case in `vision.md`.
- Reuses [ADR-007](adr-007-remote-compute-profiles.md)'s profile structure instead of
  a parallel config surface.
- Traced denials give an audit trail for free once
  [ADR-023](adr-023-provenance-evaluation-data-model.md) lands.

**Negative**

- Two more fields to keep correct per profile (`zdr`, `allowed_destinations`) —
  misconfiguration (a profile marked `zdr: true` that isn't) is a policy-vs-reality
  gap this ADR can surface but not close alone.
- Adds a decision point to every escalation's hot path.
- `egress: none` changes today's default escalation behavior for existing
  deployments if defaulted wrong — must default to `allowed` on upgrade.

## Open questions

- Default `egress` when no per-project policy exists yet — global fallback
  (`allowed`) or fail-closed (`none`) until [ADR-022](adr-022-per-project-agent-policy.md)
  ships?
- Is `zdr: true` self-asserted in `models.yaml` (trust the operator) or does it need
  a verification hook (out of scope today, flagged as a future gap)?
- Does egress policy cover tool output injected into later turns (e.g. `git_diff`
  output sent to `frontier` on escalation), not just the original user message —
  almost certainly yes, but the enforcement point needs to see the full outbound
  payload.
- Is a denied escalation an [ADR-019](adr-019-permission-capability-model.md)
  "capability denial" event, or a distinct `egress.denied` event type?

## References

- [vision.md](vision.md)
- [adr-005-frontier-escalation.md](adr-005-frontier-escalation.md)
- [adr-007-remote-compute-profiles.md](adr-007-remote-compute-profiles.md)
- [adr-009-hybrid-retrieval-embeddings.md](adr-009-hybrid-retrieval-embeddings.md)
- [adr-019-permission-capability-model.md](adr-019-permission-capability-model.md)
- [adr-022-per-project-agent-policy.md](adr-022-per-project-agent-policy.md)
- `packages/router/src/annulus_router/escalation.py`
- `packages/router/src/annulus_router/router.py`
- `packages/core/src/annulus_core/config.py`
- `config/models.yaml`
