# 🐍 VERI SDK (Python Client)

> **The Python client for BehaviorOS. Instrument, track, contract-protect, and analyze autonomous agent execution trees.**

---

## 🚀 Key Features

*   **🌳 Dynamic Behavior Graph**: Compiles execution history into parent-child trace graphs.
*   **🛡️ Executable Behavioral Contracts**: Intercept and evaluate agent actions at runtime using the `@behavior_contract` decorator.
*   **🔐 Cryptographic Fingerprinting**: Deterministically snapshot system dependencies, model parameters, and prompts to identify environment drift.
*   **🔄 True Causal Replay**: Verify and pinpoint exactly which upstream node caused a downstream failure using in-process baseline-substitution replay.
*   **🔒 In-Memory L0 Circuit Breakers**: Cost and call limiters evaluated with sub-microsecond latency to prevent runaway agents.
*   **🔌 Auto-Instrumentation**: Instantly capture traces from `openai` and `langchain`.

---

## 📦 Installation

```bash
pip install -e .
```

---

## ⚡ Integration Guide

### 1. Initialize and Instrument
Initialize VERI and hook agent libraries at your application's entry point:

```python
import veri

# 1. Initialize global client with L0 budget limits
veri.init(
    api_key="your_veri_api_key",
    cost_limit=5.00,  # Limit spend to $5.00 per session
    call_limit=50     # Kill session if LLM calls exceed 50
)

# 2. Automatically patch OpenAI / LangChain
veri.instrument(["openai", "langchain"])
```

### 2. Wrap Tools with Behavioral Contracts
Protect critical real-world integrations (payments, system commands, database updates) by declaring explicit contracts:

```python
from veri.contracts import behavior_contract

@behavior_contract(
    max_price=500.0, 
    allowed_country="Japan", 
    human_required=True
)
def purchase_ticket(price: float, country: str):
    # Enforced at runtime: values exceeding max_price or outside allowed_country will raise ContractViolations
    print(f"Purchasing ticket to {country} for ${price}...")
```

### 3. Record Sessions & Spans
Capture the cognitive flow and tools execution under a tracked session context:

```python
from veri.context import ExecutionSpanScope

with veri.session(session_id="session_001", agent_id="travel_planner_v2", project_id="proj_alpha") as session:
    client = veri.get_client()

    # Track a planning reasoning span
    with ExecutionSpanScope(client, "reasoning", "route_planner") as span:
        # Run agent logic
        flight_info = purchase_ticket(450.0, "Japan")
        
        # Complete reasoning span
        span.complete(flight_info)
```

### 4. Diagnose Failures via Replay
If a session fails, isolate the causal culprit against a known golden baseline run:

```python
# Returns the ID of the specific node that caused the regression
culprit_id = session.analyze_failure(baseline_session_id="sess_golden_001")
if culprit_id:
    print(f"Causal failure isolated! Culprit node ID: {culprit_id}")
```
