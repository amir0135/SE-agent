"""Tool base classes plus a minimal stdlib JSON-Schema validator.

Constitution: every capability is a Tool with name/description/input_schema and a single
run() entry point; model-supplied arguments are validated before execution.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None

    @classmethod
    def success(cls, data: Any) -> "ToolResult":
        return cls(ok=True, data=data)

    @classmethod
    def failure(cls, error: str) -> "ToolResult":
        return cls(ok=False, error=error)


class ToolError(Exception):
    """Structured tool failure. ``code`` is one of: auth, transport, validation,
    not_found, unknown_tool, internal. Never carries secret values."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Tool(abc.ABC):
    """Abstract base for all tools."""

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)  # type: ignore[assignment]

    def available(self) -> bool:  # noqa: D401 - simple predicate
        """Whether this tool can run in the current environment. Default: always."""
        return True

    @abc.abstractmethod
    def run(self, args: dict[str, Any]) -> ToolResult:
        """Execute the tool. ``args`` has already been schema-validated by the agent."""
        raise NotImplementedError

    def descriptor(self) -> dict[str, Any]:
        """MCP-compatible descriptor (name/description/inputSchema)."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


# --------------------------------------------------------------------------------------
# Minimal JSON Schema validation (stdlib only). Supports the subset used by our tools:
# type (object/string/integer/number/boolean/array), properties, required, enum,
# minimum/maximum, additionalProperties=false, and defaults application.
# --------------------------------------------------------------------------------------

_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
}


def apply_defaults(schema: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``args`` with object-level defaults applied."""
    out = dict(args)
    for key, prop in (schema.get("properties") or {}).items():
        if key not in out and isinstance(prop, dict) and "default" in prop:
            out[key] = prop["default"]
    return out


def validate(schema: dict[str, Any], value: Any, path: str = "$") -> None:
    """Validate ``value`` against ``schema``; raise ToolError(code='validation') on failure."""
    expected = schema.get("type")
    if expected:
        types = _TYPE_MAP.get(expected)
        if types is None:
            raise ToolError("validation", f"{path}: unsupported schema type '{expected}'")
        # bool is a subclass of int; guard integer/number against bool.
        if expected in {"integer", "number"} and isinstance(value, bool):
            raise ToolError("validation", f"{path}: expected {expected}, got boolean")
        if not isinstance(value, types):
            raise ToolError(
                "validation", f"{path}: expected {expected}, got {type(value).__name__}"
            )

    if "enum" in schema and value not in schema["enum"]:
        raise ToolError("validation", f"{path}: '{value}' not in {schema['enum']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ToolError("validation", f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ToolError("validation", f"{path}: {value} > maximum {schema['maximum']}")

    if expected == "object" and isinstance(value, dict):
        props: dict[str, Any] = schema.get("properties") or {}
        for req in schema.get("required", []):
            if req not in value:
                raise ToolError("validation", f"{path}: missing required property '{req}'")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            if extra:
                raise ToolError(
                    "validation", f"{path}: unexpected propert(ies) {sorted(extra)}"
                )
        for key, sub in value.items():
            if key in props:
                validate(props[key], sub, f"{path}.{key}")

    if expected == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                validate(item_schema, item, f"{path}[{i}]")
