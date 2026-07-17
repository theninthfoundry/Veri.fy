-- PostgreSQL Initial Schema for VERI metadata and configuration management.

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_suites (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS golden_tests (
    id VARCHAR(36) PRIMARY KEY,
    suite_id VARCHAR(36) NOT NULL REFERENCES test_suites(id) ON DELETE CASCADE,
    input TEXT NOT NULL,
    golden_response TEXT NOT NULL,
    fixtures JSONB NOT NULL DEFAULT '[]', -- List of fuzzy matched tool expectations
    assertions JSONB NOT NULL DEFAULT '[]', -- Expected metrics, forbidden/required tools
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review', -- pending_review, active, archived
    success_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suggestions (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL, -- e.g., loop.identical_tool_calls, cost.anomaly
    finding_message TEXT NOT NULL,
    fix_description TEXT NOT NULL,
    config_diff TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, merged, dismissed
    risk_level VARCHAR(10) NOT NULL DEFAULT 'L1',
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Project for verify demo
INSERT INTO projects (id, name) VALUES ('proj_alpha', 'Default Workspace') ON CONFLICT DO NOTHING;
INSERT INTO agents (id, project_id, name) VALUES ('support-v3', 'proj_alpha', 'Support Agent Agent') ON CONFLICT DO NOTHING;
INSERT INTO test_suites (id, agent_id, name) VALUES ('suite_alpha', 'support-v3', 'Regression Golden Suite') ON CONFLICT DO NOTHING;

-- ── Runtime IR Tables ──

CREATE TABLE IF NOT EXISTS runtime_nodes (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    kind VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    confidence NUMERIC(5, 4),
    uncertainty NUMERIC(5, 4),
    assumptions TEXT[] DEFAULT '{}',
    evidence TEXT[] DEFAULT '{}',
    cost_usd NUMERIC(10, 6) DEFAULT 0.0,
    latency_ms INTEGER DEFAULT 0,
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- v2 additions
    confidence_value REAL,
    confidence_source TEXT CHECK (confidence_source IN ('measured','self_reported','derived','unavailable')),
    confidence_method TEXT,
    capabilities TEXT[] DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_nodes_session ON runtime_nodes (session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_nodes_project_agent ON runtime_nodes (project_id, agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON runtime_nodes (kind);
CREATE INDEX IF NOT EXISTS idx_nodes_confidence ON runtime_nodes (confidence) WHERE confidence IS NOT NULL;

CREATE TABLE IF NOT EXISTS runtime_edges (
    id VARCHAR(36) PRIMARY KEY,
    source_id VARCHAR(36) NOT NULL,
    target_id VARCHAR(36) NOT NULL,
    kind VARCHAR(50) NOT NULL,
    weight NUMERIC(5, 4) DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    session_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- v2 addition
    edge_confidence_source TEXT NOT NULL DEFAULT 'inferred' CHECK (edge_confidence_source IN ('measured','inferred'))
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON runtime_edges (source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON runtime_edges (target_id);
CREATE INDEX IF NOT EXISTS idx_edges_session ON runtime_edges (session_id);

CREATE TABLE IF NOT EXISTS runtime_frames (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    agent_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    active_goals TEXT[] DEFAULT '{}',
    active_beliefs TEXT[] DEFAULT '{}',
    active_plan TEXT[] DEFAULT '{}',
    working_memory TEXT[] DEFAULT '{}',
    total_cost NUMERIC(10, 6) DEFAULT 0.0,
    total_latency INTEGER DEFAULT 0,
    overall_confidence NUMERIC(5, 4),
    overall_risk NUMERIC(5, 4),
    nodes_added TEXT[] DEFAULT '{}',
    nodes_removed TEXT[] DEFAULT '{}',
    beliefs_changed TEXT[] DEFAULT '{}',
    confidence_deltas JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_frames_session ON runtime_frames (session_id, timestamp);

CREATE TABLE IF NOT EXISTS state_deltas (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    before_state JSONB DEFAULT '{}',
    after_state JSONB DEFAULT '{}',
    significance NUMERIC(5, 4) NOT NULL,
    source_node_ids TEXT[] DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_deltas_session ON state_deltas (session_id, timestamp);

CREATE TABLE IF NOT EXISTS predictions (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    probability NUMERIC(5, 4) NOT NULL,
    confidence NUMERIC(5, 4) NOT NULL,
    horizon_steps INTEGER,
    explanation TEXT NOT NULL,
    evidence JSONB DEFAULT '[]',
    counterfactual TEXT,
    suggested_action TEXT,
    method VARCHAR(50) NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    resolution TEXT,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_session ON predictions (session_id, computed_at);
CREATE INDEX IF NOT EXISTS idx_predictions_unresolved ON predictions (resolved) WHERE NOT resolved;

CREATE TABLE IF NOT EXISTS optimizations (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    cost_reduction NUMERIC(10, 6) DEFAULT 0.0,
    latency_reduction INTEGER DEFAULT 0,
    quality_impact NUMERIC(5, 4) DEFAULT 0.0,
    confidence NUMERIC(5, 4) NOT NULL,
    affected_node_ids TEXT[] DEFAULT '{}',
    applied BOOLEAN DEFAULT FALSE,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_optimizations_session ON optimizations (session_id);

CREATE TABLE IF NOT EXISTS simulations (
    id VARCHAR(36) PRIMARY KEY,
    prediction_id VARCHAR(36) REFERENCES predictions(id) ON DELETE CASCADE,
    optimization_id VARCHAR(36) REFERENCES optimizations(id) ON DELETE CASCADE,
    fix_payload JSONB NOT NULL DEFAULT '{}',
    evaluated_score NUMERIC(5, 4) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed', -- pending, running, completed, failed
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_simulations_prediction ON simulations (prediction_id);
CREATE INDEX IF NOT EXISTS idx_simulations_optimization ON simulations (optimization_id);
