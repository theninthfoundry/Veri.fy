-- ClickHouse Ingestion Schema for telemetry streams.

CREATE DATABASE IF NOT EXISTS veri;

CREATE TABLE IF NOT EXISTS veri.events (
    id String,
    parent_span_id String DEFAULT '',
    span_id String DEFAULT '',
    project_id String,
    agent_id String,
    session_id String,
    category LowCardinality(String), -- e.g., system, llm, tool, reasoning
    type LowCardinality(String),     -- e.g., session.started, tool.started, llm.completed
    name String DEFAULT '',           -- e.g., openai.gpt-4o, order_lookup
    payload String DEFAULT '{}',      -- raw inputs/outputs (graceful json strings)
    
    -- Metrics
    latency_ms UInt32 DEFAULT 0,
    cost_usd Decimal(10, 8) DEFAULT 0.0,
    tokens_input UInt32 DEFAULT 0,
    tokens_output UInt32 DEFAULT 0,
    
    timestamp DateTime64(3, 'UTC')
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_id, agent_id, session_id, timestamp);
