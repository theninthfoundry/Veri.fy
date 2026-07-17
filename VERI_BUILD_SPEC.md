# VERI — Runtime Intelligence Engine
## Corrected Architecture & Complete Build Specification (v2)

> **How to use this document with an agentic coding IDE (Antigravity, Claude Code, etc.):**
> This spec is written in build order. Feed it one phase at a time as a task prompt — each phase section
> is self-contained with file manifest, schema, and acceptance criteria. Do not ask the agent to build
> Phase 2 before Phase 1's acceptance criteria pass. The "Agent Task Prompt" block at the start of each
> phase can be pasted directly as the instruction.

---

## 0. What changed from v1, and why

The original design had a real diagnosis (event-log dashboards are commodity) but three load-bearing
flaws that would have broken it in production:

| Flaw in v1 | Fix in v2 |
|---|---|
| "Causal Engine" traversed a graph that was never proven to reflect real influence | **Measured dataflow provenance**: the SDK tags values at the source and tracks them as they flow into later prompts/calls, so `depends_on` edges are facts, not guesses |
| `confidence`/`uncertainty` were free-floating numbers with no defined source | **Confidence provenance wrapper**: every score is tagged `measured / self_reported / derived / unavailable`, so nothing downstream silently trusts a hallucinated number |
| Closed enums (`NodeKind`, `OptimizationType`...) would need a schema migration within 2 quarters | **Capability tags**: open string `kind` for humans, small set of composable capability flags for engines to pattern-match on |
| "Causal chain" and "counterfactual" were narrative templates, not computations | **Two-tier attribution**: real counterfactual replay (ablation) where sessions are replayable; explicitly-labeled structural heuristic elsewhere |
| "LLVM of AI agents" moat claimed a network effect that doesn't exist without third-party adoption | **Honest moat**: correctness of per-framework instrumentation + a working replay engine + an accumulated failure-pattern library — earnable by 2 people, not dependent on ecosystem buy-in |
| Phase 1 timeline (3 weeks) bundled ~7-9 weeks of real work for a 2-engineer team | **Re-scoped phases** below, sized against a stated team, with the graph UI deliberately deferred behind the data model |

---

## 1. Corrected Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 6: SURFACES          Dashboard · CLI · API clients · Alerts       │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 5: INTELLIGENCE APIs  Explain() Predict() Replay() Diff() Optimize()│
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 4: REASONING ENGINES                                              │
│   ┌────────────┐ ┌────────────┐ ┌───────────────┐ ┌──────────────────┐  │
│   │  Causal    │ │ Prediction │ │  Optimization │ │  Session Diff     │  │
│   │  Engine    │ │  Engine    │ │   Compiler    │ │  (graph edit dist)│  │
│   │ (2-tier)   │ │ (heuristic │ │  (static pass)│ │                   │  │
│   │            │ │  → hybrid) │ │               │ │                   │  │
│   └─────┬──────┘ └─────┬──────┘ └──────┬────────┘ └────────┬──────────┘  │
│         └──────────────┴───────────────┴───────────────────┘             │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 3: REPLAY ENGINE  (deterministic re-execution + single-node       │
│           ablation — this is the flagship, not a Phase-4 stretch goal)  │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 2: RUNTIME IR                                                     │
│   Nodes (kind: string, capabilities: tag[], confidence: Confidence)      │
│   Edges (measured dataflow deps + inferred fallback, each labeled)       │
├──────────────────────────────────────────────────────────────────────────┤
│  Layer 1: PERCEPTION — Python/JS SDK with IRRef dataflow tagging         │
│           auto-patches OpenAI/Anthropic/LangChain call sites             │
├──────────────────────────────────────────────────────────────────────────┤
│  STORAGE — PostgreSQL (nodes, edges, deltas, predictions, replay cache)  │
│  Redis (job queue, live pub/sub)                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Five Core Innovations (build these first — everything else depends on them)

### 2.1 Dataflow Provenance via `IRRef` Tagging

The single most important mechanism in this system. Instead of inferring relationships between
nodes after the fact (fragile, statistical), the SDK tags every value returned from a tracked
call and detects when that tagged value is later used.

