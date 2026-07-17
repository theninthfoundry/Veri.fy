from veri.fingerprint import RuntimeFingerprint, capture_current_fingerprint
from veri.contracts import BehaviorContract
from veri.lineage import BehaviorBOM

def test_runtime_fingerprint():
    # Capture a baseline fingerprint
    fp1 = RuntimeFingerprint(
        prompt_templates={"query": "Draft refund for {amount}"},
        model_parameters={"model": "gpt-4o-mini", "temperature": 0.0},
        tool_schemas={"refund_tool": {"properties": {"amount": "number"}}},
        environment_packages=["requests", "pyyaml"]
    )
    
    # Capture a matching fingerprint
    fp2 = RuntimeFingerprint(
        prompt_templates={"query": "Draft refund for {amount}"},
        model_parameters={"model": "gpt-4o-mini", "temperature": 0.0},
        tool_schemas={"refund_tool": {"properties": {"amount": "number"}}},
        environment_packages=["requests", "pyyaml"]
    )
    
    # Capture a drifted fingerprint
    fp3 = RuntimeFingerprint(
        prompt_templates={"query": "Draft refund for {amount} immediately"},
        model_parameters={"model": "gpt-4o-mini", "temperature": 0.5}, # Drifted temperature and prompt
        tool_schemas={"refund_tool": {"properties": {"amount": "number"}}},
        environment_packages=["requests", "pyyaml"]
    )
    
    assert fp1.hash == fp2.hash
    assert fp1.hash != fp3.hash
    print("Runtime Fingerprint hashes verify correctly.")

def test_behavioral_contracts():
    contract = BehaviorContract(
        max_cost=10.0,
        forbidden_tools=["delete_account"],
        required_explanations=["refund_check"],
        tool_value_constraints={
            "refund_check": [
                {"field": "amount", "operator": "lt", "value": 1000}
            ]
        }
    )

    # 1. Clean trace
    nodes_ok = [
        {"id": "n1", "category": "tool", "name": "refund_check", "content": {"input": {"amount": 450}, "explanation": "Defective item"}, "metrics": {"cost_usd": 0.005}}
    ]
    violations = contract.verify_trace(nodes_ok)
    assert len(violations) == 0

    # 2. Trace with forbidden tool and budget violation
    nodes_bad = [
        {"id": "n1", "category": "tool", "name": "delete_account", "content": {}, "metrics": {"cost_usd": 0.05}},
        {"id": "n2", "category": "tool", "name": "refund_check", "content": {"input": {"amount": 1200}}, "metrics": {"cost_usd": 12.50}}
    ]
    violations = contract.verify_trace(nodes_bad)
    assert len(violations) == 3
    rules = [v.rule for v in violations]
    assert "forbidden_tools" in rules
    assert "max_cost" in rules
    assert "value_constraint.amount" in rules
    print("Behavioral contracts flag violations correctly.")

def test_behavioral_bom_lineage():
    nodes = [
        {"id": "n_retrieval", "category": "observation", "name": "doc_lookup", "content": {"output": "User has policy coverage."}},
        {"id": "n_memory", "category": "belief", "name": "conversation_history", "content": {"output": "User wants a refund."}},
        {"id": "n_llm", "category": "llm", "name": "refund_processor", "metrics": {"model": "gpt-4o-mini", "cost_usd": 0.002}, "content": {"prompt_hash": "abc123hash", "output": "Approved"}}
    ]
    
    edges = [
        {"source": "n_retrieval", "target": "n_llm", "kind": "depends_on"},
        {"source": "n_memory", "target": "n_llm", "kind": "depends_on"}
    ]

    bom = BehaviorBOM(nodes, edges)
    lineage = bom.get_lineage("n_llm")
    
    comp = lineage.get("components", {})
    assert len(comp["retrievals"]) == 1
    assert comp["retrievals"][0]["source"] == "doc_lookup"
    assert len(comp["memories"]) == 1
    assert comp["memories"][0]["key"] == "conversation_history"
    assert len(comp["models"]) == 1
    assert comp["models"][0]["model"] == "gpt-4o-mini"
    print("Behavioral BOM computes dependency lineage correctly.")

from veri.contracts import behavior_contract
from veri.fingerprint import compute_behavior_hash

def test_behavior_contract_decorator():
    # Define a tool with contracts
    @behavior_contract(max_price=1000.0, allowed_country="Japan")
    def book_flight(price: float, country: str):
        return f"Flight booked to {country} for ${price}"

    # 1. Matches constraints (should pass)
    res = book_flight(450.00, "Japan")
    assert "booked to Japan" in res

    # 2. Exceeds max price (should fail)
    try:
        book_flight(1200.00, "Japan")
        assert False, "Should have raised Contract Violation for price"
    except ValueError as e:
        assert "Contract Violation: Price" in str(e)

    # 3. Destination country not allowed (should fail)
    try:
        book_flight(450.00, "France")
        assert False, "Should have raised Contract Violation for country"
    except ValueError as e:
        assert "Contract Violation: Country" in str(e)

    print("behavior_contract decorator enforces assertions successfully.")

def test_behavior_hash_generation():
    h1 = compute_behavior_hash(
        planner_steps=["search", "rank", "ask", "book"],
        tool_sequence=["search_flights", "rank_results", "ask_confirmation", "book_flight"],
        decision_order=["option_1", "ask", "option_1"],
        constraints=["max_price=1000"],
        memory_usage=["user_pref_saved"]
    )
    h2 = compute_behavior_hash(
        planner_steps=["search", "rank", "ask", "book"],
        tool_sequence=["search_flights", "rank_results", "ask_confirmation", "book_flight"],
        decision_order=["option_1", "ask", "option_1"],
        constraints=["max_price=1000"],
        memory_usage=["user_pref_saved"]
    )
    h3 = compute_behavior_hash(
        planner_steps=["search", "rank", "book"], # askConfirmation skipped!
        tool_sequence=["search_flights", "rank_results", "book_flight"],
        decision_order=["option_1", "option_1"],
        constraints=["max_price=1000"],
        memory_usage=["user_pref_saved"]
    )

    assert h1 == h2
    assert h1 != h3
    print("compute_behavior_hash detects behavioral drifts successfully.")
