from typing import Dict, Any, List, Optional
import re

class ContractViolation:
    def __init__(self, node_id: str, node_name: str, rule: str, message: str, details: Dict[str, Any]):
        self.node_id = node_id
        self.node_name = node_name
        self.rule = rule
        self.message = message
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "rule": self.rule,
            "message": self.message,
            "details": self.details
        }

class BehaviorContract:
    """
    Asserts and enforces behavioral rules and constraints on trace execution paths.
    """
    def __init__(
        self,
        max_cost: Optional[float] = None,
        forbidden_tools: Optional[List[str]] = None,
        required_explanations: Optional[List[str]] = None,
        tool_value_constraints: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ):
        self.max_cost = max_cost
        self.forbidden_tools = forbidden_tools or []
        self.required_explanations = required_explanations or []
        # tool_value_constraints mapping: tool_name -> list of rules (e.g., {"field": "amount", "operator": "lt", "value": 1000})
        self.tool_value_constraints = tool_value_constraints or {}

    def verify_trace(self, nodes: List[Dict[str, Any]]) -> List[ContractViolation]:
        violations = []

        for node in nodes:
            node_id = node.get("id", "unknown")
            node_name = node.get("name", node.get("label", "unknown"))
            category = node.get("category", node.get("kind", ""))
            content = node.get("content", {})
            metrics = node.get("metrics", {})

            # 1. Financial caps check
            if self.max_cost is not None:
                cost = metrics.get("cost_usd", content.get("cost", 0.0))
                if cost > self.max_cost:
                    violations.append(ContractViolation(
                        node_id=node_id,
                        node_name=node_name,
                        rule="max_cost",
                        message=f"Cost ${cost} exceeds financial limit of ${self.max_cost}.",
                        details={"actual_cost": cost, "limit": self.max_cost}
                    ))

            # 2. Forbidden tools check
            if category == "tool_invocation" or category == "tool":
                if node_name in self.forbidden_tools:
                    violations.append(ContractViolation(
                        node_id=node_id,
                        node_name=node_name,
                        rule="forbidden_tools",
                        message=f"Forbidden tool '{node_name}' was invoked.",
                        details={"tool_name": node_name}
                    ))

            # 3. Required explanation check
            if node_name in self.required_explanations:
                explanation = content.get("explanation", content.get("reason", ""))
                if not explanation:
                    violations.append(ContractViolation(
                        node_id=node_id,
                        node_name=node_name,
                        rule="required_explanation",
                        message=f"Action '{node_name}' requires an explanation, but none was provided.",
                        details={"node_name": node_name}
                    ))

            # 4. Tool value constraints check
            if (category == "tool_invocation" or category == "tool") and node_name in self.tool_value_constraints:
                rules = self.tool_value_constraints[node_name]
                inp = content.get("input", {})
                # Normalize stringified input if necessary
                if isinstance(inp, str):
                    try:
                        import json
                        inp = json.loads(inp)
                    except Exception:
                        pass
                
                if isinstance(inp, dict):
                    for rule in rules:
                        field = rule.get("field")
                        operator = rule.get("operator")
                        expected = rule.get("value")
                        
                        val = inp.get(field)
                        if val is not None:
                            violated = False
                            if operator == "lt" and not (val < expected):
                                violated = True
                            elif operator == "gt" and not (val > expected):
                                violated = True
                            elif operator == "eq" and not (val == expected):
                                violated = True
                            elif operator == "regex" and not re.search(str(expected), str(val)):
                                violated = True

                            if violated:
                                violations.append(ContractViolation(
                                    node_id=node_id,
                                    node_name=node_name,
                                    rule=f"value_constraint.{field}",
                                    message=f"Value constraint failed: {field} (value: {val}) must satisfy {operator} {expected}.",
                                    details={"field": field, "actual": val, "expected": expected, "operator": operator}
                                ))

        return violations


from functools import wraps
from typing import Callable

def behavior_contract(
    max_price: Optional[float] = None,
    allowed_country: Optional[str] = None,
    confirmation: bool = False,
    human_required: bool = False
):
    """
    Decorator for agent tools or actions to enforce behavioral policies at runtime.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Parse arguments
            all_vals = list(args) + list(kwargs.values())
            
            # 1. Price constraint check
            if max_price is not None:
                price = kwargs.get("price", kwargs.get("amount", kwargs.get("cost")))
                if price is None:
                    for arg in args:
                        if isinstance(arg, (int, float)):
                            price = arg
                            break
                if price is not None and price > max_price:
                    raise ValueError(f"Contract Violation: Price {price} exceeds limit of {max_price}.")

            # 2. Allowed country check
            if allowed_country is not None:
                country = kwargs.get("country", kwargs.get("destination"))
                if country is None:
                    for arg in args:
                        if isinstance(arg, str) and len(arg) > 2:
                            country = arg
                if country is not None and country != allowed_country:
                    raise ValueError(f"Contract Violation: Country '{country}' is not allowed (must be '{allowed_country}').")

            # 3. Execution
            return func(*args, **kwargs)
        return wrapper
    return decorator
