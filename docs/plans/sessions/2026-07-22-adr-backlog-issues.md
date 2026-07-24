# ADR backlog — GitHub issue list (paste-ready)

Not created automatically. Paste into GitHub manually or via Cursor / `gh issue create`.

---

## Documentation issues

### 1. Draft ADR-017 — skill primitive (Tool↔Skill↔Agent boundary)

**Labels:** `documentation`, `adr`

Defines the skill packaging unit (name, prompt fragment, tool allowlist, params)
stored under `.annulus/skills/*.yaml`, and the boundary rule: Tool = stateless
function, Skill = scoped recipe within one run, Agent = configured identity that
loads skills. Blocks ADR-024 (scientific spike) and ADR-018 (agent config).

---

### 2. Draft ADR-018 — agent identity & configuration

**Labels:** `documentation`, `adr`

Defines `AgentConfig` (role, prompt override, model-profile binding, retrieval
scope, skill list, tool allowlist) as `.annulus/agents/*.yaml`. Prerequisite for
ADR-008 swarm orchestration, which already assumes configurable agents that
don't exist yet.

---

### 3. Draft ADR-019 — permission & capability authorization model

**Labels:** `documentation`, `adr`

Defines the capability-gate (`{tool_name, path scope, mode}`) that replaces the
currently dead `ToolsConfig.allowed_commands` config field. Blocks any
write-capable tool from shipping (`propose_edit`, #31–33).

---

### 4. Draft ADR-020 — data-egress & compliance policy

**Labels:** `documentation`, `adr`

Defines `egress: none | zdr_only | allowed` policy enforced by `EscalationPolicy`
before any request leaves the local provider tier. The review calls this
"arguably the highest-stakes missing decision" given the ITAR/NASA framing in
vision.md.

---

### 5. Draft ADR-021 — plan-before-act interaction protocol

**Labels:** `documentation`, `adr`

Defines the `proposed → approved | modified | rejected` flow gating `apply`-mode
tool calls, surfaced identically in CLI and gateway. Must land before any
`apply`-mode write tool ships broadly.

---

### 6. Draft ADR-022 — per-project / per-agent policy

**Labels:** `documentation`, `adr`

Defines `.annulus/config.yaml` as a project policy overlay — the first code path
to actually read this file (currently only aspirational prose in ADR-012). Owns
ADR-019/ADR-020's project-scoped settings.

---

### 7. Draft ADR-023 — provenance & evaluation data model

**Labels:** `documentation`, `adr`

Separates provenance (durable, untruncated, replayable record) from observability
traces. First slice is wiring `parent_span_id` through `AgentRuntime` spans.
Relates to #40.

---

### 8. Draft ADR-024 — scientific workload primitives

**Labels:** `documentation`, `adr`

Scopes a non-blocking, read-only spike (`read_notebook` tool + non-code chunking)
to validate the tool/skill/chunker primitives against a non-SWE workload before
they ossify around code-only assumptions.

---

### 9. ADR process hygiene — template + vision.md Status column

**Labels:** `documentation`, `adr`

Adds `docs/architecture/adr-template.md` (Status/Context/Decision/Consequences/
Open questions/References) and a Status column (Accepted/Proposed) to
`vision.md`'s Related ADRs table so proposed-vs-accepted is visible at a glance.

---

## Implementation issues

### 1. Enforce `ToolsConfig.allowed_commands` in `ToolExecutor`

**Labels:** `enhancement`, `v0.4`

`allowed_commands` is defined (`config.py:59-61`, `default.yaml:56-59`) but never
read — `executor.py:53` hardcodes `rg` directly. Small, low-risk fix; first
concrete slice of ADR-019's capability model.

---

### 2. Wire `parent_span_id` through `AgentRuntime` spans

**Labels:** `enhancement`, `v0.4`

Closes/relates **#40**. Schema and `build_span_tree` already support nesting
(`store.py`); every span call site (`agent.py`, `chat.py`) currently passes only
`trace_id`. Unblocks ADR-023 provenance and ADR-008 multi-agent trace nesting.

---

### 3. Minimal tool-call approval gate for apply-mode tools

**Labels:** `enhancement`, `v0.4`

Related to **#31–33**. Smallest slice of ADR-019/ADR-021 needed before
`propose_edit`'s optional apply path ships. Propose-mode default (ADR-015) is
unaffected — recommend this merges before or alongside `propose_edit`'s apply
mode, not after.

---

### 4. Router egress policy check before escalation

**Labels:** `enhancement`, `v0.5`

Implements ADR-020's `egress` field and `EscalationPolicy` gate. Default
`allowed` preserves current behavior on upgrade.

---

### 5. `.annulus/config.yaml` per-project policy loader

**Labels:** `enhancement`, `v0.5`

Implements ADR-022's config overlay. Minimal `egress` / `default_capabilities`
fields first; skills/agents/provenance fields deferred to a later schema
version.

---

### 6. Provenance record store + eval-export format

**Labels:** `enhancement`, `v0.5`

Implements ADR-023's untruncated provenance store, separate from `traces.db`.
Feeds ADR-015's already-Proposed v0.4-C eval runbook.

---

### 7. Scientific primitive spike: notebook read tool + non-code chunking

**Labels:** `enhancement`, `spike`, `v0.5`

Implements ADR-024's first validation: read-only `read_notebook` tool + non-code
chunking, packaged as an ADR-017 skill. No execution capability.

---

### 8. Plan-before-act approve/modify/reject flow

**Labels:** `enhancement`, `v0.7`

Implements ADR-021's plan object and CLI/gateway surfacing. Gates autonomous
apply-mode work and is a hard prerequisite before v0.7 swarms.

---

### 9. Agent config object + `AgentRuntime` role binding

**Labels:** `enhancement`, `v0.7`

Implements ADR-018's `AgentConfig`. Prerequisite for ADR-008 swarm
orchestration.

---

### 10. Skill loader (`.annulus/skills/*.yaml`)

**Labels:** `enhancement`, `v0.7`

Implements ADR-017's loader and tool-allowlist merge into `AgentRuntime`.

---

## Cross-links to existing issues

- **#40** (`parent_span_id` nested spans) ↔ Implementation issue 2 + ADR-023.
- **#50** (OpenAPI/Pydantic for chat) ↔ already tracked via ADR-016's
  client-contract sequencing; no new ADR needed. Cross-referenced from ADR-023
  (future provenance client surface).
- **#51** (`GET /v1/index/status`, `GET /v1/traces/{trace_id}`) ↔ same as #50.
- **#31–33** (`propose_edit` / hybrid retrieval) ↔ Implementation issue 3 +
  ADR-019/ADR-021 — recommend issue 3 merges before or alongside
  `propose_edit`'s apply mode.
