import { Confidence } from './confidence';

/**
 * Escalation Policy — defines when an agent action requires human approval.
 * Policies are evaluated client-side (SDK) and enforced server-side (gateway).
 */
export interface EscalationPolicy {
  id: string;
  projectId: string;
  name: string;
  description?: string;

  trigger: {
    capabilities?: string[];           // e.g. ['is_decision_point']
    actionTypes?: string[];            // e.g. ['financial_transaction', 'refund']
    riskThreshold?: number;            // escalate if risk > threshold
    confidenceBelow?: number;          // escalate if confidence < threshold
    confidenceSource?: string;         // only trigger on specific source
    costAbove?: number;                // escalate if cost > threshold
  };

  resolution: {
    channel: 'in_app_queue' | 'slack' | 'email' | 'webhook';
    webhookUrl?: string;
    slackChannel?: string;
    email?: string;
    timeoutSeconds: number;
    timeoutBehavior: 'block' | 'proceed_with_flag' | 'abort';
    requiredApprovers: number;
  };

  auditRequirement: 'none' | 'reasoned' | 'signed';
  enabled: boolean;
  priority: number;
}

/**
 * Escalation Record — created when a policy triggers on an agent action.
 * Immutable once created (append-only storage for compliance).
 */
export interface EscalationRecord {
  id: string;
  policyId: string;
  policyName: string;
  sessionId: string;
  projectId: string;
  agentId: string;

  // The node that triggered escalation
  nodeId: string;
  nodeKind: string;
  nodeLabel: string;
  nodeContent: Record<string, unknown>;
  nodeConfidenceValue?: number;
  nodeConfidenceSource?: string;
  nodeCapabilities: string[];

  // Resolution state
  status: 'pending' | 'approved' | 'rejected' | 'timed_out' | 'aborted';
  resolvedBy?: string;
  resolvedAt?: string;
  resolutionReason?: string;
  resolutionSignature?: string;      // HMAC-SHA256 for non-repudiation

  // Timing
  escalatedAt: string;
  timeoutAt: string;
  timedOut: boolean;
}

/**
 * Approval Audit Log Entry — strictly append-only record of every
 * state transition on an escalation. Each entry carries an HMAC
 * signature for non-repudiation.
 */
export interface ApprovalAuditEntry {
  id: number;
  escalationId: string;
  action: 'created' | 'approved' | 'rejected' | 'timed_out' | 'aborted' | 'escalated_to_channel';
  actor: string;
  reason?: string;
  signature: string;                  // HMAC-SHA256(actor|action|timestamp|escalation_id)
  metadata?: Record<string, unknown>;
  createdAt: string;
}

/**
 * Causal Finding — a single link in a causal chain, always labeled
 * with whether it was derived from real replay (ablation) or
 * structural heuristic. Never blended, never hidden.
 */
export interface CausalFinding {
  id: string;
  sessionId: string;
  failureNodeId: string;
  candidateNodeId: string;
  method: 'ablation' | 'structural_heuristic';
  score: number;                      // 0.0–1.0 contribution to failure
  explanation: string;
  computedAt: string;
}

/**
 * Auditable Decision — the complete evidence package for a single
 * agent decision. This is what a compliance officer, external auditor,
 * or board member reviews. It combines causal analysis, replay proof,
 * and human approval records into a single exportable artifact.
 */
export interface AuditableDecision {
  decisionNodeId: string;
  sessionId: string;
  projectId: string;
  timestamp: string;

  // Causal chain with method transparency
  causalChain: CausalFinding[];

  // Replay evidence
  replayArtifact: {
    replayable: boolean;
    cachedInputSnapshot: Record<string, unknown>;
    reproducedAt?: string;
    reproducedBy: 'ablation_engine' | 'structural_heuristic';
  };

  // Human approval trail
  humanApprovals: EscalationRecord[];

  // Risk context at decision time
  riskAssessment: {
    confidenceAtDecision: Confidence;
    upstreamRiskFactors: string[];
  };

  // Export metadata
  exportFormat: 'json' | 'pdf_report' | 'soc2_evidence_package';
  generatedAt: string;
}
