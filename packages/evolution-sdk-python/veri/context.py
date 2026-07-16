"""
VERI Session & Span Context — The operational core.

Tracks hierarchical execution state via contextvars (async-safe),
computes parent-child span relationships dynamically, and enforces
L0 circuit-breakers (cost limit, call limit) entirely in-process
with zero network round-trips.
"""

import json
import time
import contextvars
import threading
from typing import Any, Dict, List, Optional, Tuple

import ulid


# ── L0 Guardrail Exceptions ────────────────────────────────────────


class VeriL0Exception(Exception):
    """Base exception for L0 circuit-breaker activations."""

    pass


class VeriCostLimitExceeded(VeriL0Exception):
    """Raised when session USD spend exceeds the configured cap."""

    pass


class VeriCallLimitExceeded(VeriL0Exception):
    """Raised when LLM call count exceeds the configured cap."""

    pass


# ── Thread-Safe Context Variables ──────────────────────────────────

active_session_context: contextvars.ContextVar[Optional["AgentSessionContext"]] = (
    contextvars.ContextVar("veri_active_session", default=None)
)
active_span_stack: contextvars.ContextVar[List[Tuple[str, str]]] = contextvars.ContextVar(
    "veri_span_stack", default=[]
)


# ── Serialization Boundary ─────────────────────────────────────────


