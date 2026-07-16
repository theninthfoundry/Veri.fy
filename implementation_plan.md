# VERI: Runtime Intelligence Engine — The Category-Defining Architecture

## Why The Previous Architecture Was Wrong

The previous architecture was **excellent infrastructure engineering**. It was also a **reproducible product**.

Any well-funded team (LangSmith, Arize, Datadog) could build:
- Event ingestion → ClickHouse → Dashboard → Graphs

That's not a moat. That's a feature.

The critique is correct on every point. The core problem:

| Previous VERI | What VERI Must Become |
|---|---|
| Events → Database → Analytics → Visualization | Reality → Intent → Execution → Prediction → Optimization → Learning |
| Workflow graph | Intelligence graph (beliefs, intent, causality, unknowns, conflicts) |
| "What happened?" | "Why did this happen, what will happen next, and how do we prevent it?" |
| Stores everything | Stores semantic deltas (knowledge compression) |
| Framework-specific traces | Universal Runtime IR (LLVM for AI) |
| Passive observation | Adaptive runtime that rewrites itself |
| Rule-based predictions | Hybrid reasoning (Bayesian + graph + temporal + LLM) |
| Event replay | Counterfactual simulation ("what if?") |

The moat isn't the database, the dashboard, or the SDK. The moat is:

1. **Runtime IR** — A universal representation that every agent framework compiles into
2. **Reality Graph** — A continuously updating world model, not a log of events
3. **Hybrid Reasoning Engine** — Symbolic + probabilistic + neural explanation
4. **Optimization Compiler** — Automatically improves agent execution
5. **Cross-customer Learning** — Gets smarter with every connected agent (privacy-preserving)

---

## The Architecture That Defines a Category

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          VERI ARCHITECTURE                              │
│                    Runtime Intelligence Engine                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 7: VISUALIZATION + INTERACTION                                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Dashboard    CLI    API Clients    IDE Plugins    Alerts         │  │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │                                          │
│  Layer 6: INTELLIGENCE APIs                                             │
│  ┌───────────────────────────┴───────────────────────────────────────┐  │
│  │  Understand()  Predict()  Explain()  Simulate()  Optimize()      │  │
│  │  Compare()     Search()   Replay()   Adapt()     Verify()        │  │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │                                          │
│  Layer 5: REASONING ENGINES                                             │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Causal │  │ Intent │  │ Policy │  │Prediction│  │  Simulation  │  │
│  │ Engine │  │ Engine │  │ Engine │  │  Engine   │  │    Engine    │  │
│  └───┬────┘  └───┬────┘  └───┬────┘  └────┬─────┘  └──────┬───────┘  │
│      └───────────┴───────────┴─────────────┴───────────────┘           │
│                              │                                          │
│  Layer 4: STATE ENGINE                                                  │
│  ┌───────────────────────────┴───────────────────────────────────────┐  │
│  │  Reality Graph  │  Intent Graph  │  Temporal Engine  │  Constraints│ │
│  │  (world state)  │  (who wants    │  (past/present/   │  (physics,  │ │
│  │                 │   what & why)  │   future states)  │   budgets)  │ │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │                                          │
│  Layer 3: RUNTIME OPTIMIZATION COMPILER                                 │
│  ┌───────────────────────────┴───────────────────────────────────────┐  │
│  │  Parse IR → Analyze → Optimize → Compress → Emit Improved IR     │  │
│  │  (remove redundant reasoning, merge tool calls, optimize prompts) │  │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │                                          │
│  Layer 2: RUNTIME IR (Universal Runtime Representation)                 │
│  ┌───────────────────────────┴───────────────────────────────────────┐  │
│  │  Every agent framework compiles into this intermediate form        │  │
│  │  Nodes: Intent, Belief, Observation, Decision, Action, Outcome    │  │
│  │  Edges: causes, depends_on, conflicts_with, updates, constrains   │  │
│  │  Metadata: confidence, uncertainty, cost, latency, risk           │  │
│  └───────────────────────────┬───────────────────────────────────────┘  │
│                              │                                          │
│  Layer 1: PERCEPTION (SDKs + Adapters)                                  │
│  ┌───────────────────────────┴───────────────────────────────────────┐  │
│  │  Python SDK    JS SDK    OTel Adapter    LangChain    CrewAI      │  │
│  │  (auto-instruments frameworks, emits Runtime IR)                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  STORAGE LAYER (beneath everything)                                     │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  State Store     │  Delta Store      │  Model Store               │  │
│  │  (current world) │  (semantic deltas) │  (learned patterns)       │  │
│  │  (PostgreSQL)    │  (PostgreSQL)      │  (PostgreSQL + Redis)     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  LEARNING LAYER (continuous improvement)                                │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Pattern Learning    Failure Models    Optimization Models         │  │
│  │  (every execution improves the system)                             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Seven Breakthroughs That Make VERI Uncopyable

### Breakthrough 1: Runtime IR (The LLVM of AI Agents)

Every agent framework today speaks a different language:
- LangChain emits "runs" with "callbacks"
- CrewAI emits "tasks" with "agent delegation"  
- AutoGen emits "messages" between "agents"
- Custom agents emit whatever the developer decided

**VERI Runtime IR** is a universal intermediate representation that every framework compiles into. Like LLVM IR lets compilers target any hardware, VERI IR lets intelligence engines reason about any agent.

```typescript
// packages/runtime-ir/src/types.ts

/**
 * A RuntimeNode is the atomic unit of the Runtime IR.
 * Everything an agent does, thinks, or observes becomes a node.
 * 
 * Unlike events (which are logs), nodes are SEMANTIC UNITS
 * with typed relationships, confidence, and uncertainty.
 */
export interface RuntimeNode {
  id: string;                           // ULID
  kind: NodeKind;                       // What this node represents
  
  // Content
  label: string;                        // Human-readable: "Search for flights"
  content: Record<string, unknown>;     // Structured payload
  
  // Epistemic state (what does the agent KNOW about this?)
  confidence: number;                   // 0.0–1.0: How sure is the agent?
  uncertainty: number;                  // 0.0–1.0: How much is unknown?
  evidence: string[];                   // What supports this node?
  assumptions: string[];               // What was assumed without evidence?
  
  // Resource tracking
  cost: number;                         // USD cost of this node
  latency: number;                      // ms duration
  tokens: { input: number; output: number; };
  
  // Temporal
  timestamp: string;                    // When this node was created
  duration?: number;                    // How long this node was active
  
  // Context
  agentId: string;
  sessionId: string;
  projectId: string;
}

/**
 * NodeKind defines WHAT the node represents.
 * This is NOT a log category. It's a semantic type
 * that the reasoning engines understand.
 */
export type NodeKind =
  // Intentional (what the agent WANTS)
  | 'intent'              // Top-level goal or desire
  | 'subgoal'             // Decomposed sub-goal
  | 'plan'                // Sequence of planned actions
  
  // Epistemic (what the agent BELIEVES)
  | 'belief'              // Something the agent holds as true
  | 'observation'         // Something the agent perceived
  | 'knowledge'           // Verified fact from retrieval
  | 'assumption'          // Unverified belief
  | 'conflict'            // Two beliefs that contradict
  | 'unknown'             // Recognized gap in knowledge
  
  // Cognitive (what the agent THINKS)
  | 'reasoning'           // A step of reasoning
  | 'decision'            // A choice between alternatives
  | 'reflection'          // Self-evaluation of past action
  | 'learning'            // Updated understanding from experience
  
  // Operational (what the agent DOES)
  | 'action'              // An executed action (tool call, API, etc.)
  | 'tool_invocation'     // Specific tool usage
  | 'llm_call'            // LLM inference call
  | 'delegation'          // Delegated work to another agent
  
  // Environmental (what the WORLD is)
  | 'world_state'         // Snapshot of relevant world state
  | 'constraint'          // A physical/logical/policy constraint
  | 'resource'            // Available resource (compute, budget, time)
  
  // Evaluative (how things WENT)
  | 'outcome'             // Result of an action
  | 'error'               // Something went wrong
  | 'risk'                // Detected risk signal
  | 'anomaly';            // Deviation from expected pattern

/**
 * RuntimeEdge connects two nodes with a TYPED relationship.
 * Edges carry meaning — they're not just "parent/child."
 */
export interface RuntimeEdge {
  id: string;
  source: string;                      // Source node ID
  target: string;                      // Target node ID
  kind: EdgeKind;                      // Relationship type
  weight?: number;                     // 0.0–1.0: strength of relationship
  metadata?: Record<string, unknown>;
}

export type EdgeKind =
  | 'causes'              // A caused B
  | 'caused_by'           // A was caused by B
  | 'depends_on'          // A requires B
  | 'enables'             // A makes B possible
  | 'conflicts_with'      // A contradicts B
  | 'updates'             // A is an updated version of B
  | 'constrains'          // A limits what B can do
  | 'supports'            // A provides evidence for B
  | 'refutes'             // A provides evidence against B
  | 'decomposes_into'     // A breaks down into B
  | 'delegates_to'        // A assigns work to B
  | 'learns_from'         // A's understanding changed because of B
  | 'predicts'            // A predicts B will happen
  | 'optimizes'           // A is an improved version of B
  | 'observes'            // A observed B in the environment
  | 'assumes'             // A assumed B without verification
  | 'reflects_on';        // A is a reflection about B

/**
 * A RuntimeFrame is a complete snapshot of an agent's state at a moment.
 * It contains all active nodes and edges — the agent's "mental state."
 * 
 * Frames are the unit of temporal reasoning:
 * Past Frame → Current Frame → Predicted Future Frame
 */
export interface RuntimeFrame {
  id: string;
  sessionId: string;
  agentId: string;
  timestamp: string;
  
  // Active state
  activeGoals: string[];               // Currently active intent nodes
  activeBeliefs: string[];             // Current belief set
  activePlan: string[];                // Current plan sequence
  workingMemory: string[];             // Nodes in working memory
  
  // Metrics snapshot
  totalCost: number;
  totalLatency: number;
  overallConfidence: number;
  overallRisk: number;
  
  // Delta from previous frame
  nodesAdded: string[];
  nodesRemoved: string[];
  beliefsChanged: string[];
  confidenceDeltas: Record<string, number>;  // nodeId → change
}
```