```python
# packages/sdk-python/veri/ir_ref.py

class IRRef:
    """
    A transparent wrapper around any value returned from a tracked SDK call.
    Behaves like the underlying value (str, dict, list) for all normal usage,
    but carries its origin node_id. When an IRRef — or something built from
    one — is passed into another tracked call, the SDK detects the tag and
    emits a MEASURED depends_on edge automatically. No similarity threshold,
    no timestamp guessing.
    """
    __slots__ = ("_value", "_source_node_id", "_source_field")

    def __init__(self, value, source_node_id: str, source_field: str = "content"):
        self._value = value
        self._source_node_id = source_node_id
        self._source_field = source_field

    def __getattr__(self, name):
        return getattr(self._value, name)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    # Arithmetic/container dunder passthroughs so IRRef(dict) or IRRef(list)
    # behave transparently in f-strings, json.dumps, prompt interpolation, etc.
    def __getitem__(self, key):
        result = self._value[key]
        return IRRef(result, self._source_node_id, f"{self._source_field}.{key}")

    def unwrap(self):
        return self._value


def extract_refs(*args, **kwargs) -> list[tuple[str, str]]:
    """
    Walks arguments passed into a tracked call (prompt strings, tool args,
    kwargs dicts) and finds any IRRef instances or IRRef fragments embedded
    in f-strings via a lightweight sentinel-token scheme, returning
    [(source_node_id, source_field), ...]. This is what generates a
    MEASURED depends_on edge, as opposed to an INFERRED one.
    """
    refs = []
    def walk(x):
        if isinstance(x, IRRef):
            refs.append((x._source_node_id, x._source_field))
        elif isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x: walk(v)
    for a in args: walk(a)
    for v in kwargs.values(): walk(v)
    return refs
```

**Edge emission rule:**

```python
# When session.reasoning(), session.decision(), session.action() etc. are called,
# the SDK inspects its own inputs for IRRef tags BEFORE executing the wrapped call.

edge = {
    "source": ref_node_id,
    "target": new_node.id,
    "kind": "depends_on",
    "confidence_source": "measured",   # <-- this is the fix over v1
}
```

For values that cross an instrumentation boundary you don't control (raw string concatenation
that drops the wrapper, an untyped third-party dict), fall back to content-overlap similarity —
but the resulting edge is tagged `confidence_source: "inferred"` and the UI must visually
distinguish measured vs. inferred edges (solid vs. dashed line). **Never silently upgrade an
inferred edge to look like a measured one.**

### 2.2 Confidence Provenance

```typescript
// packages/runtime-ir/src/confidence.ts

export interface Confidence {
  value: number;                 // 0.0–1.0
  source: 'measured' | 'self_reported' | 'derived' | 'unavailable';
  method?: string;               // 'retrieval_cosine_sim' | 'llm_logprob' |
                                  // 'self_consistency_k5' | 'reranker_score'
}

// Rules enforced by validation.ts at ingest time:
// - retrieval/knowledge nodes MUST supply source: 'measured' with a method,
//   or the ingest API rejects the node (forces SDKs to do this right)
// - LLM decision/reasoning nodes default to 'self_reported' unless the SDK
//   ran self-consistency sampling or the provider exposed logprobs
// - Prediction Engine discounts 'self_reported' confidence by a fixed
//   calibration factor (configurable, default 0.7x) before using it in
//   any heuristic — self-reported LLM confidence is known to be miscalibrated
```

### 2.3 Capability Tags (replaces closed enums)

```typescript
// packages/runtime-ir/src/types.ts

export interface RuntimeNode {
  id: string;
  kind: string;                        // open string for display: "reasoning", "tool_call", etc.
  capabilities: Capability[];          // what engines can DO with this node — this is what's matched on
  label: string;
  content: Record<string, unknown>;
  confidence?: Confidence;
  cost: number;
  latency: number;
  timestamp: string;
  agentId: string;
  sessionId: string;
  projectId: string;
}

export type Capability =
  | 'has_dataflow_deps'      // participates in depends_on edges
  | 'is_decision_point'      // a branch/choice was made here
  | 'has_measurable_confidence'
  | 'is_replayable'          // deterministic + cacheable → ablation engine can use it
  | 'affects_cost'
  | 'is_terminal'            // session/goal end state
  | 'is_error';

// Engines pattern-match on capabilities:
//   causalEngine.findCandidates(nodes) => nodes.filter(n => n.capabilities.includes('is_replayable'))
// A brand-new framework emitting an unanticipated `kind` string still gets
// analyzed correctly as long as its SDK adapter tags the right capabilities.
// This removes the recurring schema-migration tax closed enums impose.
```

