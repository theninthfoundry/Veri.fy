"""
VERI Three-Layer Assertion Engine — Behavioral Validation.

Solves the Semantic Similarity Blind Spot: embedding models score
"processed successfully" vs "NOT processed successfully" at 0.92+
because they share keywords. This engine catches what embeddings miss.

Three layers, each catches what the previous misses:

  Layer 1 (Facts):    Regex-based extraction of amounts, statuses,
                      entities, and negation-qualified terms.
  Layer 2 (Polarity): Detects negation flips that invert business logic.
  Layer 3 (Semantic): Cosine similarity on TF-IDF vectors (no external
                      model needed). Falls back gracefully.

All three must pass for an assertion to succeed. Zero LLM calls.
Total cost per assertion: $0.00. Latency: < 10ms.
"""

import re
import math
import logging
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("veri.assertions")


# ── Result Types ───────────────────────────────────────────────────


class AssertionStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class LayerResult:
    """Result of a single assertion layer."""

    layer: str
    status: AssertionStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssertionResult:
    """Combined result of all three assertion layers."""

    layers: List[LayerResult]

    @property
    def passed(self) -> bool:
        return all(l.status != AssertionStatus.FAIL for l in self.layers)

    @property
    def has_warnings(self) -> bool:
        return any(l.status == AssertionStatus.WARN for l in self.layers)

    @property
    def verdict(self) -> AssertionStatus:
        if any(l.status == AssertionStatus.FAIL for l in self.layers):
            return AssertionStatus.FAIL
        if any(l.status == AssertionStatus.WARN for l in self.layers):
            return AssertionStatus.WARN
        return AssertionStatus.PASS

    def summary(self) -> str:
        lines = []
        for lr in self.layers:
            icon = {"pass": "✅", "fail": "❌", "warn": "⚠️"}[lr.status.value]
            lines.append(f"  {icon} {lr.layer}: {lr.message}")
        return "\n".join(lines)


# ── Layer 1: Fact Extraction ───────────────────────────────────────

# Status words that carry critical business logic
_STATUS_WORDS = {
    "approved",
    "denied",
    "shipped",
    "failed",
    "processed",
    "pending",
    "cancelled",
    "canceled",
    "refunded",
    "completed",
    "rejected",
    "confirmed",
    "delivered",
    "active",
    "inactive",
    "expired",
    "valid",
    "invalid",
    "successful",
    "unsuccessful",
}

# Negation words that flip meaning
_NEGATION_WORDS = {
    "not",
    "never",
    "no",
    "hasn't",
    "haven't",
    "wasn't",
    "weren't",
    "won't",
    "cannot",
    "can't",
    "couldn't",
    "didn't",
    "doesn't",
    "don't",
    "isn't",
    "aren't",
    "shouldn't",
    "wouldn't",
    "unable",
    "without",
}

_NEGATION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _NEGATION_WORDS) + r")\b", re.IGNORECASE
)