> [!IMPORTANT]
> **Why this is a moat**: Every reasoning engine, optimizer, and predictor in VERI operates on Runtime IR. Once developers instrument their agents with VERI, their runtime data exists in this universal format. The more frameworks that compile to VERI IR, the stronger the network effect. This is the LLVM strategy — own the intermediate representation, and everything above and below becomes dependent on you.

---

### Breakthrough 2: Reality Graph (Not Event Graph)

The previous architecture stored **events** — things that happened. The Reality Graph stores **state** — what the world IS.

```typescript
// packages/runtime-ir/src/reality.ts

/**
 * The Reality Graph is a continuously updating model of
 * everything relevant to the agent's operation.
 * 
 * Unlike an event log (append-only, grows forever),
 * the Reality Graph is a LIVING DOCUMENT that:
 * - Updates when observations change
 * - Tracks confidence in each belief
 * - Detects conflicts between beliefs
 * - Ages out stale knowledge
 * - Predicts future states
 */
export interface RealityGraph {
  entities: RealityEntity[];           // Things that exist
  relationships: RealityRelationship[]; // How things relate
  constraints: RealityConstraint[];    // What's physically/logically possible
  snapshot_at: string;                 // When this snapshot was taken
}

export interface RealityEntity {
  id: string;
  type: string;                        // "robot", "warehouse", "user", "api", "budget"
  properties: Record<string, unknown>; // Current known properties
  confidence: number;                  // How sure are we this is accurate?
  last_observed: string;               // When was this last confirmed?
  staleness: number;                   // 0.0–1.0: how stale is this knowledge?
  source: string;                      // Where did this knowledge come from?
}

export interface RealityRelationship {
  source: string;                      // Entity ID
  target: string;                      // Entity ID
  type: string;                        // "located_in", "owns", "depends_on"
  confidence: number;
  temporal: boolean;                   // Does this change over time?
}

export interface RealityConstraint {
  id: string;
  type: 'physical' | 'logical' | 'policy' | 'resource' | 'temporal';
  description: string;                 // Human-readable
  expression: string;                  // Machine-evaluable constraint
  priority: number;                    // How hard is this constraint?
  violable: boolean;                   // Can this be violated with consequences?
}
```

**Example**: A robot agent is navigating a warehouse.

| Event Log (Old VERI) | Reality Graph (New VERI) |
|---|---|
| `10:03 tool.executed: move_to(shelf_A)` | Entity: Robot-1 { location: shelf_A, battery: 72%, carrying: null, status: idle } |
| `10:04 tool.executed: pick(item_42)` | Entity: Shelf-A { items: [41, 43, 44], capacity: 94% } |
| `10:05 tool.failed: move_to(dock_3)` | Constraint: Robot cannot move to dock_3 (path blocked by Robot-2) |
| (No understanding of WHY) | Conflict: Robot-1 plan requires dock_3, but dock_3 is occupied for next 4 minutes |

---

### Breakthrough 3: Intent Engine

Every execution involves multiple **intents** that can align or conflict:

```typescript
// apps/dashboard/src/lib/engines/intent-engine.ts

/**
 * The Intent Engine tracks what every stakeholder WANTS
 * and detects misalignment between intents.
 * 
 * Stakeholders:
 * - The agent (its programmed goal)
 * - The user (what they actually need)
 * - The organization (policies, budgets, compliance)
 * - The environment (physical/logical constraints)
 */
export interface IntentLayer {
  agentIntent: Intent;                 // What the agent is trying to do
  userIntent: Intent;                  // What the user actually wants
  policyIntent: Intent;               // What the organization requires
  environmentConstraints: Constraint[]; // What reality allows
}

export interface Intent {
  goal: string;                        // Natural language goal
  priority: number;                    // How important is this?
  constraints: string[];               // Conditions that must hold
  deadline?: string;                   // When must this complete?
  budget?: number;                     // Max cost allowed
}

export interface IntentAlignment {
  aligned: boolean;                    // Are all intents compatible?
  conflicts: IntentConflict[];         // Where do intents disagree?
  risk: number;                        // Risk of misalignment causing failure
}

export interface IntentConflict {
  between: [string, string];           // Which stakeholders conflict
  description: string;                 // What's the conflict
  severity: 'low' | 'medium' | 'high' | 'critical';
  resolution?: string;                 // Suggested resolution
}
```

**Example**: Agent intent is "book cheapest flight." User intent is "arrive before 9am." Policy intent is "only approved airlines." Environment constraint: "cheapest flight arrives at 11pm."

**Old VERI**: Agent books cheap flight. User is unhappy. Nobody knows why until the complaint.

**New VERI**: Intent Engine detects misalignment BEFORE execution. Dashboard shows: "⚠ Agent intent (cheapest) conflicts with user intent (arrive by 9am). Cheapest option arrives at 11pm. Suggesting: filter by arrival time first."

---

### Breakthrough 4: Causal Engine

Not "A happened then B happened." Instead: "B happened BECAUSE of A, and A happened because of C, and C was caused by a stale memory from 3 hours ago."

```typescript
// apps/dashboard/src/lib/engines/causal-engine.ts

/**
 * The Causal Engine performs root-cause analysis by traversing
 * the causal graph backward from a failure to find the TRUE origin.
 * 
 * It distinguishes between:
 * - Proximate cause (the immediate trigger)
 * - Root cause (the underlying condition)
 * - Contributing factors (things that made it worse)
 * - Environmental conditions (context that enabled the failure)
 */
export interface CausalAnalysis {
  failure: string;                     // The failure node ID
  proximateCause: CausalChain;        // Immediate trigger chain
  rootCause: CausalChain;             // Deep root cause
  contributingFactors: CausalFactor[];
  environmentalConditions: string[];
  counterfactual: string;             // "If X had been different, failure would not have occurred"
  probability: number;                // Confidence in this analysis
  prevention: string;                 // How to prevent recurrence
}

export interface CausalChain {
  nodes: string[];                    // Sequence of node IDs from cause to effect
  explanation: string;                // Natural language explanation
  confidence: number;                 // How confident is this causal chain?
}

export interface CausalFactor {
  nodeId: string;
  contribution: number;              // 0.0–1.0: how much did this contribute?
  explanation: string;
}
```

