# Tasks: SE-Agent — Solution Engineer Agent with Pluggable Tools (incl. MSX)

**Feature**: `001-se-agent-msx` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tasks are grouped by user story (from spec.md). `[P]` = parallelizable (independent files).

## Phase 0 — Project setup

- [X] T001 Create `pyproject.toml` (package `se-agent`, console script `se-agent`,
  optional extras `dev` and `live`).
- [X] T002 Create `.gitignore` (`.venv`, `__pycache__`, `.env`, build artifacts) and
  `.env.example` documenting all `SEAGENT_*` variables.
- [X] T003 Create `src/se_agent/__init__.py` and package skeleton dirs (`tools/`, `llm/`).

## Phase 1 — Foundational core (blocks all stories)

- [X] T004 `src/se_agent/logging.py`: structured logger + secret-redaction helper.
- [X] T005 `src/se_agent/config.py`: `Settings.from_env()`, dry-mode detection.
- [X] T006 [P] `src/se_agent/tools/base.py`: `Tool` ABC, `ToolResult`, `ToolError`.
- [X] T007 [P] `src/se_agent/tools/registry.py`: `ToolRegistry` (register/get/list).
- [X] T008 [P] `src/se_agent/llm/base.py`: `LLM` interface (plan + finalize) and
  data types for proposed tool calls.
- [X] T009 Minimal JSON-Schema validator for tool args (stdlib only) in `tools/base.py`.

## Phase 2 — User Story 1: Pipeline questions via MSX (P1) 🎯 MVP

- [X] T010 [P] `src/se_agent/tools/auth.py`: `TokenProvider` interface + `FakeTokenProvider`
  + lazy MSAL-backed provider.
- [X] T011 [P] `src/se_agent/tools/crm.py`: `CrmClient` interface, `FakeCrmClient`
  (seeded sample data), lazy `HttpCrmClient` (enforces `/api/data/v9.2/` prefix, length
  caps, `Prefer` header).
- [X] T012 `src/se_agent/tools/msx.py`: `MsxTool` implementing the msx contract
  (open_opportunities / accounts / contacts / recent_activities + account filter).
- [X] T013 `src/se_agent/llm/fake.py`: `FakeLLM` that, for pipeline prompts, proposes an
  `msx` call then composes a summary answer (enables deterministic US1 test).
- [X] T014 `src/se_agent/agent.py`: `Agent.run()` — plan → schema-validate → dispatch →
  finalize; builds `AgentResult` with tool trace.
- [X] T015 `tests/unit/test_msx_tool.py`: open opportunities (incl. total) + empty case.
- [X] T016 `tests/unit/test_agent_loop.py`: US1 pipeline scenario end-to-end with fakes.

## Phase 3 — User Story 2: Dry mode with no credentials (P1)

- [X] T017 `src/se_agent/cli.py`: argparse CLI (`prompt`, `--json`), wires Settings →
  Agent, selects FakeLLM + FakeCrmClient when unconfigured.
- [X] T018 `MsxTool.available()` returns False without CRM config; agent reports MSX
  unavailable but stays usable (in `agent.py`/`msx.py`).
- [X] T019 `tests/integration/test_cli_dry_mode.py`: run CLI with empty env; assert
  graceful output and zero network (fakes only).

## Phase 4 — User Story 3: Extensibility (P2)

- [X] T020 [P] `src/se_agent/tools/echo.py`: trivial `EchoTool` (extensibility demo).
- [X] T021 [P] `src/se_agent/tools/notes.py`: in-memory `NotesTool`.
- [X] T022 `tests/unit/test_registry.py` + `tests/unit/test_tool_validation.py`:
  registration discovery, unknown-tool error, schema-validation rejection.

## Phase 5 — Polish

- [X] T023 `README.md`: overview, architecture diagram, quickstart, MSX explanation.
- [X] T024 Wire optional `openai_llm.py` adapter (lazy) for live runs.
- [X] T025 Run `pytest -q`; ensure green with no network/secrets.

## Dependencies

- Phase 1 blocks Phases 2–4.
- US1 (Phase 2) is the MVP and is independently testable.
- US2 (Phase 3) depends on the CLI but is otherwise independent of US3.
- US3 (Phase 4) is independent of US1/US2 beyond the shared core.
