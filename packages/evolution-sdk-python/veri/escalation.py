"""
VERI Escalation Engine — Human-in-the-Loop Accountability Primitives.

This module makes escalation a first-class, structured, auditable,
policy-driven object — not a Slack webhook bolted on as an afterthought.

When an agent execution hits a node that matches an escalation policy
(based on capabilities, confidence, action type, cost, or risk),
the engine can:
  - Block execution until a human approves ('block')
  - Continue with a flag for post-hoc review ('proceed_with_flag')
  - Abort the session entirely ('abort')

Every escalation and its resolution are recorded with HMAC signatures
for non-repudiation — the artifact a compliance officer needs.
"""

import hashlib
import hmac
import json
import logging
import time
import requests
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("veri.escalation")


# ── Escalation Exceptions ──────────────────────────────────────────


class EscalationRequired(Exception):
    """
    Raised when a node triggers an escalation policy with
    timeout_behavior='block' or 'abort'. The agent framework
    should catch this to pause execution or abort gracefully.
    """

    def __init__(self, escalation_id: str, policy_name: str, message: str,
                 behavior: str = "block"):
        self.escalation_id = escalation_id
        self.policy_name = policy_name
        self.behavior = behavior
        super().__init__(message)


class EscalationAborted(EscalationRequired):
    """Raised when timeout_behavior='abort' — session should terminate."""

    def __init__(self, escalation_id: str, policy_name: str, message: str):
        super().__init__(escalation_id, policy_name, message, behavior="abort")


class EscalationTimedOut(EscalationRequired):
    """Raised when a blocked escalation times out without resolution."""

    def __init__(self, escalation_id: str, policy_name: str, message: str):
        super().__init__(escalation_id, policy_name, message, behavior="timed_out")


# ── Data Structures ────────────────────────────────────────────────


@dataclass
class EscalationPolicy:
    """Local representation of an escalation policy loaded from the gateway."""

    id: str
    project_id: str
    name: str
    description: str = ""

    # Trigger conditions
    trigger_capabilities: List[str] = field(default_factory=list)
    trigger_action_types: List[str] = field(default_factory=list)
    trigger_risk_threshold: Optional[float] = None
    trigger_confidence_below: Optional[float] = None
    trigger_confidence_source: Optional[str] = None
    trigger_cost_above: Optional[float] = None

    # Resolution
    resolution_channel: str = "in_app_queue"
    timeout_seconds: int = 300
    timeout_behavior: str = "block"
    required_approvers: int = 1
    audit_requirement: str = "reasoned"

    priority: int = 100
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationPolicy":
        return cls(
            id=data["id"],
            project_id=data["project_id"],
            name=data["name"],
            description=data.get("description", ""),
            trigger_capabilities=data.get("trigger_capabilities") or [],
            trigger_action_types=data.get("trigger_action_types") or [],
            trigger_risk_threshold=data.get("trigger_risk_threshold"),
            trigger_confidence_below=data.get("trigger_confidence_below"),
            trigger_confidence_source=data.get("trigger_confidence_source"),
            trigger_cost_above=data.get("trigger_cost_above"),
            resolution_channel=data.get("resolution_channel", "in_app_queue"),
            timeout_seconds=data.get("timeout_seconds", 300),
            timeout_behavior=data.get("timeout_behavior", "block"),
            required_approvers=data.get("required_approvers", 1),
            audit_requirement=data.get("audit_requirement", "reasoned"),
            priority=data.get("priority", 100),
            enabled=data.get("enabled", True),
        )


@dataclass
class EscalationRecord:
    """An escalation event created when a policy triggers."""

    id: str
    policy_id: str
    policy_name: str
    session_id: str
    node_id: str
    node_kind: str
    node_label: str
    status: str = "pending"
    escalated_at: float = 0.0
    timeout_at: float = 0.0
    resolution_reason: Optional[str] = None
    resolved_by: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationRecord":
        return cls(
            id=data["id"],
            policy_id=data["policy_id"],
            policy_name=data.get("policy_name", ""),
            session_id=data["session_id"],
            node_id=data["node_id"],
            node_kind=data.get("node_kind", ""),
            node_label=data.get("node_label", ""),
            status=data.get("status", "pending"),
            escalated_at=data.get("escalated_at", 0.0),
            timeout_at=data.get("timeout_at", 0.0),
            resolution_reason=data.get("resolution_reason"),
            resolved_by=data.get("resolved_by"),
        )