**Example output**:
```
Failure: Robot dropped item at 10:05

Proximate cause:
  Gripper force was set to 2N (insufficient for 500g item)

Root cause:
  Memory retrieval at 10:02 returned weight data for item_41 (200g)
  instead of item_42 (500g) because embedding similarity was 0.94
  
Contributing factors:
  - Stale inventory data (last updated 6 hours ago) — contribution: 0.4
  - No weight verification step in plan — contribution: 0.3
  - Gripper calibration at lower bound — contribution: 0.3

Counterfactual:
  "If memory had returned correct weight for item_42, gripper force
   would have been set to 5N and the drop would not have occurred"

Prevention:
  "Add weight verification step after memory retrieval.
   Refresh inventory data more frequently (current: 6h, recommended: 1h)"
```

---

### Breakthrough 5: Hybrid Prediction Engine

Not rule-based. Not pure ML. A hybrid that combines four approaches:

```typescript
// apps/dashboard/src/lib/engines/prediction-engine.ts

/**
 * Hybrid Prediction Engine
 * 
 * Combines four reasoning approaches:
 * 1. Graph reasoning — traverse the causal/dependency graph to find risk paths
 * 2. Bayesian inference — update probabilities based on observed evidence
 * 3. Temporal modeling — detect patterns over time (loops, degradation, drift)
 * 4. LLM explanation — generate human-readable explanations from structured reasoning
 * 
 * On Day 1: Only graph reasoning + heuristics (no training data needed)
 * Month 3: Add Bayesian inference (learned from accumulated data)
 * Month 6: Add temporal modeling (enough history to detect patterns)
 * Month 12: Full hybrid with LLM explanations
 */
export interface Prediction {
  id: string;
  sessionId: string;
  type: PredictionType;
  
  // The prediction itself
  probability: number;                 // 0.0–1.0: likelihood
  confidence: number;                  // 0.0–1.0: confidence in the prediction
  horizon: number;                     // Steps ahead this predicts
  
  // Explanation (not just a number)
  explanation: string;                 // "Agent is likely to fail because..."
  evidence: PredictionEvidence[];      // What supports this prediction
  counterfactual: string;              // "If X changes, probability drops to Y"
  
  // Actionable
  suggestedAction?: string;            // "Pause and re-plan" / "Switch tool"
  
  // Provenance
  method: 'graph' | 'bayesian' | 'temporal' | 'hybrid' | 'heuristic';
  model_version: string;
  computed_at: string;
}

export type PredictionType =
  | 'failure'              // Will this session fail?
  | 'hallucination'        // Is the agent confabulating?
  | 'cost_overrun'         // Will cost exceed budget?
  | 'latency_anomaly'      // Is latency abnormal?
  | 'reasoning_loop'       // Is the agent stuck in a loop?
  | 'goal_drift'           // Has the agent drifted from its goal?
  | 'memory_staleness'     // Is the agent using stale knowledge?
  | 'intent_misalignment'  // Do agent and user intents conflict?
  | 'constraint_violation' // Will a constraint be violated?
  | 'deadlock';            // Are multiple agents deadlocked?

export interface PredictionEvidence {
  nodeId: string;                      // Which IR node is evidence
  contribution: number;               // How much does this contribute
  explanation: string;                // Why this is relevant
}
```

#### Day 1 Implementation: Graph Heuristics (No ML Required)

```typescript
// apps/dashboard/src/lib/engines/heuristics.ts

/**
 * Day-1 prediction heuristics that require ZERO training data.
 * These are graph-traversal algorithms over the Runtime IR.
 */

/** Detect reasoning loops */
export function detectReasoningLoop(nodes: RuntimeNode[]): Prediction | null {
  // Find sequences where similar reasoning nodes repeat
  const reasoningNodes = nodes.filter(n => n.kind === 'reasoning');
  
  // Sliding window: check if content similarity > 0.85 within 5-step window
  for (let i = 2; i < reasoningNodes.length; i++) {
    const window = reasoningNodes.slice(Math.max(0, i - 4), i + 1);
    const similarities = computePairwiseSimilarity(window);
    
    if (similarities.some(s => s > 0.85)) {
      return {
        type: 'reasoning_loop',
        probability: 0.78 + (similarities.filter(s => s > 0.85).length * 0.05),
        confidence: 0.7,
        explanation: `Agent has repeated similar reasoning ${similarities.filter(s => s > 0.85).length + 1} times in the last ${window.length} steps. This pattern indicates a reasoning loop.`,
        suggestedAction: 'Pause agent and re-plan with different approach',
        method: 'heuristic',
        // ...
      };
    }
  }
  return null;
}

/** Detect confidence degradation */
export function detectConfidenceDegradation(nodes: RuntimeNode[]): Prediction | null {
  const recent = nodes.slice(-10);
  if (recent.length < 5) return null;
  
  const confidences = recent.map(n => n.confidence).filter(c => c !== undefined);
  if (confidences.length < 3) return null;
  
  // Linear regression on confidence over time
  const slope = linearRegressionSlope(confidences);
  
  if (slope < -0.05) { // Confidence dropping > 5% per step
    const currentConfidence = confidences[confidences.length - 1];
    const stepsToFailure = Math.ceil(currentConfidence / Math.abs(slope));
    
    return {
      type: 'failure',
      probability: Math.min(0.95, 0.5 + Math.abs(slope) * 5),
      confidence: 0.6,
      horizon: stepsToFailure,
      explanation: `Agent confidence has been declining at ${(slope * 100).toFixed(1)}% per step. At this rate, confidence will reach zero in ~${stepsToFailure} steps.`,
      suggestedAction: 'Investigate memory quality and tool outputs',
      method: 'heuristic',
      // ...
    };
  }
  return null;
}

/** Detect cost anomaly */
export function detectCostAnomaly(
  currentSessionCost: number,
  historicalMean: number,
  historicalStd: number,
  budget?: number
): Prediction | null {
  const zScore = (currentSessionCost - historicalMean) / (historicalStd || 1);
  
  if (zScore > 2.0 || (budget && currentSessionCost > budget * 0.8)) {
    return {
      type: 'cost_overrun',
      probability: budget ? currentSessionCost / budget : Math.min(0.9, 0.5 + zScore * 0.1),
      confidence: 0.75,
      explanation: budget
        ? `Session cost ($${currentSessionCost.toFixed(3)}) is at ${((currentSessionCost / budget) * 100).toFixed(0)}% of budget ($${budget})`
        : `Session cost ($${currentSessionCost.toFixed(3)}) is ${zScore.toFixed(1)} standard deviations above the historical mean ($${historicalMean.toFixed(3)})`,
      suggestedAction: 'Review token usage; consider summarization or caching',
      method: 'heuristic',
      // ...
    };
  }
  return null;
}

/** Detect memory staleness */
export function detectMemoryStaleness(nodes: RuntimeNode[]): Prediction | null {
  const memoryNodes = nodes.filter(n => n.kind === 'knowledge' || n.kind === 'observation');
  
  const staleMemories = memoryNodes.filter(n => {
    const ageMs = Date.now() - new Date(n.timestamp).getTime();
    return ageMs > 3600000 && n.confidence > 0.5; // > 1 hour old, still high confidence
  });
  
  if (staleMemories.length > 0) {
    const stalestAge = Math.max(...staleMemories.map(n => 
      Date.now() - new Date(n.timestamp).getTime()
    ));
    
    return {
      type: 'memory_staleness',
      probability: Math.min(0.8, 0.3 + staleMemories.length * 0.1),
      confidence: 0.65,
      explanation: `Agent is relying on ${staleMemories.length} memory items that haven't been refreshed in over ${Math.round(stalestAge / 3600000)} hours. Decisions based on stale data carry higher failure risk.`,
      suggestedAction: 'Refresh memory retrieval before critical decisions',
      method: 'heuristic',
      // ...
    };
  }
  return null;
}
```

---

### Breakthrough 6: Knowledge Compression

Instead of storing every event (grows linearly forever), store **semantic deltas** (grows logarithmically):

```typescript
// apps/dashboard/src/lib/engines/compressor.ts

