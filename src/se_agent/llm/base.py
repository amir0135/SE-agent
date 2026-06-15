"""LLM interface.

The agent depends only on this small surface so the deterministic core can be tested with
a scripted fake. A ``plan`` proposes tool calls; ``finalize`` composes the answer from
tool results.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


class LLM(abc.ABC):
    @abc.abstractmethod
    def plan(self, prompt: str, tools: list[dict[str, Any]]) -> list[ToolCall]:
        """Given the user prompt and available tool descriptors, propose tool calls.

        Returning an empty list means "answer directly, no tools needed".
        """
        raise NotImplementedError

    @abc.abstractmethod
    def finalize(self, prompt: str, results: list[dict[str, Any]]) -> str:
        """Compose the final natural-language answer from the prompt and tool results."""
        raise NotImplementedError