# ── HMAC Signature Utilities ───────────────────────────────────────


def compute_approval_signature(
    actor: str,
    action: str,
    timestamp: float,
    escalation_id: str,
    signing_secret: str,
) -> str:
    """
    Computes HMAC-SHA256 signature for an approval action.
    This provides non-repudiation — a verifiable proof that a specific
    person performed a specific action at a specific time.

    Message format: actor|action|timestamp|escalation_id
    """
    message = f"{actor}|{action}|{timestamp}|{escalation_id}"
    signature = hmac.new(
        signing_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def verify_approval_signature(
    actor: str,
    action: str,
    timestamp: float,
    escalation_id: str,
    signing_secret: str,
    signature: str,
) -> bool:
    """Verifies that a given signature matches the expected HMAC-SHA256."""
    expected = compute_approval_signature(
        actor, action, timestamp, escalation_id, signing_secret
    )
    return hmac.compare_digest(expected, signature)


# ── Escalation Policy Engine ──────────────────────────────────────


class EscalationEngine:
    """
    Evaluates agent execution nodes against loaded escalation policies.

    Loaded once per session from the gateway API. Policies are sorted by
    priority (lower number = higher priority). The first matching policy
    wins — this prevents cascading escalations for a single node.
    """

    def __init__(
        self,
        policies: Optional[List[EscalationPolicy]] = None,
        gateway_endpoint: str = "http://localhost:8080",
        api_key: str = "",
        enabled: bool = True,
    ):
        self._policies: List[EscalationPolicy] = []
        self._gateway_endpoint = gateway_endpoint.rstrip("/")
        self._api_key = api_key
        self._enabled = enabled

        if policies:
            self._policies = sorted(policies, key=lambda p: p.priority)

    def load_policies(self, project_id: str) -> None:
        """Fetches active escalation policies from the gateway API."""
        if not self._enabled:
            return

        try:
            response = requests.get(
                f"{self._gateway_endpoint}/api/v1/policies",
                params={"project_id": project_id},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=3.0,
            )
            if response.status_code == 200:
                policies_data = response.json()
                self._policies = sorted(
                    [EscalationPolicy.from_dict(p) for p in policies_data
                     if p.get("enabled", True)],
                    key=lambda p: p.priority,
                )
                logger.info(
                    "Loaded %d escalation policies for project %s",
                    len(self._policies), project_id,
                )
            else:
                logger.warning(
                    "Failed to load escalation policies: HTTP %d",
                    response.status_code,
                )
        except requests.exceptions.ConnectionError:
            logger.debug("Gateway unreachable — escalation policies not loaded.")
        except Exception as e:
            logger.error("Failed to load escalation policies: %s", str(e))

    def evaluate(
        self,
        node_kind: str,
        capabilities: List[str],
        confidence_value: Optional[float],
        confidence_source: Optional[str],
        action_type: Optional[str] = None,
        cost: float = 0.0,
        risk: float = 0.0,
    ) -> Optional[EscalationPolicy]:
        """
        Evaluates a node against all loaded policies. Returns the
        highest-priority matching policy, or None if no policy matches.

        Matching rules (all specified trigger conditions must match):
        - trigger_capabilities: node must have at least one matching capability
        - trigger_action_types: action_type must be in the list
        - trigger_confidence_below: confidence must be below threshold
        - trigger_confidence_source: confidence source must match
        - trigger_cost_above: cost must exceed threshold
        - trigger_risk_threshold: risk must exceed threshold
        """
        if not self._enabled or not self._policies:
            return None

        for policy in self._policies:
            if not policy.enabled:
                continue

            if self._matches(
                policy, node_kind, capabilities, confidence_value,
                confidence_source, action_type, cost, risk
            ):
                return policy

        return None

    def _matches(
        self,
        policy: EscalationPolicy,
        node_kind: str,
        capabilities: List[str],
        confidence_value: Optional[float],
        confidence_source: Optional[str],
        action_type: Optional[str],
        cost: float,
        risk: float,
    ) -> bool:
        """Checks if all specified trigger conditions match."""
        has_any_trigger = False

        # Capability match: node must have at least one overlapping capability
        if policy.trigger_capabilities:
            has_any_trigger = True
            if not set(policy.trigger_capabilities) & set(capabilities):
                return False

        # Action type match
        if policy.trigger_action_types:
            has_any_trigger = True
            if action_type not in policy.trigger_action_types:
                return False

        # Confidence threshold
        if policy.trigger_confidence_below is not None:
            has_any_trigger = True
            if confidence_value is None:
                pass  # No confidence = don't filter on this
            elif confidence_value >= policy.trigger_confidence_below:
                return False

        # Confidence source match
        if policy.trigger_confidence_source is not None:
            has_any_trigger = True
            if confidence_source != policy.trigger_confidence_source:
                return False

        # Cost threshold
        if policy.trigger_cost_above is not None:
            has_any_trigger = True
            if cost <= policy.trigger_cost_above:
                return False

        # Risk threshold
        if policy.trigger_risk_threshold is not None:
            has_any_trigger = True
            if risk <= policy.trigger_risk_threshold:
                return False

        # A policy with no triggers never matches (safety)
        return has_any_trigger

    def trigger_escalation(
        self,
        policy: EscalationPolicy,
        session_id: str,
        project_id: str,
        agent_id: str,
        node_id: str,
        node_kind: str,
        node_label: str,
        node_content: Dict[str, Any],
        node_confidence_value: Optional[float],
        node_confidence_source: Optional[str],
        node_capabilities: List[str],
    ) -> Optional[EscalationRecord]:
        """
        Creates an escalation record via the gateway API and returns it.
        If timeout_behavior is 'block', the caller should raise EscalationRequired.
        If 'abort', the caller should raise EscalationAborted.
        If 'proceed_with_flag', returns the record but doesn't block.
        """
        if not self._enabled:
            return None

        payload = {
            "policy_id": policy.id,
            "session_id": session_id,
            "project_id": project_id,
            "agent_id": agent_id,
            "node_id": node_id,
            "node_kind": node_kind,
            "node_label": node_label,
            "node_content": node_content,
            "node_confidence_value": node_confidence_value,
            "node_confidence_source": node_confidence_source or "",
            "node_capabilities": node_capabilities,
            "timeout_seconds": policy.timeout_seconds,
        }

        try:
            response = requests.post(
                f"{self._gateway_endpoint}/api/v1/escalations",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=5.0,
            )
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                record = EscalationRecord.from_dict(data)
                record.policy_name = policy.name
                logger.warning(
                    "⚠️ ESCALATION TRIGGERED: policy='%s', node='%s' (%s), "
                    "behavior='%s', escalation_id='%s'",
                    policy.name, node_label, node_kind,
                    policy.timeout_behavior, record.id,
                )
                return record
            else:
                logger.error(
                    "Failed to create escalation record: HTTP %d — %s",
                    response.status_code, response.text,
                )
        except requests.exceptions.ConnectionError:
            logger.error(
                "Gateway unreachable — cannot create escalation record. "
                "Policy '%s' triggered but not enforced.", policy.name,
            )
        except Exception as e:
            logger.error("Escalation trigger failed: %s", str(e))

        return None

    def poll_resolution(
        self, escalation_id: str, timeout_seconds: int = 300, poll_interval: float = 2.0
    ) -> EscalationRecord:
        """
        Blocks and polls the gateway for escalation resolution.
        Used when timeout_behavior='block'. Returns the resolved record
        or raises EscalationTimedOut if the timeout expires.
        """
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                response = requests.get(
                    f"{self._gateway_endpoint}/api/v1/escalations/{escalation_id}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=3.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "pending")
                    if status != "pending":
                        record = EscalationRecord.from_dict(data)
                        if status == "rejected":
                            raise EscalationAborted(
                                escalation_id=record.id,
                                policy_name=record.policy_name,
                                message=f"Escalation rejected by {record.resolved_by}: "
                                        f"{record.resolution_reason}",
                            )
                        # approved
                        logger.info(
                            "✅ Escalation '%s' resolved: %s by %s",
                            escalation_id, status, data.get("resolved_by", "unknown"),
                        )
                        return record
            except (EscalationAborted, EscalationTimedOut):
                raise
            except Exception as e:
                logger.debug("Poll error: %s", str(e))

            time.sleep(poll_interval)

        raise EscalationTimedOut(
            escalation_id=escalation_id,
            policy_name="",
            message=f"Escalation '{escalation_id}' timed out after {timeout_seconds}s "
                    f"without resolution.",
        )