/**
 * Knowledge Compression Engine
 * 
 * Instead of storing 1000 events, detect the meaningful
 * STATE TRANSITIONS and store only those.
 * 
 * Example:
 *   1000 events → 12 state transitions → 3 semantic deltas
 * 
 * This is NOT lossy compression of data.
 * It's SEMANTIC compression of meaning.
 */
export interface StateDelta {
  id: string;
  sessionId: string;
  
  // What changed
  type: 'belief_formed' | 'belief_updated' | 'belief_invalidated'
      | 'goal_set' | 'goal_completed' | 'goal_failed' | 'goal_changed'
      | 'decision_made' | 'action_taken' | 'error_occurred'
      | 'constraint_discovered' | 'conflict_detected'
      | 'learning_captured';
  
  // The change
  description: string;                 // "Agent discovered item_42 weighs 500g, not 200g"
  before: Record<string, unknown>;     // State before
  after: Record<string, unknown>;      // State after
  significance: number;                // 0.0–1.0: how important was this change?
  
  // Source events (for drill-down)
  sourceNodeIds: string[];             // Which IR nodes caused this delta
  
  // Temporal
  timestamp: string;
}

/**
 * Compress a sequence of RuntimeNodes into StateDelta[]
 * Reduces storage by 10-100x while preserving all meaningful information
 */
export function compressSession(nodes: RuntimeNode[]): StateDelta[] {
  const deltas: StateDelta[] = [];
  let currentBeliefs = new Map<string, unknown>();
  let currentGoals = new Map<string, string>();
  
  for (const node of nodes) {
    switch (node.kind) {
      case 'belief':
      case 'knowledge': {
        const key = extractBeliefKey(node);
        const oldValue = currentBeliefs.get(key);
        if (oldValue === undefined) {
          deltas.push({
            type: 'belief_formed',
            description: `Learned: ${node.label}`,
            before: {},
            after: node.content,
            significance: node.confidence,
            sourceNodeIds: [node.id],
            // ...
          });
        } else if (JSON.stringify(oldValue) !== JSON.stringify(node.content)) {
          deltas.push({
            type: 'belief_updated',
            description: `Updated understanding: ${node.label}`,
            before: { [key]: oldValue },
            after: node.content,
            significance: node.confidence * 0.8,
            sourceNodeIds: [node.id],
            // ...
          });
        }
        // If same value, NO DELTA — this is the compression
        currentBeliefs.set(key, node.content);
        break;
      }
      
      case 'decision':
        deltas.push({
          type: 'decision_made',
          description: node.label,
          before: {},
          after: node.content,
          significance: node.confidence,
          sourceNodeIds: [node.id],
          // ...
        });
        break;
        
      case 'error':
        deltas.push({
          type: 'error_occurred',
          description: node.label,
          before: {},
          after: node.content,
          significance: 1.0, // Errors are always significant
          sourceNodeIds: [node.id],
          // ...
        });
        break;
      
      // ... similar for other meaningful transitions
    }
  }
  
  return deltas;
}
```

**Impact**: A session with 1,000 IR nodes might produce only 15-30 state deltas. Storage cost drops 30-60x. But all information is preserved — you can always drill down to the source nodes.

---

### Breakthrough 7: Runtime Optimization Compiler

The killer feature nobody has built:

```typescript
// apps/dashboard/src/lib/engines/optimizer.ts

/**
 * Runtime Optimization Compiler
 * 
 * Analyzes completed sessions and identifies optimization opportunities.
 * Like a compiler optimization pass, but for AI agent execution.
 * 
 * Phase 1 (Day 1): Static analysis — identify patterns after execution
 * Phase 2 (Month 3): Suggest optimizations before execution
 * Phase 3 (Month 6): Automatically apply optimizations at runtime
 */
export interface OptimizationPass {
  id: string;
  name: string;
  description: string;
  analyze: (nodes: RuntimeNode[], edges: RuntimeEdge[]) => Optimization[];
}

export interface Optimization {
  type: OptimizationType;
  description: string;                 // Human-readable explanation
  impact: {
    costReduction: number;            // Estimated USD savings
    latencyReduction: number;         // Estimated ms savings
    qualityImpact: number;            // -1.0 to 1.0 (negative = quality decrease)
  };
  confidence: number;                  // How confident in this optimization
  suggestion: string;                  // Actionable suggestion
  affectedNodes: string[];            // Which nodes this affects
}

export type OptimizationType =
  | 'redundant_reasoning'     // Agent reasoned about the same thing twice
  | 'unnecessary_retrieval'   // Memory retrieval that wasn't used
  | 'tool_call_merge'         // Multiple tool calls that could be batched
  | 'prompt_inefficiency'     // Prompt that could be shortened
  | 'context_overflow'        // Too much context provided to LLM
  | 'unnecessary_reflection'  // Reflection that didn't change behavior
  | 'stale_cache'             // Using cached data when fresh data is needed
  | 'premature_decision'      // Decision made with insufficient information
  | 'serial_parallelizable'   // Sequential steps that could run in parallel
  | 'dead_branch';            // Reasoning branch that led nowhere

// Example optimization pass: detect redundant reasoning
export const redundantReasoningPass: OptimizationPass = {
  id: 'redundant-reasoning',
  name: 'Redundant Reasoning Elimination',
  description: 'Detects when an agent reasons about the same topic multiple times without new information',
  
  analyze(nodes, edges) {
    const optimizations: Optimization[] = [];
    const reasoningNodes = nodes.filter(n => n.kind === 'reasoning');
    
    for (let i = 1; i < reasoningNodes.length; i++) {
      for (let j = 0; j < i; j++) {
        const similarity = computeContentSimilarity(reasoningNodes[i], reasoningNodes[j]);
        
        // Check if any new information arrived between j and i
        const nodesBetween = nodes.filter(n => 
          new Date(n.timestamp) > new Date(reasoningNodes[j].timestamp) &&
          new Date(n.timestamp) < new Date(reasoningNodes[i].timestamp)
        );
        const newInfoNodes = nodesBetween.filter(n => 
          n.kind === 'observation' || n.kind === 'knowledge'
        );
        
        if (similarity > 0.8 && newInfoNodes.length === 0) {
          optimizations.push({
            type: 'redundant_reasoning',
            description: `Reasoning step "${reasoningNodes[i].label}" is ${(similarity * 100).toFixed(0)}% similar to earlier step "${reasoningNodes[j].label}" with no new information between them.`,
            impact: {
              costReduction: reasoningNodes[i].cost,
              latencyReduction: reasoningNodes[i].latency,
              qualityImpact: 0, // Removing redundant reasoning doesn't hurt quality
            },
            confidence: similarity,
            suggestion: `Cache the result of "${reasoningNodes[j].label}" and skip re-reasoning when no new information is available.`,
            affectedNodes: [reasoningNodes[i].id, reasoningNodes[j].id],
          });
        }
      }
    }
    
    return optimizations;
  },
};
```

---

## The Practical Architecture (What We Actually Ship)

### The Bridge: Vision → Reality

The seven breakthroughs above are the **destination**. We don't build all of them on Day 1. We build them **in order of what's shippable**:

| Phase | What Ships | Breakthrough Used | ML Required? |
|---|---|---|---|
| Phase 1 (Weeks 1-3) | SDK + Dashboard + Event Viewer + Basic Graph | Runtime IR (simplified), basic edges | No |
| Phase 2 (Weeks 4-6) | Intelligence Graph + Heuristic Predictions + Risk Scores | Graph heuristics, confidence tracking | No |
| Phase 3 (Weeks 7-10) | Causal Analysis + Intent Alignment + Optimization Suggestions | Causal Engine, Intent Engine, Optimizer (static) | No |
| Phase 4 (Months 3-6) | Reality Graph + Knowledge Compression + Bayesian Predictions | Reality Graph, Compressor, Bayesian inference | Light ML |
| Phase 5 (Months 6-12) | Simulation + Adaptive Runtime + Cross-customer Learning | Simulator, temporal models, federated learning | Full ML |

**Key insight**: Phases 1-3 require ZERO machine learning. They use graph algorithms, heuristics, and structured reasoning. This means we can ship breakthrough-level technology in weeks, not months.

---

### Tech Stack (Final — No Changes)

```
LANGUAGE:        TypeScript (everything except Python SDK)
                 Python (SDK only — pip install veri)

