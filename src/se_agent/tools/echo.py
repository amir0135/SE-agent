"""A trivial example tool demonstrating extensibility (Constitution: Tool-First)."""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolResult


class EchoTool(Tool):
    name = "echo"
    description = "Echo back the provided text. Useful as an extensibility example."
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }

    def run(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult.success({"text": args["text"]})
