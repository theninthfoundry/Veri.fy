-- ══════════════════════════════════════════════════════════════════
-- VERI Agent Accountability Platform — Schema Migration 002
-- Adds: Escalation Policies, Escalation Records, Approval Audit Log
-- Hardens: Append-only semantics on audit-critical tables
-- ══════════════════════════════════════════════════════════════════

-- ── Escalation Policies ───────────────────────────────────────────
-- Defines the rules that determine when an agent action requires
-- human approval before proceeding. Policies are evaluated in the
-- SDK at span creation time (via capability + confidence matching)
-- and enforced server-side by the analyzer service.

CREATE TABLE IF NOT EXISTS escalation_policies (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Trigger conditions (any combination — all specified conditions must match)
    trigger_capabilities TEXT[] DEFAULT '{}',
    trigger_action_types TEXT[] DEFAULT '{}',
    trigger_risk_threshold REAL,
    trigger_confidence_below REAL,
    trigger_confidence_source TEXT CHECK (
        trigger_confidence_source IS NULL
        OR trigger_confidence_source IN ('measured','self_reported','derived','unavailable')
    ),
    trigger_cost_above REAL,

    -- Resolution configuration
    resolution_channel VARCHAR(50) NOT NULL DEFAULT 'in_app_queue'
        CHECK (resolution_channel IN ('in_app_queue','slack','email','webhook')),
    resolution_webhook_url TEXT,
    resolution_slack_channel TEXT,
    resolution_email TEXT,
    timeout_seconds INTEGER NOT NULL DEFAULT 300,
    timeout_behavior VARCHAR(50) NOT NULL DEFAULT 'block'
        CHECK (timeout_behavior IN ('block','proceed_with_flag','abort')),
    required_approvers INTEGER NOT NULL DEFAULT 1,

    -- Audit requirements
    audit_requirement VARCHAR(50) NOT NULL DEFAULT 'reasoned'
        CHECK (audit_requirement IN ('none','reasoned','signed')),

    enabled BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policies_project
    ON escalation_policies (project_id) WHERE enabled = true;

-- ── Escalation Records ────────────────────────────────────────────
-- Each row represents a single escalation event: an agent node that
-- triggered a policy and requires human resolution. This table is
-- designed to be append-only for compliance — status transitions are
-- tracked via the approval_audit_log table.

CREATE TABLE IF NOT EXISTS escalation_records (
    id VARCHAR(36) PRIMARY KEY,
    policy_id VARCHAR(36) NOT NULL REFERENCES escalation_policies(id),
    session_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    agent_id VARCHAR(36) NOT NULL,

    -- The node that triggered escalation
    node_id VARCHAR(36) NOT NULL,
    node_kind VARCHAR(50) NOT NULL,
    node_label VARCHAR(255) NOT NULL,
    node_content JSONB NOT NULL DEFAULT '{}',
    node_confidence_value REAL,
    node_confidence_source VARCHAR(50),
    node_capabilities TEXT[] DEFAULT '{}',

    -- Resolution state
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','timed_out','aborted')),
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    resolution_reason TEXT,
    resolution_signature TEXT,

    -- Timing
    escalated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timeout_at TIMESTAMPTZ NOT NULL,
    timed_out BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_escalation_pending
    ON escalation_records (project_id, status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_escalation_session
    ON escalation_records (session_id);
CREATE INDEX IF NOT EXISTS idx_escalation_policy
    ON escalation_records (policy_id);
CREATE INDEX IF NOT EXISTS idx_escalation_timeout
    ON escalation_records (timeout_at) WHERE status = 'pending';

-- ── Approval Audit Log ────────────────────────────────────────────
-- Strictly append-only. Every state transition on an escalation record
-- is logged here with an HMAC signature for non-repudiation. This is
-- the artifact a compliance officer or auditor reviews.

CREATE TABLE IF NOT EXISTS approval_audit_log (
    id BIGSERIAL PRIMARY KEY,
    escalation_id VARCHAR(36) NOT NULL REFERENCES escalation_records(id),
    action VARCHAR(50) NOT NULL
        CHECK (action IN ('created','approved','rejected','timed_out','aborted','escalated_to_channel')),
    actor VARCHAR(255) NOT NULL,
    reason TEXT,
    -- HMAC-SHA256(actor|action|timestamp|escalation_id, project_signing_secret)
    signature TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_escalation
    ON approval_audit_log (escalation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor
    ON approval_audit_log (actor, created_at);

-- ── Project Signing Secrets ───────────────────────────────────────
-- Per-project HMAC signing key for approval signatures.
-- Stored hashed — the raw key is returned only at creation time.

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS signing_secret TEXT,
    ADD COLUMN IF NOT EXISTS escalation_enabled BOOLEAN DEFAULT false;

-- ── Replay Cache + Causal Findings Immutability ───────────────────
-- For existing tables from 001_init.sql that hold audit-critical data:
-- We add the replay_cache table if it doesn't exist from prior schema,
-- and enforce append-only semantics on audit tables.

CREATE TABLE IF NOT EXISTS replay_cache (
    node_id TEXT PRIMARY KEY REFERENCES runtime_nodes(id),
    input_snapshot JSONB NOT NULL,
    output_snapshot JSONB NOT NULL,
    deterministic BOOLEAN NOT NULL DEFAULT false,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS causal_findings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    failure_node_id TEXT NOT NULL,
    candidate_node_id TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('ablation','structural_heuristic')),
    score REAL NOT NULL,
    explanation TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_diffs (
    id TEXT PRIMARY KEY,
    session_a_id TEXT NOT NULL,
    session_b_id TEXT NOT NULL,
    divergence_node_id TEXT,
    edit_distance REAL NOT NULL,
    diff_summary JSONB NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Seed: Default Escalation Policy ───────────────────────────────
-- A sensible default policy for the demo project.

INSERT INTO escalation_policies (
    id, project_id, name, description,
    trigger_capabilities, trigger_action_types,
    trigger_confidence_below, trigger_confidence_source,
    resolution_channel, timeout_seconds, timeout_behavior,
    required_approvers, audit_requirement, priority
) VALUES (
    'pol_default_financial', 'proj_alpha',
    'High-risk financial actions',
    'Escalate any financial transaction or refund where the agent confidence is below 0.7',
    '{"is_decision_point"}', '{"financial_transaction","refund","payment"}',
    0.7, 'self_reported',
    'in_app_queue', 300, 'block',
    1, 'reasoned', 10
) ON CONFLICT (id) DO NOTHING;

INSERT INTO escalation_policies (
    id, project_id, name, description,
    trigger_capabilities,
    trigger_confidence_below, trigger_confidence_source,
    resolution_channel, timeout_seconds, timeout_behavior,
    required_approvers, audit_requirement, priority
) VALUES (
    'pol_low_confidence', 'proj_alpha',
    'Low-confidence decisions',
    'Flag any decision point with self-reported confidence below 0.5',
    '{"is_decision_point"}',
    0.5, 'self_reported',
    'in_app_queue', 600, 'proceed_with_flag',
    1, 'reasoned', 50
) ON CONFLICT (id) DO NOTHING;

-- Update the default project with a signing secret
UPDATE projects SET
    signing_secret = encode(gen_random_bytes(32), 'hex'),
    escalation_enabled = true
WHERE id = 'proj_alpha' AND signing_secret IS NULL;
