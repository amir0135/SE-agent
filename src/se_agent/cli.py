"""Command-line entry point and agent assembly.

Wires Settings -> tools -> LLM -> Agent. Selects fakes (dry mode) when the environment is
not fully configured, so the agent always runs without secrets or network.
"""

from __future__ import annotations

import argparse
import json
import sys

from .agent import Agent
from .config import Settings
from .llm.base import LLM
from .llm.fake import FakeLLM
from .logging import get_logger
from .tools.auth import FakeTokenProvider, MsalTokenProvider
from .tools.crm import CrmClient, FakeCrmClient, HttpCrmClient
from .tools.echo import EchoTool
from .tools.msx import MsxTool
from .tools.notes import NotesTool
from .tools.registry import ToolRegistry


def build_crm_client(settings: Settings) -> CrmClient | None:
    """Return a live CRM client when configured, a fake when in dry mode, else None."""
    if settings.dry_run:
        return FakeCrmClient()
    if not settings.crm.configured:
        return None
    if settings.crm.client_secret:
        provider = MsalTokenProvider(
            tenant_id=settings.crm.tenant_id or "",
            client_id=settings.crm.client_id or "",
            client_secret=settings.crm.client_secret,
        )
    else:
        # Without a secret we cannot do app-only auth; fall back to unavailable rather
        # than guessing an interactive flow in a non-interactive CLI.
        return None
    return HttpCrmClient(crm_url=settings.crm.crm_url or "", token_provider=provider)


def build_llm(settings: Settings) -> LLM:
    if settings.dry_run:
        return FakeLLM()
    # Live LLM is optional; import lazily to avoid requiring the SDK in base installs.
    from .llm.openai_llm import OpenAILLM

    return OpenAILLM(settings.llm)


def build_registry(crm: CrmClient | None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(MsxTool(crm))
    registry.register(EchoTool())
    registry.register(NotesTool())
    return registry


def build_agent(settings: Settings | None = None) -> Agent:
    settings = settings or Settings.from_env()
    crm = build_crm_client(settings)
    llm = build_llm(settings)
    registry = build_registry(crm)
    return Agent(llm=llm, registry=registry, dry_run=settings.dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="se-agent",
        description="Solution Engineer agent with pluggable tools (including MSX / Dynamics CRM).",
    )
    parser.add_argument("prompt", nargs="*", help="The question or task for the agent.")
    parser.add_argument("--json", action="store_true", help="Emit the result as JSON.")
    parser.add_argument(
        "--list-tools", action="store_true", help="List available tools and exit."
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    agent = build_agent(settings)

    if args.list_tools:
        registry = build_registry(build_crm_client(settings))
        tools = [
            {**t.descriptor(), "available": t.available()} for t in registry.list()
        ]
        print(json.dumps(tools, indent=2))
        return 0

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        if sys.stdin.isatty():
            parser.error("Provide a prompt, e.g.: se-agent \"Contoso open pipeline\"")
        prompt = sys.stdin.read().strip()
    if not prompt:
        parser.error("Empty prompt.")

    log = get_logger()
    if settings.dry_run:
        log.info("running in DRY mode (no live model/CRM)")

    result = agent.run(prompt)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.answer)
        if result.dry_run:
            print("\n[dry run — used sample data, no network]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
