"""The agent loop: plan -> validate -> dispatch -> finalize (Constitution: deterministic core)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .llm.base import LLM, ToolCall
from .logging import get_logger, redact
from .tools.base import ToolError, apply_defaults, validate
from .tools.registry import ToolRegistry


@dataclass
class ToolInvocation:
    tool: str
    args: dict[str, Any]
    ok: bool
    latency_ms: int
    error: str | None = None


@dataclass
class AgentResult:
    answer: str
    tool_trace: list[ToolInvocation] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "dry_run": self.dry_run,
            "tool_trace": [
                {
                    "tool": t.tool,
                    "args": t.args,
                    "ok": t.ok,
                    "latency_ms": t.latency_ms,
                    "error": t.error,
                }
                for t in self.tool_trace
            ],
        }


class Agent:
    def __init__(self, llm: LLM, registry: ToolRegistry, dry_run: bool = False) -> None:
        self._llm = llm
        self._registry = registry
        self._dry_run = dry_run
        self._log = get_logger()

    def run(self, prompt: str) -> AgentResult:
        descriptors = self._registry.descriptors(available_only=True)
        calls = self._llm.plan(prompt, descriptors)

        trace: list[ToolInvocation] = []
        results: list[dict[str, Any]] = []

        for call in calls:
            invocation, result = self._dispatch(call)
            trace.append(invocation)
            results.append(result)

        answer = self._llm.finalize(prompt, results)
        return AgentResult(answer=answer, tool_trace=trace, dry_run=self._dry_run)

    def _dispatch(self, call: ToolCall) -> tuple[ToolInvocation, dict[str, Any]]:
        start = time.monotonic()
        safe_args = redact(call.arguments)

        # 1. Unknown tool -> structured error, keep going.
        if not self._registry.has(call.name):
            self._log.warning("unknown tool requested: %s", call.name)
            latency = int((time.monotonic() - start) * 1000)
            return (
                ToolInvocation(call.name, safe_args, False, latency, "unknown_tool"),
                {"tool": call.name, "ok": False, "error": f"Unknown tool '{call.name}'"},
            )

        tool = self._registry.get(call.name)

        # 2. Validate model-supplied args against the schema (untrusted input gate).
        try:
            args = apply_defaults(tool.input_schema, dict(call.arguments))
            validate(tool.input_schema, args)
        except ToolError as exc:
            self._log.warning("validation failed for %s: %s", call.name, exc.message)
            latency = int((time.monotonic() - start) * 1000)
            return (
                ToolInvocation(call.name, safe_args, False, latency, exc.message),
                {"tool": call.name, "ok": False, "error": exc.message},
            )

        # 3. Execute.
        self._log.info("invoking tool %s args=%s", call.name, redact(args))
        try:
            result = tool.run(args)
            ok = result.ok
            error = result.error
            data = result.data
        except ToolError as exc:
            ok, error, data = False, exc.message, None
        except Exception as exc:  # never leak raw exceptions/secrets
            self._log.exception("tool %s crashed", call.name)
            ok, error, data = False, f"internal error in '{call.name}'", None

        latency = int((time.monotonic() - start) * 1000)
        self._log.info("tool %s ok=%s latency=%dms", call.name, ok, latency)
        invocation = ToolInvocation(call.name, redact(args), ok, latency, error)
        payload = {"tool": call.name, "ok": ok, "data": data, "error": error}
        return invocation, payload
