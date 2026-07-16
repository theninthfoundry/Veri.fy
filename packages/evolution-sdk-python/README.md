# VERI SDK (Python)

The Python implementation of the VERI agent engineering hypervisor client. 

Provides:
- Thread-safe, async-safe context logging.
- Auto-instrumentation monkey-patches for `openai` and `langchain`.
- Local L0 guardrails (cost/call limiters) evaluated completely in-memory with sub-microsecond latency.
- Dynamic parent-child trace execution hierarchies.

## Installation

```bash
pip install -e .
```

## Integration

Initialize VERI at your agent's entry point:

```python
import veri

# 1. Initialize
veri.init(
    api_key="your_api_key",
    cost_limit=5.00,  # Max session spend
    call_limit=50     # Max LLM steps
)

# 2. Hook frameworks
veri.instrument(["openai", "langchain"])

# 3. Track Sessions
with veri.session(session_id="session_abc", agent_id="support_bot", project_id="proj_1"):
    # Run agent code here
    # All LLM requests, tool calls, and inputs/outputs are captured automatically.
```
