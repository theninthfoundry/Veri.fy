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
