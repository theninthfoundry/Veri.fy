"""
VERI Fuzzy Fixture Matcher — Priority Cascade Resolution.

Solves the Argument Hash Fallacy: LLMs format tool arguments
inconsistently ({"id": 4521} vs {"order_id": 4521} vs {"id": "4521"}).
Instead of brittle hash-based lookup, this matcher cascades through
three tiers of decreasing strictness:

  Tier 1 (Exact):      Normalized deep equality
  Tier 2 (Structural): Leaf-value overlap (ignores key names)
  Tier 3 (Intent):     Same tool + core identifying values match

Each tier returns a confidence score. The first tier to match wins.
"""

import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger("veri.matcher")


# ── Data Structures ────────────────────────────────────────────────


@dataclass
class Fixture:
    """A recorded tool call with frozen input/output."""

    tool_name: str
    input: Dict[str, Any]
    output: Any
    source_session_id: Optional[str] = None
    recorded_at: Optional[float] = None


@dataclass
class MatchResult:
    """Result of attempting to match a tool call to a fixture."""

    status: str  # "exact", "structural", "intent", "unmatched", "unmocked"
    fixture: Optional[Fixture]
    confidence: float = 0.0
    tier: int = 0  # 1, 2, 3 or 0 for no match
    match_details: Dict[str, Any] = field(default_factory=dict)

    @property
    def matched(self) -> bool:
        return self.status in ("exact", "structural", "intent")

    @property
    def is_evolution(self) -> bool:
        """New tool call that doesn't exist in any fixture — not a regression."""
        return self.status == "unmocked"


class FixtureMatcher:
    """
    Three-tier priority cascade matcher for tool call fixtures.

    Usage:
        matcher = FixtureMatcher(fixtures)
        result = matcher.match("order_lookup", {"id": 4521})
        if result.matched:
            return result.fixture.output
        elif result.is_evolution:
            report_new_behavior(result)
    """

    # Minimum confidence thresholds per tier
    STRUCTURAL_THRESHOLD = 0.70
    INTENT_THRESHOLD = 0.50

    def __init__(self, fixtures: List[Fixture]):
        self._fixtures = fixtures
        self._fixture_index: Dict[str, List[Fixture]] = {}
        for f in fixtures:
            self._fixture_index.setdefault(f.tool_name, []).append(f)

    def match(self, tool_name: str, tool_input: Dict[str, Any]) -> MatchResult:
        """
        Attempts to match a tool call against recorded fixtures.
        Cascades: exact → structural → intent → unmatched/unmocked.
        """
        candidates = self._fixture_index.get(tool_name, [])

        if not candidates:
            # No fixture for this tool at all — it's a new behavior
            return MatchResult(
                status="unmocked",
                fixture=None,
                confidence=0.0,
                tier=0,
                match_details={"reason": f"No fixtures recorded for tool '{tool_name}'"},
            )

        # ── Tier 1: Exact Match ─────────────────────────────────
        for fixture in candidates:
            if _deep_equals_normalized(fixture.input, tool_input):
                return MatchResult(
                    status="exact",
                    fixture=fixture,
                    confidence=1.0,
                    tier=1,
                    match_details={"method": "normalized_deep_equality"},
                )

        # ── Tier 2: Structural Match (leaf-value overlap) ───────
        best_structural: Optional[Tuple[Fixture, float, Dict]] = None

        for fixture in candidates:
            score, details = _structural_similarity(fixture.input, tool_input)
            if score >= self.STRUCTURAL_THRESHOLD:
                if best_structural is None or score > best_structural[1]:
                    best_structural = (fixture, score, details)

        if best_structural:
            fixture, score, details = best_structural
            return MatchResult(
                status="structural",
                fixture=fixture,
                confidence=score,
                tier=2,
                match_details=details,
            )

        # ── Tier 3: Intent Match (core identifying values) ──────
        best_intent: Optional[Tuple[Fixture, float, Dict]] = None

        for fixture in candidates:
            score, details = _intent_similarity(fixture.input, tool_input)
            if score >= self.INTENT_THRESHOLD:
                if best_intent is None or score > best_intent[1]:
                    best_intent = (fixture, score, details)

        if best_intent:
            fixture, score, details = best_intent
            return MatchResult(
                status="intent",
                fixture=fixture,
                confidence=score,
                tier=3,
                match_details=details,
            )

        # ── No match found ──────────────────────────────────────
        return MatchResult(
            status="unmatched",
            fixture=None,
            confidence=0.0,
            tier=0,
            match_details={
                "reason": f"Tool '{tool_name}' has {len(candidates)} fixture(s) "
                f"but none matched the provided arguments",
                "candidates": [
                    {"input": f.input} for f in candidates[:3]
                ],
                "actual_input": tool_input,
            },
        )


# ── Comparison Functions ───────────────────────────────────────────