FRONTEND:        Next.js 15 (App Router)
                 React 19
                 Tailwind CSS v4
                 shadcn/ui + Radix
                 React Flow (intelligence graph visualization)
                 Recharts (metrics and analytics)
                 Framer Motion (animations)
                 Zustand (client state)
                 TanStack Query (server state)
                 cmdk (command palette)

BACKEND:         Next.js API routes (ingest + query)
                 tRPC (type-safe dashboard ↔ server communication)
                 Drizzle ORM (type-safe database access)
                 BullMQ (background job processing via Redis)

DATABASE:        PostgreSQL 16 (ALL data — events, state, config, analytics)
                 Redis 7 (job queue, cache, pub/sub for real-time)

INFRASTRUCTURE:  Docker Compose (development)
                 Vercel or Fly.io (production)
                 GitHub Actions (CI/CD)

TESTING:         Vitest (unit + integration)
                 Playwright (E2E)
                 pytest (Python SDK)

MONOREPO:        Turborepo + pnpm
```

**Total: 1 language (TypeScript + Python SDK), 1 database (PostgreSQL), 1 cache (Redis), 1 framework (Next.js).**

---

### Database Schema (V1)

```sql
-- =================================================================
-- RUNTIME IR STORAGE
-- =================================================================

-- Core: Runtime Nodes (the atomic unit of intelligence)
CREATE TABLE runtime_nodes (
    id TEXT PRIMARY KEY,                    -- ULID
    project_id UUID NOT NULL,
    agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    
    -- IR classification
    kind TEXT NOT NULL,                     -- 'intent', 'belief', 'reasoning', 'action', etc.
    label TEXT NOT NULL,                    -- Human-readable label
    content JSONB NOT NULL DEFAULT '{}',    -- Structured payload
    
    -- Epistemic state
    confidence REAL,                        -- 0.0–1.0
    uncertainty REAL,                       -- 0.0–1.0
    assumptions TEXT[] DEFAULT '{}',
    evidence TEXT[] DEFAULT '{}',
    
    -- Resources
    cost_usd DOUBLE PRECISION DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    
    -- Temporal
    timestamp TIMESTAMPTZ NOT NULL,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE runtime_nodes_2026_07 PARTITION OF runtime_nodes
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE runtime_nodes_2026_08 PARTITION OF runtime_nodes
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- Indexes
CREATE INDEX idx_nodes_session ON runtime_nodes (session_id, timestamp);
CREATE INDEX idx_nodes_project_agent ON runtime_nodes (project_id, agent_id, timestamp);
CREATE INDEX idx_nodes_kind ON runtime_nodes (kind);
CREATE INDEX idx_nodes_confidence ON runtime_nodes (confidence) WHERE confidence IS NOT NULL;
CREATE INDEX idx_nodes_content ON runtime_nodes USING gin (content);

-- Runtime Edges (relationships between nodes)
CREATE TABLE runtime_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    kind TEXT NOT NULL,                     -- 'causes', 'depends_on', 'conflicts_with', etc.
    weight REAL DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    session_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_edges_source ON runtime_edges (source_id);
CREATE INDEX idx_edges_target ON runtime_edges (target_id);
CREATE INDEX idx_edges_session ON runtime_edges (session_id);
CREATE INDEX idx_edges_kind ON runtime_edges (kind);

-- Runtime Frames (snapshots of agent state at a point in time)
CREATE TABLE runtime_frames (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    project_id UUID NOT NULL,
    
    timestamp TIMESTAMPTZ NOT NULL,
    
    active_goals TEXT[] DEFAULT '{}',
    active_beliefs TEXT[] DEFAULT '{}',
    active_plan TEXT[] DEFAULT '{}',
    working_memory TEXT[] DEFAULT '{}',
    
    total_cost DOUBLE PRECISION DEFAULT 0,
    total_latency INTEGER DEFAULT 0,
    overall_confidence REAL,
    overall_risk REAL,
    
    nodes_added TEXT[] DEFAULT '{}',
    nodes_removed TEXT[] DEFAULT '{}',
    beliefs_changed TEXT[] DEFAULT '{}',
    confidence_deltas JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_frames_session ON runtime_frames (session_id, timestamp);

-- =================================================================
-- STATE DELTAS (Knowledge Compression)
-- =================================================================

CREATE TABLE state_deltas (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id UUID NOT NULL,
    
    type TEXT NOT NULL,                     -- 'belief_formed', 'decision_made', etc.
    description TEXT NOT NULL,
    before_state JSONB DEFAULT '{}',
    after_state JSONB DEFAULT '{}',
    significance REAL NOT NULL,             -- 0.0–1.0
    
    source_node_ids TEXT[] DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_deltas_session ON state_deltas (session_id, timestamp);
CREATE INDEX idx_deltas_type ON state_deltas (type);
CREATE INDEX idx_deltas_significance ON state_deltas (significance DESC);

-- =================================================================
-- PREDICTIONS
-- =================================================================

CREATE TABLE predictions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id UUID NOT NULL,
    
    type TEXT NOT NULL,                     -- 'failure', 'cost_overrun', 'reasoning_loop', etc.
    probability REAL NOT NULL,
    confidence REAL NOT NULL,
    horizon_steps INTEGER,
    
    explanation TEXT NOT NULL,
    evidence JSONB DEFAULT '[]',
    counterfactual TEXT,
    suggested_action TEXT,
    
    method TEXT NOT NULL,                   -- 'heuristic', 'graph', 'bayesian', 'hybrid'
    resolved BOOLEAN DEFAULT false,
    resolution TEXT,                        -- 'correct', 'false_positive', 'prevented'
    
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_session ON predictions (session_id, computed_at);
CREATE INDEX idx_predictions_type ON predictions (type);
CREATE INDEX idx_predictions_unresolved ON predictions (resolved) WHERE NOT resolved;

-- =================================================================
-- OPTIMIZATIONS
-- =================================================================

CREATE TABLE optimizations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id UUID NOT NULL,
    
    type TEXT NOT NULL,                     -- 'redundant_reasoning', 'tool_call_merge', etc.
    description TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    
    cost_reduction DOUBLE PRECISION DEFAULT 0,
    latency_reduction INTEGER DEFAULT 0,
    quality_impact REAL DEFAULT 0,
    confidence REAL NOT NULL,
    
    affected_node_ids TEXT[] DEFAULT '{}',
    applied BOOLEAN DEFAULT false,
    
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_optimizations_session ON optimizations (session_id);
CREATE INDEX idx_optimizations_type ON optimizations (type);

-- =================================================================
-- IDENTITY + CONFIG (same as before, proven patterns)
-- =================================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(63) NOT NULL UNIQUE,
    plan VARCHAR(20) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    avatar_url TEXT,
    password_hash TEXT,
    org_id UUID REFERENCES organizations(id),
    role VARCHAR(20) DEFAULT 'member',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(63) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, slug)
);

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    name VARCHAR(255),
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    key_prefix VARCHAR(12) NOT NULL,
    permissions TEXT[] DEFAULT ARRAY['ingest', 'read'],
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    framework VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, external_id)
);

CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(30) NOT NULL,
    rules JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =================================================================
-- MATERIALIZED VIEWS
-- =================================================================

-- Session summaries (refreshed by background worker)
CREATE MATERIALIZED VIEW session_summaries AS
SELECT
    n.project_id,
    n.agent_id,
    n.session_id,
    MIN(n.timestamp) AS started_at,
    MAX(n.timestamp) AS ended_at,
    COUNT(*) AS node_count,
    COUNT(DISTINCT n.kind) AS unique_kinds,
    SUM(n.cost_usd) AS total_cost,
    AVG(n.confidence) FILTER (WHERE n.confidence IS NOT NULL) AS avg_confidence,
    COUNT(*) FILTER (WHERE n.kind = 'error') AS error_count,
    BOOL_OR(n.kind = 'intent' AND n.label LIKE '%completed%') AS completed,
    BOOL_OR(n.kind = 'error') AS has_errors
FROM runtime_nodes n
GROUP BY n.project_id, n.agent_id, n.session_id;

