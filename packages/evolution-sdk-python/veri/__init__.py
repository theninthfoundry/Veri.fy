import os
import logging
from typing import List, Optional
from .client import VeriClient
from .ir import NodeKind, EdgeKind, RuntimeNode, RuntimeEdge

logger = logging.getLogger("veri")

_global_client: Optional[VeriClient] = None


def _load_yaml_config(path: str) -> dict:
    config = {}
    if not os.path.exists(path):
        return config
    import re
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        current_section = None
        for line in lines:
            # Strip comments and whitespace
            line = line.split("#")[0].strip()
            if not line:
                continue
            
            # Match top-level sections like "guardrails:"
            section_match = re.match(r"^(\w+):$", line)
            if section_match:
                current_section = section_match.group(1)
                config[current_section] = {}
                continue
            
            # Match indented keys under a section
            indented_match = re.match(r"^(\w+):\s*([^\s]+)", line)
            if indented_match:
                k = indented_match.group(1)
                v = indented_match.group(2)
                
                # Check for nested values if we are inside a section
                if current_section:
                    # Clean quotes and parse numeric values
                    try:
                        if "." in v:
                            v = float(v)
                        else:
                            v = int(v)
                    except ValueError:
                        v = v.strip("'\"")
                    config[current_section][k] = v
                else:
                    config[k] = v
    except Exception as e:
        logger.warning("Failed to load veri.yaml: %s", str(e))
    return config


def init(
    api_key: Optional[str] = None,
    endpoint: str = "http://localhost:8080/v1/events",
    cost_limit: float = 5.00,
    call_limit: int = 100,
    disabled: bool = False,
) -> None:
    """
    Initializes the global VERI runtime client.
    Loads settings from veri.yaml in the working directory if present.

    Args:
        api_key: VERI API key. Falls back to VERI_API_KEY env var.
        endpoint: Gateway ingest URL.
        cost_limit: Maximum USD spend per session before L0 kill-switch.
        call_limit: Maximum LLM calls per session before L0 kill-switch.
        disabled: If True, SDK is inert — no events emitted, no guardrails.
    """
    global _global_client

    if _global_client is not None:
        logger.warning("VERI SDK is already initialized. Skipping redundant initialization.")
        return

    # Attempt to load from veri.yaml configuration
    local_config = _load_yaml_config("veri.yaml")
    guardrail_config = local_config.get("guardrails", {})
    
    effective_cost_limit = guardrail_config.get("cost_limit", cost_limit)
    effective_call_limit = guardrail_config.get("call_limit", call_limit)

    effective_key = api_key or os.getenv("VERI_API_KEY")
    if not effective_key and not disabled:
        raise ValueError(
            "Initialization failed: VERI_API_KEY must be provided or set via environment variable."
        )

    _global_client = VeriClient(
        api_key=effective_key or "disabled_key",
        endpoint=endpoint,
        cost_limit=effective_cost_limit,
        call_limit=effective_call_limit,
        disabled=disabled,
    )
    logger.info(
        "VERI SDK initialized (cost_limit=%s, call_limit=%s) — capture loop active.",
        effective_cost_limit,
        effective_call_limit,
    )


def get_client() -> VeriClient:
    """Returns the global VeriClient. Raises if init() was not called."""
    global _global_client
    if _global_client is None:
        raise RuntimeError("VERI Runtime Client accessed before init() was invoked.")
    return _global_client


def reset() -> None:
    """Tears down the global client. Useful for testing."""
    global _global_client
    if _global_client is not None:
        _global_client.shutdown()
        _global_client = None


def instrument(frameworks: List[str]) -> None:
    """
    Applies auto-instrumentation hooks across target frameworks.

    Supported frameworks: "openai", "langchain"
    """
    from .patching import patch_runtime

    client = get_client()
    if client.disabled:
        return
    for framework in frameworks:
        patch_runtime(framework, client)


def session(session_id: str, agent_id: str, project_id: str):
    """Shorthand context manager for creating a tracked agent session."""
    return get_client().session(
        session_id=session_id, agent_id=agent_id, project_id=project_id
    )
