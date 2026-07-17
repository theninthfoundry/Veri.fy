from typing import Any, Dict, Optional

class ReplayCache:
    """
    Local cache helper for tagging and capturing input/output snapshots
    for replayable nodes.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the cached snapshot for a node."""
        return self._cache.get(node_id)

    def set(self, node_id: str, input_snapshot: Any, output_snapshot: Any, deterministic: bool = True) -> None:
        """Cache a snapshot of input and output for a node."""
        self._cache[node_id] = {
            "input": input_snapshot,
            "output": output_snapshot,
            "deterministic": deterministic
        }

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
