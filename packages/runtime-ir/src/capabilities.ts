export type Capability =
  | 'has_dataflow_deps'      // participates in depends_on edges
  | 'is_decision_point'      // a branch/choice was made here
  | 'has_measurable_confidence'
  | 'is_replayable'          // deterministic + cacheable → ablation engine can use it
  | 'affects_cost'
  | 'is_terminal'            // session/goal end state
  | 'is_error'
  | 'is_escalated';          // triggered an escalation policy → required human approval
