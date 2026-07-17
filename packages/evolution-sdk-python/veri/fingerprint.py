import sys
import hashlib
import json
from typing import Dict, Any, List

class RuntimeFingerprint:
    """
    Captures a cryptographic, deterministic snapshot of the entire agent execution environment.
    Versions the runtime state, not just the code.
    """
    def __init__(
        self,
        prompt_templates: Dict[str, str],
        model_parameters: Dict[str, Any],
        tool_schemas: Dict[str, Dict[str, Any]],
        environment_packages: List[str]
    ):
        self.prompt_templates = prompt_templates
        self.model_parameters = model_parameters
        self.tool_schemas = tool_schemas
        # Sort packages to ensure deterministic serialization
        self.environment_packages = sorted(environment_packages)
        self.snapshot = {
            "prompt_templates": self.prompt_templates,
            "model_parameters": self.model_parameters,
            "tool_schemas": self.tool_schemas,
            "environment_packages": self.environment_packages
        }
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        serialized = json.dumps(self.snapshot, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hash": self.hash,
            "snapshot": self.snapshot
        }

def capture_current_fingerprint(
    prompt_templates: Dict[str, str],
    model_parameters: Dict[str, Any],
    tool_schemas: Dict[str, Dict[str, Any]],
    target_packages: List[str]
) -> RuntimeFingerprint:
    """Helper to capture the current execution fingerprint."""
    import pkg_resources
    env_packages = []
    for pkg in target_packages:
        try:
            version = pkg_resources.get_distribution(pkg).version
            env_packages.append(f"{pkg}=={version}")
        except Exception:
            env_packages.append(f"{pkg}==unknown")

    return RuntimeFingerprint(
        prompt_templates=prompt_templates,
        model_parameters=model_parameters,
        tool_schemas=tool_schemas,
        environment_packages=env_packages
    )


def compute_behavior_hash(
    planner_steps: List[str],
    tool_sequence: List[str],
    decision_order: List[str],
    constraints: List[str],
    memory_usage: List[str]
) -> str:
    """
    Generates a cryptographic, deterministic hash of the agent's behavior sequence.
    Independent of token output or timestamps.
    """
    data = {
        "planner_steps": planner_steps,
        "tool_sequence": tool_sequence,
        "decision_order": decision_order,
        "constraints": constraints,
        "memory_usage": memory_usage
    }
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
