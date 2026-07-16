"""
VERI Auto-Instrumentation — Monkey-patch hooks for LLM frameworks.

Intercepts at the framework's serialization boundary to capture
tool inputs/outputs, LLM calls, and token usage without requiring
any changes to the agent's source code.

Supported frameworks:
  - openai (>=1.0)
  - langchain (langchain-core callbacks)
"""

import sys
import time
import logging
from typing import Any

from .context import (
    active_session_context,
    ExecutionSpanScope,
)

logger = logging.getLogger("veri.patching")

# Track what's been patched to prevent double-patching
_patched_frameworks: set[str] = set()


def patch_runtime(framework_name: str, client) -> None:
    """Applies instrumentation hooks for the given framework."""
    if framework_name in _patched_frameworks:
        logger.debug("Framework '%s' already patched. Skipping.", framework_name)
        return

    dispatchers = {
        "openai": _patch_openai,
        "langchain": _patch_langchain,
    }

    dispatcher = dispatchers.get(framework_name)
    if dispatcher is None:
        logger.warning(
            "Framework '%s' is not supported for auto-instrumentation. "
            "Supported: %s",
            framework_name,
            ", ".join(dispatchers.keys()),
        )
        return

    dispatcher(client)
    _patched_frameworks.add(framework_name)


# ── OpenAI Instrumentation ─────────────────────────────────────────

# Approximate per-token costs (USD) for common models.
# Used for L0 budget tracking. Not for billing — just guardrails.
_MODEL_COSTS = {
    "gpt-4o": (0.005 / 1000, 0.015 / 1000),
    "gpt-4o-mini": (0.00015 / 1000, 0.0006 / 1000),
    "gpt-4-turbo": (0.01 / 1000, 0.03 / 1000),
    "gpt-3.5-turbo": (0.0005 / 1000, 0.0015 / 1000),
}