CREATE UNIQUE INDEX idx_session_summaries ON session_summaries (project_id, session_id);
```

---

### Complete Repository Structure

```
veri/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                              # Lint + test + type-check
│   │   └── deploy.yml                          # Deploy to Vercel/Fly
│   └── pull_request_template.md
│
├── apps/
│   └── dashboard/                              # Next.js 15 — THE application
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx                  # Root: fonts, theme provider, query provider
│       │   │   ├── page.tsx                    # Redirect → /dashboard
│       │   │   ├── globals.css                 # Design tokens + animations
│       │   │   │
│       │   │   ├── (auth)/
│       │   │   │   ├── layout.tsx              # Centered auth layout
│       │   │   │   ├── login/page.tsx
│       │   │   │   └── register/page.tsx
│       │   │   │
│       │   │   ├── (dashboard)/
│       │   │   │   ├── layout.tsx              # Sidebar + topnav shell
│       │   │   │   ├── page.tsx                # Overview: metrics, agent health, live feed
│       │   │   │   │
│       │   │   │   ├── agents/
│       │   │   │   │   ├── page.tsx            # Agent grid with health cards
│       │   │   │   │   └── [agentId]/
│       │   │   │   │       ├── page.tsx        # Agent detail: sessions list, metrics
│       │   │   │   │       ├── sessions/
│       │   │   │   │       │   └── [sessionId]/
│       │   │   │   │       │       └── page.tsx # THE KEY PAGE: graph + timeline + inspector
│       │   │   │   │       └── analytics/
│       │   │   │   │           └── page.tsx    # Per-agent analytics
│       │   │   │   │
│       │   │   │   ├── runtime/
│       │   │   │   │   └── page.tsx            # Live runtime: active sessions, predictions
│       │   │   │   │
│       │   │   │   ├── intelligence/
│       │   │   │   │   ├── page.tsx            # Intelligence overview: causal analyses, optimizations
│       │   │   │   │   ├── predictions/
│       │   │   │   │   │   └── page.tsx        # All predictions with resolution tracking
│       │   │   │   │   ├── optimizations/
│       │   │   │   │   │   └── page.tsx        # Optimization suggestions across sessions
│       │   │   │   │   └── causal/
│       │   │   │   │       └── page.tsx        # Causal analysis viewer
│       │   │   │   │
│       │   │   │   ├── explore/
│       │   │   │   │   └── page.tsx            # Event explorer (filterable node table)
│       │   │   │   │
│       │   │   │   ├── analytics/
│       │   │   │   │   └── page.tsx            # Global analytics: cost, latency, quality
│       │   │   │   │
│       │   │   │   ├── policies/
│       │   │   │   │   ├── page.tsx
│       │   │   │   │   └── [policyId]/page.tsx
│       │   │   │   │
│       │   │   │   └── settings/
│       │   │   │       ├── page.tsx
│       │   │   │       ├── team/page.tsx
│       │   │   │       ├── api-keys/page.tsx
│       │   │   │       └── billing/page.tsx
│       │   │   │
│       │   │   └── api/
│       │   │       ├── trpc/[trpc]/route.ts    # tRPC handler
│       │   │       ├── v1/
│       │   │       │   ├── ingest/route.ts     # POST: batch node + edge ingestion
│       │   │       │   ├── agents/route.ts
│       │   │       │   ├── sessions/
│       │   │       │   │   └── [sessionId]/
│       │   │       │   │       ├── route.ts    # GET session
│       │   │       │   │       ├── graph/route.ts   # GET computed intelligence graph
│       │   │       │   │       ├── causal/route.ts  # GET causal analysis
│       │   │       │   │       └── predictions/route.ts # GET predictions
│       │   │       │   └── health/route.ts
│       │   │       └── ws/route.ts             # WebSocket for live streaming
│       │   │
│       │   ├── components/
│       │   │   ├── ui/                         # shadcn/ui (auto-generated by CLI)
│       │   │   │   ├── button.tsx
│       │   │   │   ├── card.tsx
│       │   │   │   ├── dialog.tsx
│       │   │   │   ├── dropdown-menu.tsx
│       │   │   │   ├── input.tsx
│       │   │   │   ├── badge.tsx
│       │   │   │   ├── tooltip.tsx
│       │   │   │   ├── tabs.tsx
│       │   │   │   ├── table.tsx
│       │   │   │   ├── sheet.tsx
│       │   │   │   ├── command.tsx
│       │   │   │   ├── popover.tsx
│       │   │   │   ├── skeleton.tsx
│       │   │   │   ├── separator.tsx
│       │   │   │   ├── scroll-area.tsx
│       │   │   │   ├── select.tsx
│       │   │   │   ├── switch.tsx
│       │   │   │   ├── avatar.tsx
│       │   │   │   └── sonner.tsx              # Toast notifications
│       │   │   │
│       │   │   ├── layout/
│       │   │   │   ├── sidebar.tsx
│       │   │   │   ├── top-nav.tsx
│       │   │   │   ├── breadcrumbs.tsx
│       │   │   │   ├── command-palette.tsx      # ⌘K
│       │   │   │   └── theme-provider.tsx
│       │   │   │
│       │   │   ├── agents/
│       │   │   │   ├── agent-card.tsx
│       │   │   │   ├── agent-list.tsx
│       │   │   │   ├── agent-status.tsx
│       │   │   │   └── agent-health.tsx
│       │   │   │
│       │   │   ├── runtime/
│       │   │   │   ├── live-feed.tsx
│       │   │   │   ├── execution-pipeline.tsx
│       │   │   │   ├── confidence-gauge.tsx
│       │   │   │   ├── risk-indicator.tsx
│       │   │   │   ├── cost-tracker.tsx
│       │   │   │   └── session-card.tsx
│       │   │   │
│       │   │   ├── graph/                      # THE DIFFERENTIATOR
│       │   │   │   ├── intelligence-graph.tsx   # React Flow canvas
│       │   │   │   ├── ir-node.tsx              # Custom node (colored by NodeKind)
│       │   │   │   ├── ir-edge.tsx              # Custom edge (animated by EdgeKind)
│       │   │   │   ├── graph-controls.tsx       # Layout, filter, zoom
│       │   │   │   ├── graph-minimap.tsx
│       │   │   │   └── node-inspector.tsx       # Right panel: full node detail
│       │   │   │
│       │   │   ├── intelligence/
│       │   │   │   ├── prediction-card.tsx      # Prediction with probability + explanation
│       │   │   │   ├── causal-chain.tsx         # Visual causal chain (root → failure)
│       │   │   │   ├── intent-alignment.tsx     # Agent vs User vs Policy alignment
│       │   │   │   ├── optimization-card.tsx    # Optimization suggestion with impact
│       │   │   │   └── delta-timeline.tsx       # Compressed state delta timeline
│       │   │   │
│       │   │   ├── analytics/
│       │   │   │   ├── metric-card.tsx
│       │   │   │   ├── trend-chart.tsx
│       │   │   │   ├── cost-chart.tsx
│       │   │   │   └── quality-chart.tsx
│       │   │   │
│       │   │   ├── explore/
│       │   │   │   ├── node-table.tsx           # Paginated node table
│       │   │   │   ├── node-detail.tsx
│       │   │   │   ├── filter-bar.tsx
│       │   │   │   └── search-input.tsx
│       │   │   │
│       │   │   ├── timeline/
│       │   │   │   ├── session-timeline.tsx
│       │   │   │   └── timeline-entry.tsx
│       │   │   │
│       │   │   └── shared/
│       │   │       ├── logo.tsx
│       │   │       ├── empty-state.tsx
│       │   │       ├── loading-state.tsx
│       │   │       ├── error-boundary.tsx
│       │   │       ├── json-viewer.tsx
│       │   │       ├── code-block.tsx
│       │   │       ├── relative-time.tsx
│       │   │       ├── copy-button.tsx
│       │   │       ├── status-dot.tsx
│       │   │       └── sparkline.tsx
│       │   │
│       │   ├── hooks/
│       │   │   ├── use-realtime.ts
│       │   │   ├── use-agents.ts
│       │   │   ├── use-sessions.ts
│       │   │   ├── use-graph.ts
│       │   │   ├── use-predictions.ts
│       │   │   ├── use-analytics.ts
│       │   │   ├── use-keyboard.ts
│       │   │   └── use-theme.ts
│       │   │
│       │   ├── lib/
│       │   │   ├── trpc/
│       │   │   │   ├── client.ts               # tRPC React client
│       │   │   │   ├── server.ts               # tRPC server context + caller
│       │   │   │   ├── router.ts               # Root router
│       │   │   │   └── routers/
│       │   │   │       ├── agents.ts            # Agent queries
│       │   │   │       ├── sessions.ts          # Session queries + graph computation
│       │   │   │       ├── nodes.ts             # Node queries + search
│       │   │   │       ├── predictions.ts       # Prediction queries
│       │   │   │       ├── analytics.ts         # Aggregated analytics
│       │   │   │       └── settings.ts          # Project settings
│       │   │   │
│       │   │   ├── db/
│       │   │   │   ├── index.ts                # Drizzle client
│       │   │   │   ├── schema.ts               # ALL table definitions
│       │   │   │   └── migrations/             # Drizzle migrations
│       │   │   │
│       │   │   ├── engines/                    # THE INTELLIGENCE CORE
│       │   │   │   ├── ir-compiler.ts          # Compile framework events → Runtime IR
│       │   │   │   ├── graph-builder.ts        # Build graph from IR nodes + edges
│       │   │   │   ├── causal-engine.ts        # Root cause analysis
│       │   │   │   ├── intent-engine.ts        # Intent alignment detection
│       │   │   │   ├── prediction-engine.ts    # Hybrid predictions
│       │   │   │   ├── heuristics.ts           # Day-1 prediction heuristics
│       │   │   │   ├── optimizer.ts            # Optimization compiler passes
│       │   │   │   ├── compressor.ts           # Knowledge compression
│       │   │   │   ├── risk-scorer.ts          # Risk score computation
│       │   │   │   └── temporal.ts             # Temporal state tracking (frames)
│       │   │   │
│       │   │   ├── ingest/
│       │   │   │   ├── validator.ts            # Validate incoming IR nodes
│       │   │   │   ├── processor.ts            # Process + enrich incoming data
│       │   │   │   └── api-key.ts              # API key validation
│       │   │   │
│       │   │   ├── workers/
│       │   │   │   ├── index.ts                # BullMQ worker setup
│       │   │   │   ├── prediction-worker.ts    # Run predictions on new data
│       │   │   │   ├── compression-worker.ts   # Compress completed sessions
│       │   │   │   ├── optimization-worker.ts  # Run optimizer on completed sessions
│       │   │   │   ├── frame-worker.ts         # Compute runtime frames
│       │   │   │   └── refresh-views.ts        # Refresh materialized views
│       │   │   │
│       │   │   ├── auth/
│       │   │   │   ├── index.ts
│       │   │   │   └── middleware.ts
│       │   │   │
│       │   │   ├── websocket.ts
│       │   │   ├── utils.ts
│       │   │   ├── format.ts
│       │   │   ├── colors.ts
│       │   │   └── constants.ts
│       │   │
│       │   ├── stores/
│       │   │   ├── app-store.ts
│       │   │   ├── filter-store.ts
│       │   │   ├── graph-store.ts
│       │   │   └── realtime-store.ts
│       │   │
│       │   └── types/
│       │       └── index.ts                    # Re-exports from @veri/runtime-ir
│       │
│       ├── drizzle.config.ts
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       ├── postcss.config.js
│       └── package.json
│
├── packages/
│   ├── runtime-ir/                             # The Universal Runtime IR
│   │   ├── src/
│   │   │   ├── index.ts                       # Re-exports
│   │   │   ├── types.ts                       # RuntimeNode, RuntimeEdge, RuntimeFrame
│   │   │   ├── reality.ts                     # RealityGraph, RealityEntity, Constraints
│   │   │   ├── builders.ts                    # Fluent API to build IR nodes/edges
│   │   │   ├── validation.ts                  # Validate IR structures
│   │   │   └── serialization.ts               # JSON serialization/deserialization
│   │   ├── tsconfig.json
│   │   └── package.json
│   │
│   ├── sdk-python/                             # Python SDK
│   │   ├── veri/
│   │   │   ├── __init__.py                    # init(), Client, trace
│   │   │   ├── client.py                      # VeriClient — emits IR nodes
│   │   │   ├── ir.py                          # RuntimeNode, RuntimeEdge dataclasses
│   │   │   ├── session.py                     # Session context manager
│   │   │   ├── decorators.py                  # @veri.trace, @veri.goal
│   │   │   ├── transport.py                   # HTTPS with retry + batch
│   │   │   ├── buffer.py                      # In-memory buffer, flush on interval
│   │   │   ├── compiler.py                    # Compile framework traces → IR
│   │   │   └── integrations/
│   │   │       ├── __init__.py
│   │   │       ├── openai.py                  # Auto-patch openai → IR nodes
│   │   │       ├── anthropic.py               # Auto-patch anthropic → IR nodes
│   │   │       ├── langchain.py               # LangChain callback → IR nodes
│   │   │       └── langgraph.py               # LangGraph → IR nodes
│   │   ├── tests/
│   │   │   ├── test_client.py
│   │   │   ├── test_ir.py
│   │   │   ├── test_compiler.py
│   │   │   └── test_integrations/
│   │   │       └── test_openai.py
│   │   ├── pyproject.toml
│   │   └── README.md
│   │
│   └── sdk-js/                                # JavaScript/TypeScript SDK
│       ├── src/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   ├── session.ts
│       │   ├── ir-builder.ts                  # Fluent API to build IR
│       │   ├── transport.ts
│       │   ├── buffer.ts
│       │   ├── compiler.ts                    # Compile framework traces → IR
│       │   └── integrations/
│       │       ├── vercel-ai.ts
│       │       └── openai.ts
│       ├── tests/
│       │   ├── client.test.ts
│       │   └── compiler.test.ts
│       ├── tsconfig.json
│       ├── tsup.config.ts
│       ├── package.json
│       └── README.md
│
├── infrastructure/
│   ├── docker/
│   │   ├── docker-compose.yml                 # PostgreSQL + Redis
│   │   └── .env.example
│   └── scripts/
│       ├── setup.sh                           # Install deps + run migrations
│       ├── setup.ps1                          # Windows equivalent
│       ├── seed.ts                            # Seed demo data
│       └── demo-agent.ts                      # Generate realistic demo IR stream
│
├── docs/
│   ├── quickstart.md
│   ├── architecture.md
│   ├── runtime-ir.md                          # IR specification
│   ├── intelligence-engines.md                # How the engines work
│   ├── sdk-python.md
│   ├── sdk-js.md
│   ├── api.md
│   └── self-hosting.md
│
├── tests/
│   ├── integration/
│   │   └── ingest-pipeline.test.ts            # SDK → API → DB → Graph → Dashboard
│   ├── e2e/
│   │   └── playwright/
│   │       ├── dashboard.spec.ts
│   │       └── session-graph.spec.ts
│   └── load/
│       └── k6/
│           └── ingest.js
│
├── turbo.json
├── pnpm-workspace.yaml
├── package.json
├── .gitignore
├── .env.example
├── .eslintrc.js
├── .prettierrc
├── LICENSE
└── README.md
```

---

## SDK Design: The 2-Line Developer Experience

### Python SDK (emits Runtime IR, not events)

```python
# === Zero-config: 2 lines ===
import veri
veri.init(api_key="vk_...")
# Every OpenAI/Anthropic/LangChain call now emits Runtime IR nodes automatically

