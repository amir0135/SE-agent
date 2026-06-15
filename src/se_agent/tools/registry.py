"""Tool registry: register, look up, and enumerate tools (Constitution: Tool-First)."""

from __future__ import annotations

from .base import Tool, ToolError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool must declare a non-empty name")
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolError("unknown_tool", f"No tool named '{name}'") from None

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def descriptors(self, available_only: bool = False) -> list[dict]:
        return [
            t.descriptor()
            for t in self._tools.values()
            if (not available_only or t.available())
        ]