_DEFAULT_COST = (0.000005, 0.000015)  # Conservative fallback


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimates USD cost from token counts. Best-effort, not exact."""
    input_rate, output_rate = _DEFAULT_COST
    for model_prefix, rates in _MODEL_COSTS.items():
        if model and model.startswith(model_prefix):
            input_rate, output_rate = rates
            break
    return (prompt_tokens * input_rate) + (completion_tokens * output_rate)


def _patch_openai(client) -> None:
    try:
        import openai

        # 1. Patch Synchronous Client
        original_create = openai.resources.chat.completions.Completions.create

        def patched_create(self_openai, *args, **kwargs):
            session = active_session_context.get(None)
            if not session:
                return original_create(self_openai, *args, **kwargs)

            model = kwargs.get("model", "unknown")

            # Pre-flight L0 check (before spending any tokens)
            session.increment_and_verify_l0(cost_delta=0.0)

            span = ExecutionSpanScope(client, "llm", f"openai.{model}", kwargs)
            span.__enter__()

            try:
                result = original_create(self_openai, *args, **kwargs)

                prompt_tokens = getattr(result.usage, "prompt_tokens", 0) if result.usage else 0
                completion_tokens = getattr(result.usage, "completion_tokens", 0) if result.usage else 0
                cost = _estimate_cost(model, prompt_tokens, completion_tokens)

                # Update session budget with actual cost
                session.increment_and_verify_l0(cost_delta=cost)

                content = ""
                if result.choices and result.choices[0].message:
                    content = result.choices[0].message.content or ""

                span.complete(
                    output_data=content,
                    metrics={
                        "tokens_input": prompt_tokens,
                        "tokens_output": completion_tokens,
                        "cost_usd": cost,
                        "model": model,
                    },
                )
                return result

            except Exception as e:
                span.__exit__(type(e), e, e.__traceback__)
                raise

        openai.resources.chat.completions.Completions.create = patched_create

        # 2. Patch Asynchronous Client
        original_async_create = openai.resources.chat.completions.AsyncCompletions.create

        async def patched_async_create(self_openai, *args, **kwargs):
            session = active_session_context.get(None)
            if not session:
                return await original_async_create(self_openai, *args, **kwargs)

            model = kwargs.get("model", "unknown")

            # Pre-flight L0 check (before spending any tokens)
            session.increment_and_verify_l0(cost_delta=0.0)

            span = ExecutionSpanScope(client, "llm", f"openai.{model}", kwargs)
            span.__enter__()

            try:
                result = await original_async_create(self_openai, *args, **kwargs)

                prompt_tokens = getattr(result.usage, "prompt_tokens", 0) if result.usage else 0
                completion_tokens = getattr(result.usage, "completion_tokens", 0) if result.usage else 0
                cost = _estimate_cost(model, prompt_tokens, completion_tokens)

                # Update session budget with actual cost
                session.increment_and_verify_l0(cost_delta=cost)

                content = ""
                if result.choices and result.choices[0].message:
                    content = result.choices[0].message.content or ""

                span.complete(
                    output_data=content,
                    metrics={
                        "tokens_input": prompt_tokens,
                        "tokens_output": completion_tokens,
                        "cost_usd": cost,
                        "model": model,
                    },
                )
                return result

            except Exception as e:
                span.__exit__(type(e), e, e.__traceback__)
                raise

        openai.resources.chat.completions.AsyncCompletions.create = patched_async_create
        logger.info("OpenAI auto-instrumentation active (Sync + Async).")

    except ImportError:
        logger.debug("openai package not installed. Skipping instrumentation.")


# ── LangChain Instrumentation ──────────────────────────────────────


def _patch_langchain(client) -> None:
    try:
        from langchain_core.callbacks import BaseCallbackHandler

        class VeriLangChainCallback(BaseCallbackHandler):
            """
            Hooks into LangChain's native callback pipeline.
            Captures executions at the framework's internal serialization boundaries
            across chains, tools, and LLM blocks.
            """

            def __init__(self):
                self._scopes: dict[Any, ExecutionSpanScope] = {}

            # ── Chain Spans ─────────────────────────────────────────
            def on_chain_start(
                self, serialized: dict[str, Any], inputs: dict[str, Any], *, run_id, **kwargs
            ) -> None:
                chain_name = serialized.get("name") or kwargs.get("name") or "chain"
                scope = ExecutionSpanScope(client, "reasoning", chain_name, inputs)
                self._scopes[run_id] = scope
                scope.__enter__()

            def on_chain_end(self, outputs: dict[str, Any], *, run_id, **kwargs) -> None:
                scope = self._scopes.pop(run_id, None)
                if scope:
                    scope.complete(output_data=outputs)

            def on_chain_error(self, error: BaseException, *, run_id, **kwargs) -> None:
                scope = self._scopes.pop(run_id, None)
                if scope:
                    scope.__exit__(type(error), error, error.__traceback__)

            # ── Tool Spans ──────────────────────────────────────────
            def on_tool_start(
                self, serialized: dict[str, Any], input_str: str, *, run_id, **kwargs
            ) -> None:
                tool_name = serialized.get("name", "unknown_tool")
                scope = ExecutionSpanScope(
                    client, "tool", tool_name, {"raw_input": input_str}
                )
                self._scopes[run_id] = scope
                scope.__enter__()

            def on_tool_end(self, output: Any, *, run_id, **kwargs) -> None:
                scope = self._scopes.pop(run_id, None)
                if scope:
                    scope.complete(output_data={"raw_output": str(output)})

            def on_tool_error(
                self, error: BaseException, *, run_id, **kwargs
            ) -> None:
                scope = self._scopes.pop(run_id, None)
                if scope:
                    scope.__exit__(type(error), error, error.__traceback__)

            # ── LLM Spans ───────────────────────────────────────────
            def on_llm_start(
                self, serialized: dict[str, Any], prompts: list[str], *, run_id, **kwargs
            ) -> None:
                # Retrieve model name from serialized or invocation params
                invocation_params = kwargs.get("invocation_params", {})
                model_name = invocation_params.get("model_name") or invocation_params.get("model") or "unknown_llm"
                scope = ExecutionSpanScope(
                    client, "llm", f"langchain.{model_name}", {"prompts": prompts}
                )
                self._scopes[run_id] = scope
                scope.__enter__()

            def on_llm_end(self, response: Any, *, run_id, **kwargs) -> None:
                scope = self._scopes.pop(run_id, None)
                if not scope:
                    return

                # Attempt to extract response strings and usage
                content = ""
                metrics = {}
                try:
                    if hasattr(response, "generations") and response.generations:
                        # Extract first text completion
                        gens = response.generations[0]
                        if gens:
                            content = gens[0].text

                    if hasattr(response, "llm_output") and response.llm_output:
                        llm_out = response.llm_output
                        token_usage = llm_out.get("token_usage") or llm_out.get("usage") or {}
                        prompt_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
                        completion_tokens = token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
                        model_name = llm_out.get("model_name") or "unknown"
                        cost = _estimate_cost(model_name, prompt_tokens, completion_tokens)
                        
                        metrics = {
                            "tokens_input": prompt_tokens,
                            "tokens_output": completion_tokens,
                            "cost_usd": cost,
                            "model": model_name
                        }
                        
                        # Apply local budget L0 check updates
                        session = active_session_context.get(None)
                        if session:
                            session.increment_and_verify_l0(cost_delta=cost)
                except Exception as e:
                    logger.debug("Failed to extract LLM telemetry details: %s", str(e))

                scope.complete(output_data=content, metrics=metrics)

            def on_llm_error(
                self, error: BaseException, *, run_id, **kwargs
            ) -> None:
                scope = self._scopes.pop(run_id, None)
                if scope:
                    scope.__exit__(type(error), error, error.__traceback__)

        # Expose the handler class so users can plug it into their chain
        sys.modules["veri"].LangChainHandler = VeriLangChainCallback
        logger.info("LangChain auto-instrumentation active. Use veri.LangChainHandler().")

    except ImportError:
        logger.debug("langchain-core not installed. Skipping instrumentation.")