# === Explicit tracking (full intelligence) ===
import veri

client = veri.Client(api_key="vk_...")

with client.session("book-flight") as session:
    
    # Track intent (not just "goal" — intent includes WHY)
    with session.intent("Find cheapest flight SFO → NYC",
                        constraints=["arrive before 9am"],
                        budget=0.50) as intent:
        
        # Track knowledge retrieval (with confidence + staleness)
        with session.knowledge("retrieve flight history") as mem:
            docs = vector_db.search("past flight preferences")
            mem.result(docs, confidence=0.82, 
                      assumptions=["user preferences haven't changed"])
        
        # Track reasoning (with uncertainty)
        with session.reasoning("evaluate flight options") as reason:
            analysis = llm.complete("Compare these flights...")
            reason.result(analysis, confidence=0.91, uncertainty=0.15,
                         evidence=["pricing data from search API"])
        
        # Track tool use (with cost + latency automatically captured)
        with session.action("search_flights") as action:
            results = flight_api.search(origin="SFO", dest="NYC")
            action.result(results)
        
        # Track decision (with alternatives considered)
        with session.decision("select flight UA-1234",
                            alternatives=["UA-5678 ($145, 8am)", "AA-9012 ($127, 11pm)"],
                            reasoning="Cheapest option that arrives before 9am") as decision:
            decision.result({"flight": "UA-1234", "price": 145})
        
        intent.complete(result="Booked UA-1234 for $145")

