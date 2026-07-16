"""
VERI SDK Verification — validates the full capture loop + L0 guardrails.

Run: python verify_sdk.py
"""

import sys
import os
import time

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages", "evolution-sdk-python"))

import veri
from veri.context import ExecutionSpanScope, active_session_context, VeriCostLimitExceeded


# ── Mock the HTTP transport so we can inspect payloads ──────────────

captured_batches = []


class MockResponse:
    status_code = 200


def mock_post(url, json=None, headers=None, timeout=None):
    captured_batches.append(json)
    event_count = len(json.get("events", []))
    print(f"  [INGEST] Received batch of {event_count} event(s)")
    for event in json["events"]:
        etype = event.get("type", "?")
        name = event.get("name", "")
        label = f" ({name})" if name else ""
        print(f"    → {etype}{label}")
    return MockResponse()


import requests
requests.post = mock_post


# ── Test 1: Basic session + span tracking ───────────────────────────

print("=" * 60)
print("TEST 1: Session lifecycle + span hierarchy")
print("=" * 60)

veri.init(
    api_key="vk_test_key_001",
    cost_limit=10.00,
    call_limit=100,
)

with veri.session(session_id="sess_001", agent_id="support_v3", project_id="proj_alpha") as session:
    client = veri.get_client()

    # Simulate a reasoning step with nested tool call
    with ExecutionSpanScope(client, "reasoning", "plan_response", {"query": "What is my order status?"}) as reasoning:
        time.sleep(0.02)

        # Nested tool call
        with ExecutionSpanScope(client, "tool", "order_lookup", {"id": 4521}) as tool:
            time.sleep(0.01)
            tool.complete(
                output_data={"status": "shipped", "tracking": "1Z999AA1"},
                metrics={"latency_ms": 45}
            )

        reasoning.complete(output_data={"response": "Your order has shipped!"})

print("\n✅ Test 1 passed — session and span lifecycle working.\n")

# Clean up for next test
veri.reset()
time.sleep(0.6)  # Let worker flush


# ── Test 2: L0 guardrail enforcement ────────────────────────────────

print("=" * 60)
print("TEST 2: L0 cost limit circuit breaker")
print("=" * 60)

veri.init(
    api_key="vk_test_key_002",
    cost_limit=0.001,  # Extremely tight budget
    call_limit=5,
)

l0_triggered = False

try:
    with veri.session(session_id="sess_002", agent_id="runaway_agent", project_id="proj_alpha") as session:
        # Simulate expensive operations
        for i in range(10):
            session.increment_and_verify_l0(cost_delta=0.0005)
            print(f"  Call {i+1}: cost=${session.total_cost_usd:.4f}, calls={session.llm_call_count}")
except VeriCostLimitExceeded as e:
    l0_triggered = True
    print(f"\n  🔒 L0 TRIGGERED: {e}")

assert l0_triggered, "L0 guardrail should have triggered!"
print("\n✅ Test 2 passed — L0 cost circuit breaker working.\n")

veri.reset()
time.sleep(0.6)


# ── Test 3: Safe serialization boundary ─────────────────────────────

print("=" * 60)
print("TEST 3: Non-serializable object handling")
print("=" * 60)

from veri.context import safe_serialize
import json

# Normal types
assert json.loads(safe_serialize("hello")) == "hello"
assert json.loads(safe_serialize(42)) == 42
assert json.loads(safe_serialize(None)) is None
print("  ✓ Primitives serialize correctly")

# Dict with nested types
result = safe_serialize({"a": 1, "b": [2, 3], "c": {"d": True}})
parsed = json.loads(result)
assert parsed == {"a": 1, "b": [2, 3], "c": {"d": True}}
print("  ✓ Nested dicts serialize correctly")

# Non-serializable object (simulating a DB cursor)
class FakeDBCursor:
    def __init__(self):
        self._internal_buffer = bytearray(1024)
    def __repr__(self):
        return "<FakeDBCursor connected=True rows=42>"

cursor = FakeDBCursor()
result = safe_serialize(cursor)
parsed = json.loads(result)
assert parsed["__veri_unserializable__"] is True
assert parsed["type"] == "FakeDBCursor"
assert "connected=True" in parsed["repr"]
print(f"  ✓ Non-serializable object fingerprinted: {parsed['type']}")

print("\n✅ Test 3 passed — serialization boundary is safe.\n")


# ── Summary ─────────────────────────────────────────────────────────

print("=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
total_events = sum(len(b.get("events", [])) for b in captured_batches)
print(f"Total events captured: {total_events}")
print(f"Total batches sent: {len(captured_batches)}")
