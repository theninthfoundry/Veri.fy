"""
VERI CLI Tool — The command-line interface for running and recording golden tests.

Provides:
  - `veri test`: runs local/remote golden test suites.
  - `veri record`: records new test fixtures from target environments.

Usage:
  veri test --agent support-v3
  veri record --agent support-v3 --env staging --input "query"
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Any, List

# Add path to load local veri module if running from source
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from veri.matcher import Fixture, FixtureStore
from veri.assertions import (
    ResponseAssertionEngine,
    check_tools_called,
    check_tools_not_called,
    check_token_budget,
    check_cost_budget,
    check_latency,
    AssertionStatus,
)


def load_local_tests(agent_id: str) -> List[Dict[str, Any]]:
    """Loads tests from local storage directory .veri/tests/."""
    test_dir = os.path.join(".veri", "tests", agent_id)
    if not os.path.exists(test_dir):
        return []

    tests = []
    for filename in os.listdir(test_dir):
        if filename.endswith(".json"):
            path = os.path.join(test_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tests.append(json.load(f))
            except Exception as e:
                print(f"⚠️ Failed to load test file {filename}: {e}", file=sys.stderr)
    return tests


def save_local_test(agent_id: str, test_data: Dict[str, Any]) -> str:
    """Saves a test case to local storage."""
    test_dir = os.path.join(".veri", "tests", agent_id)
    os.makedirs(test_dir, exist_ok=True)
    test_id = test_data.get("id", f"test_{int(time.time())}")
    path = os.path.join(test_dir, f"{test_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2)
    return path


def run_test_case(test: Dict[str, Any], agent_runner_fn) -> Dict[str, Any]:
    """
    Executes a single test case against the agent runner function using frozen fixtures.
    """
    print(f"\n🏃 Running test: {test.get('name', 'Unnamed Test')} ({test.get('id')})")
    print(f"   Input: \"{test.get('input')}\"")

    # Load pre-recorded fixtures into a temporary store
    fixtures_data = test.get("fixtures", [])
    fixture_store = FixtureStore()
    fixture_list = []
    for f in fixtures_data:
        fixture_list.append(Fixture(
            tool_name=f["tool_name"],
            input=f.get("input", {}),
            output=f.get("output"),
            source_session_id=f.get("source_session_id")
        ))
    fixture_store.load_from_dict([
        {
            "tool_name": f.tool_name,
            "input": f.input,
            "output": f.output,
            "source_session_id": f.source_session_id
        } for f in fixture_list
    ])
    matcher = fixture_store.get_matcher()

    # Track actual behavior during run
    actual_tool_calls = []
    tool_metrics = {"tokens_input": 0, "tokens_output": 0, "cost_usd": 0.0}

    # Intercept tool calls using mock implementation matching fixtures
    def mocked_tool_executor(tool_name: str, tool_input: Dict[str, Any]) -> Any:
        actual_tool_calls.append(tool_name)
        match_res = matcher.match(tool_name, tool_input)

        if match_res.matched:
            # Found a fuzzy matched fixture
            status_symbol = {
                "exact": "✅ [Exact]",
                "structural": "⚠️ [Structural]",
                "intent": "⚠️ [Intent]"
            }.get(match_res.status, "❓")
            print(f"   {status_symbol} Tool Call '{tool_name}' matched (Conf: {match_res.confidence:.2f})")
            return match_res.fixture.output

        if match_res.is_evolution:
            print(f"   ❌ [Evolution] Tool Call '{tool_name}' has no fixtures.")
            raise RuntimeError(f"UnmockedToolError: No fixture available for tool '{tool_name}'")

        print(f"   ❌ [Unmatched] Tool Call '{tool_name}' arguments did not match any fixtures.")
        raise RuntimeError(f"UnmatchedToolError: Fixture lookup failed for tool '{tool_name}' with args {tool_input}")

    # Run the agent (injecting our mock tool executor)
    start_time = time.time()
    try:
        actual_response = agent_runner_fn(test.get("input"), mocked_tool_executor)
        latency_ms = int((time.time() - start_time) * 1000)
        success = True
        error_msg = None
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        success = False
        actual_response = ""
        error_msg = str(e)

    # Compile results
    results = {
        "test_id": test.get("id"),
        "name": test.get("name"),
        "success": success,
        "latency_ms": latency_ms,
        "error": error_msg,
        "assertions": []
    }

    if not success:
        results["assertions"].append({
            "name": "ExecutionStatus",
            "status": "fail",
            "message": f"Agent crashed during test execution: {error_msg}"
        })
        return results

    # Evaluate Assertions
    # 1. Three-Layer Response Assertion
    assertion_engine = ResponseAssertionEngine()
    golden_response = test.get("golden_response", "")
    response_result = assertion_engine.evaluate(golden_response, actual_response)

    for lr in response_result.layers:
        results["assertions"].append({
            "name": f"Response_{lr.layer}",
            "status": lr.status.value,
            "message": lr.message,
            "details": lr.details
        })

    # 2. Tools Called Check
    expected_tools = [f["tool_name"] for f in fixtures_data]
    tools_res = check_tools_called(expected_tools, actual_tool_calls)
    results["assertions"].append({
        "name": tools_res.name,
        "status": tools_res.status.value,
        "message": tools_res.message,
        "details": tools_res.details
    })

    # 3. Forbidden Tools Safety Check
    forbidden_tools = test.get("forbidden_tools", [])
    safety_res = check_tools_not_called(forbidden_tools, actual_tool_calls)
    results["assertions"].append({
        "name": safety_res.name,
        "status": safety_res.status.value,
        "message": safety_res.message,
        "details": safety_res.details
    })

    # 4. Latency Check
    max_latency = test.get("max_latency_ms", 10000)
    latency_res = check_latency(max_latency, latency_ms)
    results["assertions"].append({
        "name": latency_res.name,
        "status": latency_res.status.value,
        "message": latency_res.message,
        "details": latency_res.details
    })

    # Update overall test success status based on assertions
    all_passed = True
    for ass in results["assertions"]:
        if ass["status"] == "fail":
            all_passed = False
            break
    results["success"] = all_passed

    return results


def cmd_test(args):
    """Runs tests for the specified agent."""
    print(f"🔍 Loading test suite for agent: {args.agent}")
    tests = load_local_tests(args.agent)
    if not tests:
        print(f"❌ No local tests found for agent '{args.agent}'. Use 'veri record' to create one.")
        sys.exit(1)

    print(f"📋 Found {len(tests)} test case(s). Starting execution...")

    # Mock agent runner function for CLI demonstration
    # In actual production, this would import and run the customer's actual agent code.
    def mock_agent_runner(user_input: str, tool_executor_fn) -> str:
        # Example dynamic simulation based on inputs
        if "order" in user_input.lower():
            # Trigger lookup tool call
            res = tool_executor_fn("order_lookup", {"id": 4521})
            return f"Your order is currently {res.get('status')}. Tracking number: {res.get('tracking')}"
        elif "refund" in user_input.lower():
            res = tool_executor_fn("refund_check", {"order_id": 8832, "reason": "defective"})
            if res.get("eligible"):
                return f"Your refund request of ${res.get('amount')} has been approved."
            return "You are not eligible for a refund."
        return "How can I help you today?"

    passed_count = 0
    failed_count = 0

    for test in tests:
        res = run_test_case(test, mock_agent_runner)
        if res["success"]:
            passed_count += 1
            print(f"✅ PASS: {res['name']} ({res['latency_ms']}ms)")
        else:
            failed_count += 1
            print(f"❌ FAIL: {res['name']} ({res['latency_ms']}ms)")
            for ass in res["assertions"]:
                if ass["status"] == "fail":
                    print(f"   ↳ ❌ {ass['name']}: {ass['message']}")
                elif ass["status"] == "warn":
                    print(f"   ↳ ⚠️ {ass['name']}: {ass['message']}")

    print("\n" + "=" * 50)
    print(f"📊 TEST RUN SUMMARY: {passed_count} Passed | {failed_count} Failed")
    print("=" * 50)

    if failed_count > 0:
        sys.exit(1)


def cmd_record(args):
    """Records a new test case by running the agent live and saving fixtures."""
    print(f"⏺️  Recording execution on environment: {args.env}")
    print(f"   Input: \"{args.input}\"")

    # In actual usage, this executes the live agent in staging/dev and intercepts calls.
    # Here, we generate a synthetic golden test case for demonstration.
    test_id = f"test_{int(time.time())}"
    simulated_test = {
        "id": test_id,
        "name": f"Recorded transaction: {args.input[:30]}...",
        "input": args.input,
        "golden_response": "Your order is currently shipped. Tracking number: 1Z999AA1",
        "max_latency_ms": 5000,
        "forbidden_tools": ["delete_order"],
        "fixtures": [
            {
                "tool_name": "order_lookup",
                "input": {"id": 4521},
                "output": {"status": "shipped", "tracking": "1Z999AA1"},
                "source_session_id": f"sess_rec_{test_id}"
            }
        ]
    }

    path = save_local_test(args.agent, simulated_test)
    print(f"💾 Successfully recorded and saved new golden test case to: {path}")


def main():
    parser = argparse.ArgumentParser(description="VERI: CI/CD & Quality Infrastructure for AI Agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Test parser
    parser_test = subparsers.add_parser("test", help="Run golden test suite")
    parser_test.add_argument("--agent", required=True, help="Target Agent ID")
    parser_test.add_argument("--env", default="local", help="Testing environment")

    # Record parser
    parser_record = subparsers.add_parser("record", help="Record execution to create golden test")
    parser_record.add_argument("--agent", required=True, help="Target Agent ID")
    parser_record.add_argument("--env", required=True, help="Target environment (staging/dev)")
    parser_record.add_argument("--input", required=True, help="User input query to run")

    args = parser.parse_args()

    if args.command == "test":
        cmd_test(args)
    elif args.command == "record":
        cmd_record(args)


if __name__ == "__main__":
    main()