# === Decorator style ===
@veri.trace
def my_agent(query: str):
    """Auto-instruments all nested calls as IR nodes"""
    results = search(query)     # → action node
    analysis = analyze(results) # → reasoning node
    return summarize(analysis)  # → reasoning node
```

**Key difference from old SDK**: The session emits `RuntimeNode` objects with `kind`, `confidence`, `uncertainty`, `assumptions`, and `evidence` — not flat events. The IR compiler in the SDK translates framework-specific traces into universal IR.

---

## API Design

```yaml
# Ingestion (the critical path — this is what SDKs call)
POST   /api/v1/ingest
  Headers: Authorization: Bearer vk_...
  Body: {
    nodes: RuntimeNode[],     # Batch of IR nodes
    edges: RuntimeEdge[]      # Batch of IR edges
  }
  Response: { accepted: number, errors: ValidationError[] }

# Agents
GET    /api/v1/agents                        # List agents
GET    /api/v1/agents/:id                    # Agent detail + health
GET    /api/v1/agents/:id/sessions           # Agent sessions (paginated)

# Sessions
GET    /api/v1/sessions/:id                  # Session detail + summary
GET    /api/v1/sessions/:id/nodes            # Session IR nodes (paginated, filterable)
GET    /api/v1/sessions/:id/graph            # Computed intelligence graph
GET    /api/v1/sessions/:id/timeline         # Timeline of state deltas
GET    /api/v1/sessions/:id/frames           # Runtime frames (temporal snapshots)

# Intelligence (the differentiating APIs)
GET    /api/v1/sessions/:id/predictions      # Active predictions for session
GET    /api/v1/sessions/:id/causal           # Causal analysis (if failure occurred)
GET    /api/v1/sessions/:id/optimizations    # Optimization suggestions
GET    /api/v1/sessions/:id/intent           # Intent alignment analysis
GET    /api/v1/sessions/:id/deltas           # Compressed state deltas

# Analytics
GET    /api/v1/analytics                     # Aggregated metrics
GET    /api/v1/analytics/costs               # Cost analytics
GET    /api/v1/analytics/quality             # Quality analytics (confidence, risk)

# Real-time
WS     /api/ws                               # Live node streaming + predictions

# Management
POST   /api/v1/projects                      # Create project
GET    /api/v1/projects/:id/api-keys         # List keys
POST   /api/v1/projects/:id/api-keys         # Create key
```

---

## Execution Plan

### Phase 1 (Weeks 1-3): "The Intelligent Trace"

**Goal**: Developer installs SDK → sees intelligence graph (not logs) → understands WHY agent did what it did.

| Week | What Ships |
|---|---|
| **Week 1** | Monorepo scaffold, Docker Compose (PG + Redis), DB schema (Drizzle), Runtime IR package, ingest API, Python SDK (basic), dashboard shell (sidebar + topnav + dark theme) |
| **Week 2** | Agent list page, session list, node explorer (filterable table), JSON viewer, session timeline, live event feed (WebSocket) |
| **Week 3** | Intelligence Graph (React Flow with custom IR nodes + edges), node inspector panel, graph controls (zoom, filter, layout), basic metric cards (cost, latency, node count) |

**Success**: A LangGraph agent instrumented with VERI. Developer opens dashboard, sees the Intelligence Graph, clicks a reasoning node, sees WHY the agent made that decision. This is impossible with LangSmith today.

### Phase 2 (Weeks 4-6): "The Reasoning Debugger"

**Goal**: VERI predicts failures, explains causes, and suggests optimizations — all without ML.

| Week | What Ships |
|---|---|
| **Week 4** | Heuristic prediction engine (loop detection, confidence degradation, cost anomaly, memory staleness), prediction cards in dashboard, risk indicators |
| **Week 5** | Causal engine (backward graph traversal → root cause), causal chain visualization, intent alignment detection |
| **Week 6** | Runtime optimization compiler (static analysis: redundant reasoning, unnecessary retrieval, parallelizable steps), optimization cards, knowledge compression engine, state delta timeline |

**Success**: Developer's agent fails. VERI shows: "Failure caused by stale memory from 3 hours ago → led to wrong tool selection → cascading error." Developer also sees: "3 optimization opportunities found: $0.12 cost savings, 2.3s latency reduction."

### Phase 3 (Weeks 7-10): "Production Ready"

| What Ships |
|---|
| JavaScript/TypeScript SDK |
| Auth (login, register, API key management) |
| Command palette (⌘K) |
| Keyboard shortcuts |
| Onboarding flow |
| Auto-instrumentation for LangChain, CrewAI, OpenAI, Anthropic |
| Policy engine (cost limits, risk thresholds) |
| Live runtime monitor (active sessions with predictions) |
| Documentation site |
| Demo event generator |

**Success**: 10 external developers using VERI in production.

### Phase 4 (Months 3-12): "The Moat"

| What Ships |
|---|
| Bayesian prediction engine (trained on accumulated data) |
| Reality Graph (world state tracking beyond events) |
| Temporal modeling (pattern detection across time) |
| Cross-session learning (detect patterns across an agent's history) |
| Counterfactual simulation ("what if" with changed parameters) |
| Session comparison (diff two executions) |
| Webhook notifications + Slack/Discord integration |
| Team collaboration features |
| Self-hosted deployment (Docker Compose → production) |
| Enterprise SSO + RBAC |

---

## What Makes This Architecture Uncopyable

| Component | Why Competitors Can't Easily Copy |
|---|---|
| **Runtime IR** | Network effect — once frameworks compile to VERI IR, switching cost is high. Like LLVM: the more frontends that target it, the harder to displace. |
| **Causal Engine** | Requires typed relationships (`causes`, `conflicts_with`, `assumes`) that flat traces don't capture. Retroactively adding this to LangSmith/Arize would require rebuilding their data model. |
| **Knowledge Compression** | Requires understanding semantic meaning of state changes, not just events. Statistical compression is easy. Semantic compression requires intelligence. |
| **Cross-customer Learning** | The prediction and optimization models improve with every connected agent. More customers = better predictions = more customers. Classic data flywheel. |
| **Optimization Compiler** | Requires the IR. Without a universal representation, you can't write optimization passes that work across frameworks. |

---

## Open Questions

> [!IMPORTANT]
> ### Decisions Before I Start Building
> 1. **Shall I start building Phase 1 now?** I can scaffold the entire monorepo, Runtime IR package, database, ingest API, SDK, and dashboard in this session.
> 2. **Auth strategy**: Email/password for V1, or OAuth (GitHub, Google) from Day 1?
> 3. **Deployment**: Vercel (easy for Next.js), Fly.io (more control), or self-hosted only?
> 4. **Open source**: SDKs MIT + Dashboard ELv2 (Grafana model)?
> 5. **The IR spec**: Should we publish the Runtime IR specification as an open standard? This would accelerate adoption (more frameworks compile to it) but also lets competitors use it.
> 6. **Name**: Is "VERI" final? "Runtime IR" needs a catchy name for developer adoption.

## Verification Plan

### Automated Tests
- `vitest` for all TypeScript (unit + integration)
- `pytest` for Python SDK
- `playwright` for dashboard E2E
- Integration: Python SDK → Ingest API → PostgreSQL → Graph Builder → WebSocket → Dashboard

### Manual Verification
- Instrument a LangGraph agent → verify Intelligence Graph renders correctly
- Trigger a reasoning loop → verify prediction engine detects it
- Introduce stale memory → verify causal engine identifies it as root cause
- Complete a session → verify optimization compiler finds suggestions
- Load test: sustain 1K nodes/second through ingest API
