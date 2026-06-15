"""A simple in-memory scratchpad tool (extensibility demo)."""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolResult


class NotesTool(Tool):
    name = "notes"
    description = "Store and retrieve short notes during a session (in-memory)."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list"]},
            "text": {"type": "string"},
        },
        "required": ["action"],
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        self._notes: list[str] = []

    def run(self, args: dict[str, Any]) -> ToolResult:
        action = args["action"]
        if action == "add":
            text = args.get("text", "").strip()
            if not text:
                return ToolResult.failure("Cannot add an empty note")
            self._notes.append(text)
            return ToolResult.success({"added": text, "count": len(self._notes)})
        return ToolResult.success({"notes": list(self._notes)})
