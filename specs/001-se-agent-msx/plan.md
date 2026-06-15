# Implementation Plan: SE-Agent — Solution Engineer Agent with Pluggable Tools (incl. MSX)

**Branch**: `001-se-agent-msx` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-se-agent-msx/spec.md`

## Summary

Build a Python CLI agent for Solution Engineers that reasons over a registry of Tools and
answers natural-language questions. The flagship Tool, `msx`, reads Dynamics CRM / MSX data
via MSAL auth + the CRM Web API (`/api/data/v9.2/`), mirroring the MSX Helper desktop app.
The agent core (loop, dispatch, schema validation) is deterministic and fully testable with
fake LLM and fake CRM clients; live LLM and CRM access are injected via interfaces and
configured purely from the environment. A dry/offline mode lets the whole pipeline run with
no secrets and no network.

## Technical Context

**Language/Version**: Python 3.11+ (repo has 3.13; target 3.11+ for portability)
**Primary Dependencies**: standard library first. Optional extras (lazy-imported): `msal`
(Entra auth), `httpx` (CRM HTTP), `openai`/`azure` SDK (LLM). Tests use no network.
**Storage**: None (stateless v1; in-memory token cache only)
**Testing**: `pytest`
**Target Platform**: macOS/Linux CLI (local)
**Project Type**: Single project — CLI + library
**Performance Goals**: Interactive CLI latency dominated by LLM/CRM round-trips; core
dispatch overhead negligible (<10 ms)
**Constraints**: Offline-capable (dry mode = zero network); no secrets in source/logs;
LLM output treated as untrusted
**Scale/Scope**: Single-user local CLI; ~4 built-in tools; read-only CRM scenarios in v1

## Constitution Check

*GATE: Must pass before and after design.*

- **I. Tool-First Architecture** — PASS. Capabilities live in `Tool` subclasses registered
  in a `ToolRegistry`; agent loop never special-cases a tool.
- **II. MSX Is a First-Class Tool** — PASS. All CRM access flows through the `msx` Tool and
  its `CrmClient`; no other module touches CRM.
- **III. Deterministic Core, Probabilistic Edge** — PASS. `LLM` and `CrmClient` are
  interfaces with fakes; only the planning step calls a real model.
- **IV. Secrets Never Touch the Repo** — PASS. All config via env (`Settings.from_env`);
  `.env.example` documents keys; `.gitignore` excludes `.env`. Dry mode needs no secrets.
- **V. Observability & Text I/O** — PASS. Structured per-invocation logging with redaction;
  CLI does text in / text out with `--json` option.

No violations; no Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/001-se-agent-msx/
├── spec.md           # Feature specification
├── plan.md           # This file
├── research.md       # Phase 0 — MSX Helper behavior + decisions
├── data-model.md     # Phase 1 — entities
├── quickstart.md     # Phase 1 — how to run
├── contracts/        # Phase 1 — tool I/O contracts
│   ├── tool-interface.md
│   └── msx-tool.md
└── tasks.md          # Phase 2 — created by /speckit.tasks
```

### Source Code (repository root)

```text
src/se_agent/
├── __init__.py
├── config.py            # Settings.from_env(), dry-mode detection
├── logging.py           # structured logging + secret redaction
├── tools/
│   ├── __init__.py
│   ├── base.py          # Tool ABC, ToolError, ToolResult
│   ├── registry.py      # ToolRegistry
│   ├── msx.py           # MsxTool (flagship) — uses crm client
│   ├── crm.py           # CrmClient interface, HttpCrmClient, FakeCrmClient
│   ├── auth.py          # MSAL token provider interface + fake
│   ├── echo.py          # trivial example tool (extensibility demo)
│   └── notes.py         # simple in-memory scratchpad tool
├── llm/
│   ├── __init__.py
│   ├── base.py          # LLM interface (chat with tool-calling)
│   ├── fake.py          # scripted FakeLLM for tests/dry mode
│   └── openai_llm.py    # optional Azure/OpenAI adapter (lazy import)
├── agent.py             # Agent loop: plan → validate → dispatch → answer
└── cli.py               # argparse CLI entry point

tests/
├── unit/
│   ├── test_registry.py
│   ├── test_tool_validation.py
│   ├── test_msx_tool.py
│   ├── test_crm_client.py
│   └── test_agent_loop.py
└── integration/
    └── test_cli_dry_mode.py

pyproject.toml
README.md
.env.example
.gitignore
```

**Structure Decision**: Single project (CLI + library). The agent core, tools, and LLM
adapters are plain library modules; `cli.py` is the only entry point. This keeps the
deterministic core importable and testable independent of any I/O.

## Architecture & Flow

```text
User prompt ──► cli.py ──► Agent.run()
                              │
                              ▼
                     LLM.plan(prompt, tools)        # FakeLLM in dry mode
                              │  (proposes tool calls)
                              ▼
                  validate args vs Tool.schema       # untrusted input gate
                              │
                              ▼
                  ToolRegistry.dispatch(name, args)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        MsxTool.run()                    EchoTool/NotesTool.run()
              │
              ▼
        CrmClient.query()  ──►  HttpCrmClient → /api/data/v9.2/  (live)
                                FakeCrmClient → canned records     (tests/dry)
              │
              ▼
        ToolResult ──► LLM.finalize() ──► AgentResult ──► stdout
```

## Key Decisions (see research.md)

1. **Interfaces + fakes over mocks**: `LLM`, `CrmClient`, and `TokenProvider` are small
   ABCs. Tests inject fakes; no patching of network libraries.
2. **Lazy optional deps**: `msal`, `httpx`, and the OpenAI SDK are imported only when the
   live adapters are used, so the package installs and tests run with stdlib only.
3. **Dry mode by default when unconfigured**: if required env vars are missing, the agent
   selects `FakeLLM` + reports `msx` as unavailable rather than failing.
4. **CRM safety mirrors MSX Helper**: enforce `/api/data/v9.2/` prefix, length caps, and
   `Prefer: odata.include-annotations="*"`; raw bodies only on `$batch` POST.
5. **MCP-compatible later**: the `Tool` schema shape (name/description/inputSchema) matches
   MCP tool descriptors, so exposing SE-Agent as an MCP server (pluggable into MSX Helper)
   is a thin future adapter, not a core change.

## Phase 0 — Research

Captured in [research.md](./research.md): findings from inspecting `MSX Helper.app`
(Dynamics CRM Web API usage, headers, transports, MCP manager) and the resulting design
decisions and alternatives considered.

## Phase 1 — Design Artifacts

- [data-model.md](./data-model.md) — Tool, Opportunity, Account, Activity, AgentResult.
- [contracts/tool-interface.md](./contracts/tool-interface.md) — the Tool ABC contract.
- [contracts/msx-tool.md](./contracts/msx-tool.md) — `msx` tool operations and schemas.
- [quickstart.md](./quickstart.md) — install, dry-run, and live-config instructions.

## Phase 2 — Tasks

Generated by `/speckit.tasks` into [tasks.md](./tasks.md).
