"""A deterministic, rule-based FakeLLM for dry mode and tests.

It uses simple keyword heuristics to decide which tool to call and to compose an answer.
No network, no model — fully reproducible.
"""

from __future__ import annotations

import re
from typing import Any

from .base import LLM, ToolCall

# Capture a likely account name: consecutive Capitalized words right after "for".
# Stops at the first lowercase connector word (e.g. "and", "the", "pipeline").
_ACCOUNT_RE = re.compile(r"\bfor\s+([A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*)")


def _guess_account(prompt: str) -> str | None:
    m = _ACCOUNT_RE.search(prompt)
    if m:
        return m.group(1).strip()
    return None


class FakeLLM(LLM):
    def plan(self, prompt: str, tools: list[dict[str, Any]]) -> list[ToolCall]:
        text = prompt.lower()
        names = {t["name"] for t in tools}

        if "msx" in names and any(
            kw in text
            for kw in ("opportunit", "pipeline", "deal", "crm", "account", "activit")
        ):
            account = _guess_account(prompt)
            if "activit" in text:
                op = "recent_activities"
            elif "contact" in text:
                op = "contacts"
            elif "account" in text and "opportun" not in text and "pipeline" not in text:
                op = "accounts"
            else:
                op = "open_opportunities"
            args: dict[str, Any] = {"operation": op}
            if account:
                args["account_name"] = account
            return [ToolCall(name="msx", arguments=args)]

        if "echo" in names and text.startswith("echo "):
            return [ToolCall(name="echo", arguments={"text": prompt[5:]})]

        if "list" in text and "tool" in text:
            return []  # answered directly in finalize

        return []

    def finalize(self, prompt: str, results: list[dict[str, Any]]) -> str:
        if not results:
            return (
                "I didn't need any tools for that. Ask me about an account's open "
                "opportunities, pipeline, contacts, or recent activities and I'll use MSX."
            )

        lines: list[str] = []
        for r in results:
            tool = r.get("tool")
            if not r.get("ok"):
                lines.append(f"[{tool}] error: {r.get('error')}")
                continue
            data = r.get("data") or {}
            if tool == "msx":
                lines.append(_summarize_msx(data))
            else:
                lines.append(f"[{tool}] {data}")
        return "\n".join(lines)


def _summarize_msx(data: dict[str, Any]) -> str:
    if "opportunities" in data:
        opps = data["opportunities"]
        if not opps:
            return "No open opportunities found for that account."
        out = [f"Found {data['count']} open opportunit(ies):"]
        for o in opps:
            value = o.get("estimated_value")
            value_str = f"${value:,.0f}" if isinstance(value, (int, float)) else "n/a"
            out.append(
                f"  • {o.get('name')} — {o.get('stage')} — {value_str}"
                f" (close {o.get('close_date')})"
            )
        total = data.get("total_estimated_value") or 0
        out.append(f"Total pipeline: ${total:,.0f}")
        return "\n".join(out)
    if "accounts" in data:
        accts = data["accounts"]
        if not accts:
            return "No matching accounts found."
        return "Accounts:\n" + "\n".join(f"  • {a.get('name')}" for a in accts)
    if "contacts" in data:
        cons = data["contacts"]
        if not cons:
            return "No matching contacts found."
        return "Contacts:\n" + "\n".join(
            f"  • {c.get('name')} <{c.get('email')}> ({c.get('account_name')})" for c in cons
        )
    if "activities" in data:
        acts = data["activities"]
        if not acts:
            return "No recent activities found."
        return "Recent activities:\n" + "\n".join(
            f"  • [{a.get('type')}] {a.get('subject')} — {a.get('regarding')}" for a in acts
        )
    return str(data)