def extract_facts(text: str) -> Dict[str, Any]:
    """
    Extracts verifiable facts from agent output text.
    Returns a dict of fact_type → value for comparison.

    This is pure regex + dictionary lookup. No LLM. No model. < 1ms.
    """
    facts: Dict[str, Any] = {}
    text_lower = text.lower()

    # ── Dollar amounts ──────────────────────────────────────
    for i, match in enumerate(re.finditer(r"\$[\d,]+(?:\.\d{1,2})?", text)):
        raw = match.group().replace(",", "")
        facts[f"dollar_amount_{i}"] = raw

    # ── Percentages ─────────────────────────────────────────
    for i, match in enumerate(re.finditer(r"\d+(?:\.\d+)?%", text)):
        facts[f"percentage_{i}"] = match.group()

    # ── Dates ───────────────────────────────────────────────
    date_patterns = [
        r"\d{4}-\d{2}-\d{2}",  # ISO
        r"\d{1,2}/\d{1,2}/\d{2,4}",  # US
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*\d{4}\b",
    ]
    for pattern in date_patterns:
        for i, match in enumerate(re.finditer(pattern, text, re.IGNORECASE)):
            facts[f"date_{i}"] = match.group()

    # ── Status words (with negation context) ────────────────
    for word in _STATUS_WORDS:
        if word in text_lower:
            # Check for negation within 5 words before the status word
            negation_window = rf"({_NEGATION_PATTERN.pattern})\s+(?:\w+\s+){{0,4}}{re.escape(word)}"
            if re.search(negation_window, text_lower):
                facts["status"] = f"NOT_{word}"
            else:
                facts["status"] = word

    # ── Tracking numbers / order IDs ────────────────────────
    for i, match in enumerate(
        re.finditer(r"\b[A-Z0-9]{2,4}[-]?\d{6,}\b", text)
    ):
        facts[f"tracking_id_{i}"] = match.group()

    # ── Email addresses ─────────────────────────────────────
    for i, match in enumerate(
        re.finditer(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", text)
    ):
        facts[f"email_{i}"] = match.group().lower()

    return facts


def compare_facts(
    golden_facts: Dict[str, Any], actual_facts: Dict[str, Any]
) -> LayerResult:
    """
    Compares extracted facts between golden and actual outputs.
    """
    if not golden_facts:
        return LayerResult(
            layer="Facts",
            status=AssertionStatus.PASS,
            message="No verifiable facts in golden output.",
        )

    matches = []
    mismatches = []
    missing = []

    for key, expected in golden_facts.items():
        actual = actual_facts.get(key)
        if actual is None:
            # Check if the fact exists under a different index
            found = False
            for ak, av in actual_facts.items():
                if ak.split("_")[0] == key.split("_")[0] and av == expected:
                    found = True
                    matches.append(key)
                    break
            if not found:
                missing.append((key, expected))
        elif actual == expected:
            matches.append(key)
        else:
            mismatches.append((key, expected, actual))

    # Critical: status mismatch is always a failure
    status_mismatch = any(k == "status" for k, _, _ in mismatches)

    if mismatches:
        return LayerResult(
            layer="Facts",
            status=AssertionStatus.FAIL,
            message=f"{len(mismatches)} fact(s) mismatch, {len(matches)} match",
            details={
                "matches": matches,
                "mismatches": [
                    {"fact": k, "expected": e, "actual": a}
                    for k, e, a in mismatches
                ],
                "missing": [{"fact": k, "expected": e} for k, e in missing],
                "is_status_mismatch": status_mismatch,
            },
        )

    if missing:
        return LayerResult(
            layer="Facts",
            status=AssertionStatus.WARN,
            message=f"{len(missing)} fact(s) missing from output, {len(matches)} present",
            details={
                "matches": matches,
                "missing": [{"fact": k, "expected": e} for k, e in missing],
            },
        )

    return LayerResult(
        layer="Facts",
        status=AssertionStatus.PASS,
        message=f"All {len(matches)} fact(s) verified.",
        details={"matches": matches},
    )


# ── Layer 2: Polarity Detection ────────────────────────────────────


def detect_polarity(text: str) -> Tuple[str, int]:
    """
    Detects the overall polarity of a text based on negation word count.

    Returns (polarity, negation_count) where polarity is "POSITIVE"
    or "NEGATIVE". Odd negation count = negative.
    """
    negations = _NEGATION_PATTERN.findall(text.lower())
    count = len(negations)
    polarity = "NEGATIVE" if count % 2 == 1 else "POSITIVE"
    return polarity, count


def check_polarity(golden: str, actual: str) -> LayerResult:
    """
    Catches the killer case: "processed successfully" vs "NOT processed successfully".
    """
    golden_pol, golden_neg_count = detect_polarity(golden)
    actual_pol, actual_neg_count = detect_polarity(actual)

    if golden_pol != actual_pol:
        return LayerResult(
            layer="Polarity",
            status=AssertionStatus.FAIL,
            message=f"POLARITY FLIP: Golden is {golden_pol}, actual is {actual_pol}",
            details={
                "golden_polarity": golden_pol,
                "actual_polarity": actual_pol,
                "golden_negation_count": golden_neg_count,
                "actual_negation_count": actual_neg_count,
                "explanation": (
                    "The actual output contains a negation that inverts "
                    "the core meaning of the golden output. This is a "
                    "critical business logic error."
                ),
            },
        )

    return LayerResult(
        layer="Polarity",
        status=AssertionStatus.PASS,
        message=f"Polarity consistent ({golden_pol}).",
    )


# ── Layer 3: Semantic Similarity (TF-IDF, no external model) ──────


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"\b\w+\b", text.lower())


