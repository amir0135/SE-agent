"""Optional live LLM adapter (Azure OpenAI / OpenAI), lazily importing the SDK.

This adapter is only constructed for live runs. It is intentionally thin: it asks the
model to choose a tool via JSON, then to compose a final answer. Kept minimal because the
deterministic core and all tests use FakeLLM.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import LlmConfig
from .base import LLM, ToolCall

_PLAN_SYSTEM = (
    "You are SE-Agent, an assistant for Solution Engineers. You have access to the tools "
    "listed below. Decide whether to call a tool. Respond ONLY with JSON of the form "
    '{"tool_calls": [{"name": "<tool>", "arguments": { ... }}]}. '
    "Return an empty list if no tool is needed. Arguments must match the tool's inputSchema."
)


class OpenAILLM(LLM):
    def __init__(self, config: LlmConfig) -> None:
        self._config = config
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            if self._config.provider == "azure-openai":
                from openai import AzureOpenAI  # type: ignore

                self._client = AzureOpenAI(
                    api_key=self._config.api_key,
                    azure_endpoint=self._config.endpoint or "",
                    api_version="2024-06-01",
                )
            else:
                from openai import OpenAI  # type: ignore

                self._client = OpenAI(api_key=self._config.api_key)
        except ImportError as exc:  # pragma: no cover - only in live installs
            raise RuntimeError(
                "openai is not installed; install the 'live' extra to use a real model"
            ) from exc
        return self._client

    def _chat(self, messages: list[dict[str, str]]) -> str:
        client = self._ensure_client()
        resp = client.chat.completions.create(
            model=self._config.deployment,
            messages=messages,
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    def plan(self, prompt: str, tools: list[dict[str, Any]]) -> list[ToolCall]:
        content = self._chat(
            [
                {"role": "system", "content": _PLAN_SYSTEM},
                {
                    "role": "user",
                    "content": f"Tools:\n{json.dumps(tools)}\n\nUser request: {prompt}",
                },
            ]
        )
        try:
            parsed = json.loads(content)
            calls = parsed.get("tool_calls", [])
        except (json.JSONDecodeError, AttributeError):
            return []
        return [
            ToolCall(name=c["name"], arguments=c.get("arguments", {}))
            for c in calls
            if isinstance(c, dict) and "name" in c
        ]

    def finalize(self, prompt: str, results: list[dict[str, Any]]) -> str:
        return self._chat(
            [
                {
                    "role": "system",
                    "content": "Compose a concise, helpful answer for a Solution Engineer "
                    "using the tool results. Do not invent data.",
                },
                {
                    "role": "user",
                    "content": f"Request: {prompt}\n\nTool results:\n{json.dumps(results)}",
                },
            ]
        )