def safe_serialize(obj: Any) -> str:
    """
    Graceful serialization — never crashes, always produces useful output.

    For serializable objects: returns JSON string.
    For non-serializable objects (DB cursors, file handles, class instances):
    returns a fingerprint with type, truncated repr, and object id.
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return json.dumps(obj)

    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError):
        pass

    return json.dumps(
        {
            "__veri_unserializable__": True,
            "type": type(obj).__name__,
            "repr": repr(obj)[:250],
            "id": id(obj),
        }
    )


# ── Session Context ────────────────────────────────────────────────


class AgentSessionContext:
    """
    Tracks a single agent execution session. Manages:
    - Hierarchical span relationships (parent-child via stack)
    - Cumulative cost and call-count tracking
    - L0 guardrail enforcement (local, no network)
    - Session lifecycle events (started/completed/failed)
    - Semantic context managers for Universal Runtime IR (intent, reasoning, etc)
    """

    def __init__(
        self,
        client,
        session_id: str,
        agent_id: str,
        project_id: str,
        cost_limit: float,
        call_limit: int,
    ):
        self.client = client
        self.session_id = session_id
        self.agent_id = agent_id
        self.project_id = project_id

        self.cost_limit = cost_limit
        self.call_limit = call_limit

        self.total_cost_usd: float = 0.0
        self.llm_call_count: int = 0
        self._lock = threading.Lock()

        self._session_token = None
        self._span_token = None

    def __enter__(self):
        self._session_token = active_session_context.set(self)
        self._span_token = active_span_stack.set([])

        self.client.emit_async(
            {
                "id": ulid.new().str,
                "project_id": self.project_id,
                "agent_id": self.agent_id,
                "session_id": self.session_id,
                "category": "system",
                "type": "session.started",
                "timestamp": time.time(),
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "completed" if exc_type is None else "failed"
        payload: Dict[str, Any] = {}
        if exc_val:
            payload["error"] = {
                "code": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_val),
            }

        self.client.emit_async(
            {
                "id": ulid.new().str,
                "project_id": self.project_id,
                "agent_id": self.agent_id,
                "session_id": self.session_id,
                "category": "system",
                "type": f"session.{status}",
                "payload": payload,
                "metrics": {
                    "total_cost_usd": self.total_cost_usd,
                    "llm_call_count": self.llm_call_count,
                },
                "timestamp": time.time(),
            }
        )

        active_session_context.reset(self._session_token)
        active_span_stack.reset(self._span_token)

        # Don't suppress L0 exceptions — let them propagate
        return False

    def increment_and_verify_l0(self, cost_delta: float) -> None:
        """
        Updates session counters and enforces L0 guardrails.
        Entirely local — zero network calls. Sub-microsecond latency.
        """
        with self._lock:
            self.total_cost_usd += cost_delta
            self.llm_call_count += 1

            if self.total_cost_usd > self.cost_limit:
                raise VeriCostLimitExceeded(
                    f"Session cost ${self.total_cost_usd:.4f} exceeded "
                    f"limit ${self.cost_limit:.4f}. Execution halted."
                )
            if self.llm_call_count > self.call_limit:
                raise VeriCallLimitExceeded(
                    f"LLM call count {self.llm_call_count} exceeded "
                    f"limit {self.call_limit}. Execution halted."
                )

    # ── Semantic Context Managers for Runtime IR ───────────────────

    def intent(self, label: str, constraints: Optional[List[str]] = None, budget: Optional[float] = None):
        from .ir import NodeKind
        return ExecutionSpanScope(
            self.client, NodeKind.INTENT, label,
            content={"constraints": constraints or [], "budget": budget}
        )

    def knowledge(self, label: str, assumptions: Optional[List[str]] = None, evidence: Optional[List[str]] = None):
        from .ir import NodeKind
        return ExecutionSpanScope(
            self.client, NodeKind.KNOWLEDGE, label,
            assumptions=assumptions, evidence=evidence
        )

    def reasoning(self, label: str, assumptions: Optional[List[str]] = None):
        from .ir import NodeKind
        return ExecutionSpanScope(
            self.client, NodeKind.REASONING, label,
            assumptions=assumptions
        )

    def action(self, label: str, tool_name: Optional[str] = None):
        from .ir import NodeKind
        return ExecutionSpanScope(
            self.client, NodeKind.ACTION, label,
            content={"tool_name": tool_name}
        )

    def decision(self, label: str, alternatives: Optional[List[str]] = None, reasoning: Optional[str] = None):
        from .ir import NodeKind
        return ExecutionSpanScope(
            self.client, NodeKind.DECISION, label,
            content={"alternatives": alternatives or [], "reasoning": reasoning}
        )


# ── Execution Span ─────────────────────────────────────────────────


def get_edge_kind(parent_kind: str, child_kind: str) -> str:
    from .ir import NodeKind, EdgeKind
    if parent_kind == NodeKind.INTENT and child_kind in (NodeKind.INTENT, NodeKind.SUBGOAL):
        return EdgeKind.DECOMPOSES_INTO
    if parent_kind == NodeKind.REASONING and child_kind in (NodeKind.ACTION, NodeKind.TOOL_INVOCATION, NodeKind.LLM_CALL):
        return EdgeKind.CAUSES
    if parent_kind == NodeKind.DECISION and child_kind in (NodeKind.ACTION, NodeKind.TOOL_INVOCATION):
        return EdgeKind.CAUSES
    if parent_kind == NodeKind.ACTION and child_kind == NodeKind.OUTCOME:
        return EdgeKind.CAUSES
    if parent_kind == NodeKind.KNOWLEDGE and child_kind == NodeKind.REASONING:
        return EdgeKind.SUPPORTS
    if parent_kind == NodeKind.ASSUMPTION and child_kind == NodeKind.REASONING:
        return EdgeKind.ASSUMES
    return EdgeKind.DEPENDS_ON


class ExecutionSpanScope:
    """
    Tracks a single logical step within a session (an LLM call,
    tool execution, reasoning step, etc).

    Automatically establishes parent-child relationships via the
    span stack in the active context, emitting RuntimeNodes and RuntimeEdges.
    """

    def __init__(
        self,
        client,
        category: str,
        name: str,
        input_data: Any = None,
        content: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        uncertainty: Optional[float] = None,
        evidence: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
    ):
        self.client = client
        from .ir import NodeKind
        category_map = {
            "llm": NodeKind.LLM_CALL,
            "tool": NodeKind.TOOL_INVOCATION,
            "reasoning": NodeKind.REASONING,
            "system": NodeKind.WORLD_STATE,
        }
        self.category = category_map.get(category, category)
        self.name = name
        self.input_data = input_data

        self.content = content or {}
        self.confidence = confidence
        self.uncertainty = uncertainty
        self.evidence = evidence or []
        self.assumptions = assumptions or []

        self.span_id = ulid.new().str
        self.parent_span_id: Optional[str] = None
        self.start_time: float = 0.0

    def __enter__(self):
        session = active_session_context.get(None)
        if not session:
            return self

        stack = active_span_stack.get([])
        parent_category = None
        if stack:
            self.parent_span_id, parent_category = stack[-1]
        stack.append((self.span_id, self.category))

        self.start_time = time.time()

        # 1. If there's a parent, dynamically build and emit a RuntimeEdge
        if self.parent_span_id and parent_category:
            from .ir import RuntimeEdge
            edge_kind = get_edge_kind(parent_category, self.category)
            edge = RuntimeEdge(
                source=self.parent_span_id,
                target=self.span_id,
                kind=edge_kind,
                session_id=session.session_id,
            )
            edge_dict = edge.to_dict()
            # Inject standard fields for gateway compatibility
            edge_dict.update({
                "project_id": session.project_id,
                "agent_id": session.agent_id,
                "category": "edge",
                "type": "edge.created",
                "name": edge_kind,
                "payload": {
                    "source": edge.source,
                    "target": edge.target,
                    "weight": edge.weight,
                    "metadata": edge.metadata
                },
                "timestamp": self.start_time,
            })
            self.client.emit_async(edge_dict)

        # 2. Emit RuntimeNode starting event
        self.client.emit_async(
            {
                "id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "span_id": self.span_id,
                "project_id": session.project_id,
                "agent_id": session.agent_id,
                "session_id": session.session_id,
                "category": self.category,
                "type": f"{self.category}.started",
                "name": self.name,
                "payload": {"input": safe_serialize(self.input_data)},
                "timestamp": self.start_time,
                # New IR fields
                "kind": self.category,
                "label": self.name,
                "content": {"input": self.input_data, **self.content},
                "confidence": self.confidence,
                "uncertainty": self.uncertainty,
                "evidence": self.evidence,
                "assumptions": self.assumptions,
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Pop from span stack on exit (handles exceptions during scope)
        stack = active_span_stack.get([])
        if stack and stack[-1][0] == self.span_id:
            stack.pop()

        if exc_type is not None:
            session = active_session_context.get(None)
            if session:
                duration_ms = int((time.time() - self.start_time) * 1000)
                self.client.emit_async(
                    {
                        "id": ulid.new().str,
                        "span_id": self.span_id,
                        "parent_span_id": self.parent_span_id,
                        "project_id": session.project_id,
                        "agent_id": session.agent_id,
                        "session_id": session.session_id,
                        "category": self.category,
                        "type": f"{self.category}.failed",
                        "name": self.name,
                        "payload": {
                            "error": {
                                "code": exc_type.__name__,
                                "message": str(exc_val),
                            }
                        },
                        "timestamp": time.time(),
                        # New IR fields
                        "kind": self.category,
                        "label": self.name,
                        "content": {"input": self.input_data, "error": str(exc_val), **self.content},
                        "confidence": 0.0,
                        "latency": duration_ms,
                        "duration": duration_ms,
                    }
                )
        return False  # Don't suppress exceptions

    def complete(
        self, output_data: Any, metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Manually completes the span with output data and metrics.
        Call this instead of relying on __exit__ for successful completions.
        """
        session = active_session_context.get(None)
        if not session:
            return

        stack = active_span_stack.get([])
        if stack and stack[-1][0] == self.span_id:
            stack.pop()

        duration_ms = int((time.time() - self.start_time) * 1000)
        base_metrics: Dict[str, Any] = {"latency_ms": duration_ms, "cost_usd": 0.0}
        if metrics:
            base_metrics.update(metrics)

        # Emit RuntimeNode completed event
        self.client.emit_async(
            {
                "id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "span_id": self.span_id,
                "project_id": session.project_id,
                "agent_id": session.agent_id,
                "session_id": session.session_id,
                "category": self.category,
                "type": f"{self.category}.completed",
                "name": self.name,
                "payload": {"output": safe_serialize(output_data)},
                "metrics": base_metrics,
                "timestamp": time.time(),
                # New IR fields
                "kind": self.category,
                "label": self.name,
                "content": {"input": self.input_data, "output": output_data, **self.content},
                "confidence": self.confidence,
                "uncertainty": self.uncertainty,
                "evidence": self.evidence,
                "assumptions": self.assumptions,
                "cost": base_metrics.get("cost_usd", 0.0),
                "latency": base_metrics.get("latency_ms", 0.0),
                "tokens": {
                    "input": base_metrics.get("tokens_input", 0),
                    "output": base_metrics.get("tokens_output", 0),
                },
                "duration": duration_ms,
            }
        )