def _normalize_value(val: Any) -> Any:
    """
    Normalizes a value for comparison:
    - Strings are lowered and stripped
    - Numbers are coerced to float
    - Nested structures are recursively normalized
    """
    if isinstance(val, str):
        stripped = val.strip().lower()
        # Try numeric coercion: "4521" → 4521.0
        try:
            return float(stripped)
        except (ValueError, OverflowError):
            return stripped
    elif isinstance(val, (int, float)):
        return float(val)
    elif isinstance(val, dict):
        return {str(k).strip().lower(): _normalize_value(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_normalize_value(item) for item in val]
    elif isinstance(val, bool):
        return val
    elif val is None:
        return None
    else:
        return str(val).strip().lower()


def _deep_equals_normalized(a: Any, b: Any) -> bool:
    """
    Deep equality after normalization.
    {"id": 4521} == {"id": "4521"} → True (numeric coercion)
    {"ID": 4521} == {"id": 4521} → True (case normalization)
    """
    return _normalize_value(a) == _normalize_value(b)


def _extract_leaf_values(obj: Any, _prefix: str = "") -> List[Tuple[str, Any]]:
    """
    Extracts all leaf (non-container) values with their path.
    {"a": {"b": 1}, "c": [2, 3]} → [("a.b", 1), ("c.0", 2), ("c.1", 3)]
    """
    leaves: List[Tuple[str, Any]] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{_prefix}.{k}" if _prefix else str(k)
            leaves.extend(_extract_leaf_values(v, path))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            path = f"{_prefix}.{i}" if _prefix else str(i)
            leaves.extend(_extract_leaf_values(v, path))
    else:
        leaves.append((_prefix, _normalize_value(obj)))

    return leaves


def _structural_similarity(
    recorded: Dict[str, Any], actual: Dict[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    """
    Tier 2: Measures overlap of leaf values regardless of key names.

    Returns (score, details) where score is in [0.0, 1.0].

    {"id": 4521}  vs  {"order_id": 4521}          → 1.0 (value present)
    {"id": 4521}  vs  {"order_id": 4521, "v": 0}  → 1.0 (superset, all orig values present)
    {"id": 4521}  vs  {"id": 9999}                 → 0.0 (value missing)
    """
    recorded_leaves = _extract_leaf_values(recorded)
    actual_leaves = _extract_leaf_values(actual)

    if not recorded_leaves:
        return 0.5, {"reason": "empty_recorded_input"}

    recorded_vals = set(v for _, v in recorded_leaves)
    actual_vals = set(v for _, v in actual_leaves)

    matched = recorded_vals & actual_vals
    missing = recorded_vals - actual_vals
    extra = actual_vals - recorded_vals

    score = len(matched) / len(recorded_vals) if recorded_vals else 0.5

    details = {
        "method": "leaf_value_overlap",
        "matched_values": [str(v) for v in list(matched)[:10]],
        "missing_values": [str(v) for v in list(missing)[:10]],
        "extra_values": [str(v) for v in list(extra)[:10]],
        "recorded_key_count": len(recorded_leaves),
        "actual_key_count": len(actual_leaves),
    }

    return score, details


def _intent_similarity(
    recorded: Dict[str, Any], actual: Dict[str, Any]
) -> Tuple[float, Dict[str, Any]]:
    """
    Tier 3: Checks if the "core identifying values" are the same.

    Heuristic: Extract numeric IDs, proper nouns, and structured
    identifiers from both inputs. If the majority overlap, the
    intent is the same even if the structure is very different.
    """
    recorded_ids = _extract_identifying_values(recorded)
    actual_ids = _extract_identifying_values(actual)

    if not recorded_ids:
        return 0.3, {"reason": "no_identifying_values_in_recorded"}

    overlap = recorded_ids & actual_ids
    score = len(overlap) / len(recorded_ids) if recorded_ids else 0.0

    details = {
        "method": "identifying_value_overlap",
        "recorded_ids": [str(v) for v in recorded_ids],
        "actual_ids": [str(v) for v in actual_ids],
        "overlap": [str(v) for v in overlap],
    }

    return score, details


def _extract_identifying_values(obj: Any) -> set:
    """
    Extracts values likely to be identifiers:
    - Numbers (IDs, amounts)
    - Strings that look like IDs (alphanumeric, UUIDs, emails)
    """
    ids: set = set()
    leaves = _extract_leaf_values(obj)

    for _, val in leaves:
        if isinstance(val, (int, float)):
            ids.add(val)
        elif isinstance(val, str):
            stripped = val.strip()
            # Keep short strings that look like identifiers
            if stripped and len(stripped) < 100:
                ids.add(stripped)

    return ids


# ── Fixture Store ──────────────────────────────────────────────────


class FixtureStore:
    """
    In-memory fixture store for the test runner.
    Loads fixtures from JSON files and provides matcher access.
    """

    def __init__(self):
        self._fixtures: List[Fixture] = []
        self._matcher: Optional[FixtureMatcher] = None

    def add(self, fixture: Fixture) -> None:
        self._fixtures.append(fixture)
        self._matcher = None  # Invalidate cached matcher

    def load_from_dict(self, data: List[Dict[str, Any]]) -> None:
        """Load fixtures from a list of dicts (e.g., parsed from JSON)."""
        for item in data:
            self._fixtures.append(
                Fixture(
                    tool_name=item["tool_name"],
                    input=item.get("input", {}),
                    output=item.get("output"),
                    source_session_id=item.get("source_session_id"),
                    recorded_at=item.get("recorded_at"),
                )
            )
        self._matcher = None

    def get_matcher(self) -> FixtureMatcher:
        """Returns a FixtureMatcher built from all loaded fixtures."""
        if self._matcher is None:
            self._matcher = FixtureMatcher(self._fixtures)
        return self._matcher

    @property
    def count(self) -> int:
        return len(self._fixtures)

    def to_dict(self) -> List[Dict[str, Any]]:
        """Serializes all fixtures to a list of dicts."""
        return [
            {
                "tool_name": f.tool_name,
                "input": f.input,
                "output": f.output,
                "source_session_id": f.source_session_id,
                "recorded_at": f.recorded_at,
            }
            for f in self._fixtures
        ]