### 2.4 Two-Tier Causal Engine

```typescript
// apps/dashboard/src/lib/engines/causal-engine.ts

export interface CausalFinding {
  candidateNodeId: string;
  method: 'ablation' | 'structural_heuristic';   // NEVER hidden from the user
  score: number;                                   // 0.0–1.0
  explanation: string;
}

/**
 * TIER 1 — Real counterfactual replay.
 * Only runs on nodes tagged `is_replayable` (deterministic tool calls,
 * cached retrieval results, anything the Replay Engine can re-execute
 * with a substituted value).
 */
export async function ablationScore(
  session: SessionHandle,
  failureNodeId: string,
  candidateNodeId: string
): Promise<CausalFinding> {
  const baseline = await replayEngine.run(session, { upto: failureNodeId });
  const perturbed = await replayEngine.run(session, {
    upto: failureNodeId,
    override: { [candidateNodeId]: replayEngine.nullOrAltValue(candidateNodeId) },
  });
  const stillFails = failureSignatureMatches(perturbed, baseline);
  return {
    candidateNodeId,
    method: 'ablation',
    score: stillFails ? 0.0 : 1.0,
    explanation: stillFails
      ? `Perturbing this node's output did not change the outcome — not the cause.`
      : `Perturbing this node's output prevented the failure — likely cause.`,
  };
}

/**
 * TIER 2 — Structural heuristic fallback for non-replayable nodes
 * (nondeterministic LLM sampling, side-effecting external calls).
 * Explicitly labeled so the UI never presents this as measured.
 */
export function structuralHeuristicScore(
  failureNode: RuntimeNode,
  candidateNode: RuntimeNode,
  pathDistance: number
): CausalFinding {
  const confidenceAtUse = candidateNode.confidence?.value ?? 0.5;
  const score = (1 / (1 + pathDistance)) * (1 - confidenceAtUse) * (candidateNode.confidence?.source === 'measured' ? 1 : 0.6);
  return {
    candidateNodeId: candidateNode.id,
    method: 'structural_heuristic',
    score,
    explanation: `Estimated (not measured) contribution based on graph distance and confidence at time of use.`,
  };
}

export async function analyzeCausality(session: SessionHandle, failureNodeId: string): Promise<CausalFinding[]> {
  const candidates = getUpstreamCandidates(session, failureNodeId); // via depends_on edges
  const findings: CausalFinding[] = [];
  for (const c of candidates) {
    findings.push(
      c.capabilities.includes('is_replayable')
        ? await ablationScore(session, failureNodeId, c.id)
        : structuralHeuristicScore(getNode(failureNodeId), c, pathDistanceBetween(c.id, failureNodeId))
    );
  }
  return findings.sort((a, b) => b.score - a.score);
}
```

### 2.5 Replay Engine (flagship — build in Phase 2, not deferred to Month 6)

```typescript
// apps/dashboard/src/lib/engines/replay-engine.ts

export interface ReplayOptions {
  upto: string;                              // node id to replay to
  override?: Record<string, unknown>;        // nodeId -> substituted value
}

/**
 * Re-executes the deterministic portion of a session's dependency graph.
 * Requires that replayable nodes (tool calls, retrieval) have their
 * inputs/outputs cached at ingest time (see `replay_cache` table).
 * Nondeterministic nodes (raw LLM sampling) are replayed by replaying
 * the cached output UNLESS they are the override target, in which case
 * downstream nodes are recomputed with the substituted value threaded
 * through via the same IRRef mechanism used at record time.
 */
export async function run(session: SessionHandle, opts: ReplayOptions) {
  const dag = topologicalSort(session.nodes, session.edges);
  const values = new Map<string, unknown>();
  for (const node of dag) {
    if (node.id === opts.override?.[node.id]) {
      values.set(node.id, opts.override[node.id]);
      continue;
    }
    if (!node.capabilities.includes('is_replayable')) {
      values.set(node.id, getCachedOutput(node.id)); // replay cached, not re-run
      continue;
    }
    const inputs = getDependencyValues(node, values);
    values.set(node.id, await reExecute(node, inputs));
    if (node.id === opts.upto) break;
  }
  return values;
}
```

This is also what powers **session diffing** (graph edit distance between two runs' dependency
graphs, pinpointing exactly which decision node diverged and what upstream data changed) —
a feature no competitor in this space currently has, because it requires typed, measured
dependency edges to diff against.

---

## 3. Corrected Database Schema (additions/changes only — rest as originally specified)

```sql
-- Confidence is now a structured sub-object, not a bare float
ALTER TABLE runtime_nodes
    ADD COLUMN confidence_value REAL,
    ADD COLUMN confidence_source TEXT CHECK (confidence_source IN ('measured','self_reported','derived','unavailable')),
    ADD COLUMN confidence_method TEXT,
    ADD COLUMN capabilities TEXT[] DEFAULT '{}';   -- replaces reliance on closed `kind` enum

