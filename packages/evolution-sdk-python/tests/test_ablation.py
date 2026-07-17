from veri.context import AgentSessionContext, ExecutionSpanScope
import veri

class MockClient:
    def emit_async(self, data):
        pass

def test_causal_ablation_baseline_substitution():
    client = MockClient()
    
    # Initialize SDK
    try:
        veri.init(api_key="test_key_xyz", disabled=True)
    except ValueError:
        pass
    
    # 1. Run baseline session
    baseline_id = "sess_baseline_001"
    
    def tool_replay_fn(inp, *args, **kwargs):
        return "correct_data" if inp == "input_ok" else "buggy_data"
        
    with AgentSessionContext(
        client=client,
        session_id=baseline_id,
        agent_id="test_agent",
        project_id="test_project",
        cost_limit=10.0,
        call_limit=100
    ) as session:
        with ExecutionSpanScope(
            client=client,
            category="tool",
            name="data_fetcher",
            input_data="input_ok",
            replay_fn=tool_replay_fn,
            capabilities=["is_replayable"]
        ) as span:
            tool_output = "correct_data"
            tool_ref = span.complete(tool_output)
            
        with ExecutionSpanScope(
            client=client,
            category="llm",
            name="response_generator",
            input_data=f"Process: {tool_ref}"
        ) as span:
            final_output = "Success: correct_data"
            span.complete(final_output)

    # 2. Run experimental session with injected bug
    experimental_id = "sess_experimental_001"
    with AgentSessionContext(
        client=client,
        session_id=experimental_id,
        agent_id="test_agent",
        project_id="test_project",
        cost_limit=10.0,
        call_limit=100
    ) as session_exp:
        with ExecutionSpanScope(
            client=client,
            category="tool",
            name="data_fetcher",
            input_data="input_bad",  # Bug injected
            replay_fn=tool_replay_fn,
            capabilities=["is_replayable"]
        ) as span:
            tool_output = "buggy_data"
            tool_ref = span.complete(tool_output)
            
        with ExecutionSpanScope(
            client=client,
            category="llm",
            name="response_generator",
            input_data=f"Process: {tool_ref}"
        ) as span:
            final_output = "Failure: buggy_data"
            span.complete(final_output)

        # 3. Analyze failure
        culprit_id = session_exp.analyze_failure(baseline_id)
        
        assert culprit_id is not None
        culprit_node = session_exp.replay_graph.nodes[culprit_id]
        assert culprit_node.name == "data_fetcher"