def _tfidf_vectors(
    text_a: str, text_b: str
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Computes TF-IDF vectors for two texts using their combined vocabulary.
    No external dependencies. Pure Python.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    # Term frequency
    tf_a = Counter(tokens_a)
    tf_b = Counter(tokens_b)

    # Document frequency (how many of the 2 docs contain each term)
    vocab = set(tf_a.keys()) | set(tf_b.keys())
    df: Dict[str, int] = {}
    for term in vocab:
        df[term] = (1 if term in tf_a else 0) + (1 if term in tf_b else 0)

    # TF-IDF
    n_docs = 2
    vec_a: Dict[str, float] = {}
    vec_b: Dict[str, float] = {}

    for term in vocab:
        idf = math.log((n_docs + 1) / (df[term] + 1)) + 1
        vec_a[term] = (tf_a.get(term, 0) / max(len(tokens_a), 1)) * idf
        vec_b[term] = (tf_b.get(term, 0) / max(len(tokens_b), 1)) * idf

    return vec_a, vec_b


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    all_keys = set(vec_a.keys()) | set(vec_b.keys())

    dot = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in all_keys)
    mag_a = math.sqrt(sum(v**2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v**2 for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def check_semantic_similarity(
    golden: str, actual: str, threshold: float = 0.60
) -> LayerResult:
    """
    TF-IDF cosine similarity. No external model. No LLM call. ~1ms.

    The threshold is intentionally lower than embedding-based similarity
    because TF-IDF is a weaker signal. The heavy lifting is done by
    Layers 1 and 2; this is the safety net.
    """
    vec_a, vec_b = _tfidf_vectors(golden, actual)
    score = _cosine_similarity(vec_a, vec_b)

    if score >= threshold:
        return LayerResult(
            layer="Semantic",
            status=AssertionStatus.PASS,
            message=f"Similarity {score:.2f} ≥ {threshold:.2f}",
            details={"score": round(score, 4), "threshold": threshold},
        )
    else:
        return LayerResult(
            layer="Semantic",
            status=AssertionStatus.FAIL,
            message=f"Similarity {score:.2f} < {threshold:.2f}",
            details={
                "score": round(score, 4),
                "threshold": threshold,
                "explanation": (
                    "The actual output has drifted significantly from the "
                    "golden output in terms of word usage and structure."
                ),
            },
        )





# ── Behavioral Assertions (Non-Response) ───────────────────────────


@dataclass
class BehavioralCheckResult:
    """Result of a behavioral assertion (tools called, cost, latency, etc)."""

    name: str
    status: AssertionStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


def check_tools_called(
    expected: List[str], actual: List[str]
) -> BehavioralCheckResult:
    """Verifies the correct tools were called."""
    expected_set = set(expected)
    actual_set = set(actual)

    missing = expected_set - actual_set
    extra = actual_set - expected_set

    if missing:
        return BehavioralCheckResult(
            name="ToolsCalled",
            status=AssertionStatus.FAIL,
            message=f"Missing tool calls: {missing}",
            details={"expected": expected, "actual": actual, "missing": list(missing)},
        )

    if extra:
        return BehavioralCheckResult(
            name="ToolsCalled",
            status=AssertionStatus.WARN,
            message=f"Extra tool calls (evolution): {extra}",
            details={"expected": expected, "actual": actual, "extra": list(extra)},
        )

    return BehavioralCheckResult(
        name="ToolsCalled",
        status=AssertionStatus.PASS,
        message=f"All {len(expected)} expected tool(s) called.",
    )


def check_tools_not_called(
    forbidden: List[str], actual: List[str]
) -> BehavioralCheckResult:
    """Verifies forbidden tools were NOT called (safety check)."""
    violations = set(forbidden) & set(actual)

    if violations:
        return BehavioralCheckResult(
            name="SafetyCheck",
            status=AssertionStatus.FAIL,
            message=f"SAFETY VIOLATION: Forbidden tools called: {violations}",
            details={"forbidden": forbidden, "violations": list(violations)},
        )

    return BehavioralCheckResult(
        name="SafetyCheck",
        status=AssertionStatus.PASS,
        message="No forbidden tools called.",
    )


def check_token_budget(max_tokens: int, actual_tokens: int) -> BehavioralCheckResult:
    """Verifies token usage is within budget."""
    if actual_tokens > max_tokens:
        return BehavioralCheckResult(
            name="TokenBudget",
            status=AssertionStatus.FAIL,
            message=f"Tokens {actual_tokens} > budget {max_tokens}",
            details={
                "max": max_tokens,
                "actual": actual_tokens,
                "overage_pct": round((actual_tokens / max_tokens - 1) * 100, 1),
            },
        )

    return BehavioralCheckResult(
        name="TokenBudget",
        status=AssertionStatus.PASS,
        message=f"Tokens {actual_tokens} within budget {max_tokens}.",
    )


def check_cost_budget(max_usd: float, actual_usd: float) -> BehavioralCheckResult:
    """Verifies cost is within budget."""
    if actual_usd > max_usd:
        return BehavioralCheckResult(
            name="CostBudget",
            status=AssertionStatus.FAIL,
            message=f"Cost ${actual_usd:.4f} > budget ${max_usd:.4f}",
            details={"max_usd": max_usd, "actual_usd": actual_usd},
        )

    return BehavioralCheckResult(
        name="CostBudget",
        status=AssertionStatus.PASS,
        message=f"Cost ${actual_usd:.4f} within budget ${max_usd:.4f}.",
    )


def check_latency(max_ms: int, actual_ms: int) -> BehavioralCheckResult:
    """Verifies latency is within bounds."""
    if actual_ms > max_ms:
        return BehavioralCheckResult(
            name="Latency",
            status=AssertionStatus.FAIL,
            message=f"Latency {actual_ms}ms > limit {max_ms}ms",
            details={"max_ms": max_ms, "actual_ms": actual_ms},
        )

    return BehavioralCheckResult(
        name="Latency",
        status=AssertionStatus.PASS,
        message=f"Latency {actual_ms}ms within limit {max_ms}ms.",
    )


# ── Optional Layer 4: LLM-as-a-Judge ────────────────────────────────


def check_llm_judge(
    golden: str, actual: str, api_key: Optional[str] = None
) -> LayerResult:
    """
    Evaluates semantic logic discrepancies using gpt-4o-mini as a judge.
    Runs only when an API key is available. Falls back to a warning otherwise.

    Uses a direct requests call to avoid import overhead of the openai client.
    """
    import os
    import json
    import requests

    effective_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("VERI_API_KEY")
    if not effective_key or effective_key == "disabled_key":
        return LayerResult(
            layer="LLM-Judge",
            status=AssertionStatus.WARN,
            message="LLM-as-a-Judge skipped: No valid API key set in environment.",
        )

    system_prompt = (
        "You are an expert AI Agent Quality Assurance judge. Compare the ACTUAL agent response "
        "against the GOLDEN response and evaluate if there is any critical semantic discrepancy, "
        "logical inversion, or factual error. Pay extreme attention to minor variations like "
        "negation words, percentages, numbers, or dates.\n\n"
        "Return a JSON object matching this schema:\n"
        "{\n"
        '  "verdict": "PASS" | "FAIL",\n'
        '  "explanation": "Detailed explanation of discrepancy or why it passed.",\n'
        '  "discrepancy_type": "none" | "negation_flip" | "factual_mismatch" | "hallucination" | "other"\n'
        "}"
    )

    user_prompt = f"GOLDEN:\n{golden}\n\nACTUAL:\n{actual}"

    headers = {
        "Authorization": f"Bearer {effective_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }

    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=body,
            headers=headers,
            timeout=5.0,
        )
        if res.status_code != 200:
            return LayerResult(
                layer="LLM-Judge",
                status=AssertionStatus.WARN,
                message=f"LLM-as-a-Judge API error: HTTP {res.status_code}",
                details={"body": res.text},
            )

        data = res.json()
        raw_content = data["choices"][0]["message"]["content"]
        result_map = json.loads(raw_content)

        verdict = result_map.get("verdict", "FAIL")
        explanation = result_map.get("explanation", "No explanation provided.")
        discrepancy = result_map.get("discrepancy_type", "none")

        status = AssertionStatus.PASS if verdict == "PASS" else AssertionStatus.FAIL

        return LayerResult(
            layer="LLM-Judge",
            status=status,
            message=f"{verdict}: {explanation}",
            details={"discrepancy_type": discrepancy, "raw_result": result_map},
        )

    except Exception as e:
        return LayerResult(
            layer="LLM-Judge",
            status=AssertionStatus.WARN,
            message=f"LLM-as-a-Judge execution failed: {str(e)}",
        )


# ── Combined Assertion ─────────────────────────────────────────────


class ResponseAssertionEngine:
    """
    Four-layer response assertion.
    By default, runs local, zero-cost checks. Optional LLM-as-a-Judge runs
    automatically if an API key is available or explicitly requested.

    Layer priority:
      1. Polarity — negation flips (local, 0ms)
      2. Facts — amounts, dates, status words (local, 0ms)
      3. Semantic — TF-IDF text similarity (local, 1ms)
      4. LLM-Judge — deep logical judge (remote, optional)
    """

    def __init__(self, semantic_threshold: float = 0.60, use_judge: bool = False):
        self.semantic_threshold = semantic_threshold
        self.use_judge = use_judge

    def evaluate(
        self, golden: str, actual: str, api_key: Optional[str] = None
    ) -> AssertionResult:
        """
        Runs the assertion suite.
        """
        layers: List[LayerResult] = []

        # Layer 1: Fact comparison
        golden_facts = extract_facts(golden)
        actual_facts = extract_facts(actual)
        layers.append(compare_facts(golden_facts, actual_facts))

        # Layer 2: Polarity check
        layers.append(check_polarity(golden, actual))

        # Layer 3: Semantic similarity
        layers.append(
            check_semantic_similarity(golden, actual, self.semantic_threshold)
        )

        # Layer 4: Optional LLM Judge
        if self.use_judge:
            layers.append(check_llm_judge(golden, actual, api_key))

        return AssertionResult(layers=layers)

