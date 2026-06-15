"""Render a Teams Adaptive Card data payload for the morning brief.

This is a deterministic helper (no model, no network) that turns Cloud MSX Worker query
output into the `$data` binding consumed by ``samples/teams/morning-brief.card.json``.
The orchestrator can call this to populate the card it posts to Teams.
"""

from __future__ import annotations

from typing import Any


def build_brief_data(
    *,
    user: str,
    date: str,
    meetings: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    handled: list[str] | None = None,
    deadlines: list[dict[str, Any]] | None = None,
    pipeline_query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the Adaptive Card data binding for the morning brief.

    ``pipeline_query`` is the ``data`` object returned by the worker's ``/msx/query``
    ``open_opportunities`` operation; its ``count`` drives the pipeline line.
    """
    meetings = meetings or []
    decisions = decisions or []
    pipeline_count = 0
    if pipeline_query:
        pipeline_count = int(pipeline_query.get("count", 0))

    # Number the decisions for display.
    numbered = []
    for i, d in enumerate(decisions, start=1):
        numbered.append({**d, "index": i})

    return {
        "user": user,
        "date": date,
        "meetings": {"count": len(meetings), "items": meetings},
        "decisions": {"count": len(numbered), "items": numbered},
        "handled": handled or [],
        "deadlines": deadlines or [],
        "pipeline": {"count": pipeline_count},
    }