-- Edges now carry provenance of the relationship itself
ALTER TABLE runtime_edges
    ADD COLUMN edge_confidence_source TEXT NOT NULL DEFAULT 'inferred'
        CHECK (edge_confidence_source IN ('measured','inferred'));

-- New: cache for replay engine (Tier 1 causal analysis depends on this)
CREATE TABLE replay_cache (
    node_id TEXT PRIMARY KEY REFERENCES runtime_nodes(id),
    input_snapshot JSONB NOT NULL,
    output_snapshot JSONB NOT NULL,
    deterministic BOOLEAN NOT NULL DEFAULT false,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- New: causal findings persisted with method transparency
CREATE TABLE causal_findings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    failure_node_id TEXT NOT NULL,
    candidate_node_id TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('ablation','structural_heuristic')),
    score REAL NOT NULL,
    explanation TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- New: session diff results
CREATE TABLE session_diffs (
    id TEXT PRIMARY KEY,
    session_a_id TEXT NOT NULL,
    session_b_id TEXT NOT NULL,
    divergence_node_id TEXT,              -- first node where dependency graphs diverge
    edit_distance REAL NOT NULL,
    diff_summary JSONB NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 4. Repository Structure (delta from v1 — new/changed paths only)

```
veri/
├── packages/
│   ├── runtime-ir/
│   │   └── src/
│   │       ├── confidence.ts            # NEW — Confidence provenance types
│   │       ├── capabilities.ts          # NEW — Capability tag definitions
│   │       └── types.ts                 # CHANGED — open `kind`, capability array
│   │
│   └── sdk-python/veri/
│       ├── ir_ref.py                    # NEW — IRRef dataflow tagging (2.1)
│       └── replay_cache.py              # NEW — records input/output snapshots
│
├── apps/dashboard/src/lib/engines/
│   ├── causal-engine.ts                 # REWRITTEN — two-tier (2.4)
│   ├── replay-engine.ts                 # NEW, moved up from Phase 4 (2.5)
│   ├── session-diff.ts                  # NEW — graph edit distance
│   └── confidence-calibration.ts        # NEW — discount factors per source type
│
├── apps/dashboard/src/components/
│   ├── graph/
│   │   └── ir-edge.tsx                  # CHANGED — solid (measured) vs dashed (inferred)
│   └── intelligence/
│       ├── causal-chain.tsx             # CHANGED — shows method badge per finding
│       └── session-diff-view.tsx        # NEW
```

---

## 5. Realistic Phased Plan — sized for **2 senior engineers + 1 part-time PM/designer**

### Phase 1 — "The Provenance Trace" (Weeks 1–4)

**Agent Task Prompt (paste this to start):**
> Scaffold a pnpm/Turborepo monorepo per the structure in Section 4 plus the original v1 structure.
> Set up Docker Compose (Postgres 16 + Redis 7). Implement `packages/runtime-ir` with the corrected
> `types.ts` (open `kind`, `capabilities[]`, `Confidence` object) from Sections 2.2–2.3. Implement the
> ingest API (`POST /api/v1/ingest`) with validation that REJECTS any node claiming
> `confidence_source: 'measured'` without a `method` field. Implement `packages/sdk-python` with the
> `IRRef` class and `extract_refs()` from Section 2.1, wired into `session.reasoning()`,
> `session.action()`, `session.knowledge()`, `session.decision()` context managers so that passing
> a prior step's tagged return value into a new tracked call automatically emits a
> `depends_on` edge with `edge_confidence_source: 'measured'`. Build a plain dashboard: agent list,
> session list, filterable node table (NOT the graph visualization yet). Do not build the React Flow
> graph UI in this phase.

| Week | Deliverable | Why deferred/reordered vs v1 |
|---|---|---|
| 1 | Monorepo, Docker, DB schema incl. Section 3 additions, CI | unchanged from v1 |
| 2 | Runtime IR package + ingest API with confidence/capability validation | moved earlier — this is the correctness backbone |
| 3 | Python SDK with `IRRef` tagging wired through 4 core context managers | new, and the highest-value week in the whole plan |
| 4 | Dashboard shell + plain node table + session list (no graph canvas) | graph UI deliberately deferred — prove the data model first |

**Acceptance criteria**: Instrument one real LangGraph or raw-OpenAI agent. Confirm that a value
retrieved in one step and interpolated into a later prompt produces a `measured` `depends_on` edge
in the node table — not just two nodes with close timestamps.

### Phase 2 — "The Replay Debugger" (Weeks 5–9)

**Agent Task Prompt:**
> Implement the Replay Engine (Section 2.5): `replay_cache` table population at ingest time for any
> node tagged `is_replayable`, and the `run()` function supporting `upto` and `override`. Implement
> the two-tier Causal Engine (Section 2.4): ablation scoring for replayable candidates, structural
> heuristic fallback for non-replayable ones, with `method` always persisted and surfaced in the API
> response — never blend the two into a single unlabeled number. Add the four Day-1 prediction
> heuristics from the original design (loop detection, confidence degradation, cost anomaly, memory
> staleness), but discount any `self_reported` confidence value by the calibration factor from
> `confidence-calibration.ts` before using it in a heuristic. Build the causal-chain UI component
> showing a method badge (⚡ Measured replay / ~ Estimated) next to every finding.

| Week | Deliverable |
|---|---|
| 5 | `replay_cache` write path + `replay-engine.ts` `run()` with override support |
| 6 | Two-tier causal engine + persistence to `causal_findings` |
| 7 | Four heuristic predictors, wired through confidence calibration |
| 8 | Intelligence Graph UI (React Flow) — now that the data model is proven, this is safe to build |
| 9 | Causal chain UI with method transparency; integration test: inject a stale-memory bug, verify Tier-1 ablation identifies it correctly (not just plausibly) |

**Acceptance criteria**: Deliberately inject a reproducible failure (stale cached retrieval value).
Verify the Causal Engine's Tier-1 ablation run correctly identifies the injected node as the cause
with `method: 'ablation'`, not a heuristic guess.

### Phase 3 — "Production Ready + Session Diff" (Weeks 10–14)

- JS/TS SDK with the same `IRRef` mechanism
- Auth, API keys, onboarding
- **Session diffing** (Section 2.5 payoff): graph edit distance between two sessions' dependency
  graphs, pinpointing first divergent decision node
- Auto-instrumentation adapters for LangChain, CrewAI (each is its own multi-day effort — budget
  3-4 days per framework adapter, they will not be uniform)
- Optimization compiler static passes (redundant reasoning, unnecessary retrieval) — this part of
  v1 was fine as designed, port as-is

### Phase 4 — Months 4–8 — "Bayesian layer + cross-session learning"

Only attempt once Phase 1–3 have real usage data. Do not build Bayesian/ML prediction on
synthetic data — it will overfit to your own test fixtures and be wrong on real traffic.

---

## 6. Honest Moat (revised)

| Claim | Status |
|---|---|
| "Universal IR / LLVM of AI agents" | **Not yet true** — requires third-party frameworks to adopt it voluntarily. Don't claim this until you have ≥2 external integrations you don't control. |
| "Measured dataflow provenance, not inferred correlation" | **True and defensible** — this is real, ongoing instrumentation work per framework that's genuinely tedious to replicate correctly |
| "Real counterfactual replay for agent failures" | **True and defensible, and currently undifferentiated in the market** — build this as your primary demo |
| "Cross-customer learning flywheel" | **Not yet true** — requires volume you don't have at launch. Don't lead with it. |

---

## 7. Verification Plan

- Unit: `vitest` for TS engines, `pytest` for `IRRef` + `extract_refs` (test that nested
  dict/list wrapping still detects tagged refs correctly — this is the part most likely to have subtle bugs)
- Integration: instrument a real agent → inject one deterministic bug (stale cache value) →
  assert Tier-1 ablation names it correctly, with `method: 'ablation'`
- Integration: run the same agent twice with one upstream value changed → assert session-diff
  correctly identifies the first divergent node
- Manual: have someone unfamiliar with the codebase read a causal-chain UI output and confirm
  they can tell, without asking, whether a given finding was measured or estimated — if the
  method badge isn't self-explanatory, the UI has failed the transparency requirement in Section 2.4
