# SE-Agent

A **Solution Engineer agent** with a pluggable tool system. Its flagship tool, **MSX**,
reads Microsoft Sales Experience / Dynamics CRM data (open opportunities, accounts,
contacts, recent activities) the same way the **MSX Helper** desktop app does — via
Microsoft Entra (MSAL) auth and the Dynamics CRM Web API (`/api/data/v9.2/`).

Built with [GitHub Spec Kit](https://github.com/github/spec-kit) using Spec-Driven
Development. The full spec, plan, and tasks live in
[`specs/001-se-agent-msx/`](specs/001-se-agent-msx/).

## Why it's built this way

The project follows a small [constitution](.specify/memory/constitution.md):

1. **Tool-First** — every capability is a self-contained `Tool` (name, description, JSON
   schema, `run()`); new abilities are added by registering a tool, not by editing the
   agent loop.
2. **MSX is a first-class tool** — all CRM access flows through the `msx` tool.
3. **Deterministic core, probabilistic edge** — the loop, dispatch, schema validation, and
   CRM client are fully testable with fake LLM/CRM; only the planning step calls a model.
4. **Secrets never touch the repo** — all config from the environment; a dry/offline mode
   runs the whole pipeline with no secrets and no network.
5. **Observability & text I/O** — structured, secret-redacting logs; text-in/text-out CLI.

## Architecture

```text
prompt ──► cli.py ──► Agent.run()
                        │
                        ▼
               LLM.plan(prompt, tools)        FakeLLM (dry) | OpenAILLM (live)
                        │  proposes tool calls
                        ▼
            validate args vs Tool.input_schema   ← untrusted-input gate
                        │
                        ▼
              ToolRegistry.dispatch(name, args)
              ┌──────────┴──────────┐
              ▼                     ▼
          MsxTool.run()        EchoTool / NotesTool
              │
              ▼
          CrmClient            HttpCrmClient → /api/data/v9.2/  (live)
                               FakeCrmClient → sample records    (dry/tests)
              │
              ▼
          ToolResult ──► LLM.finalize() ──► answer ──► stdout
```

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Dry mode — no secrets, no network, uses sample CRM data:
python -m se_agent.cli "What are my open opportunities for Contoso and the total pipeline?"

# JSON output and tool listing:
python -m se_agent.cli --json "Summarize Contoso pipeline"
python -m se_agent.cli --list-tools
```

Example dry-mode output:

```text
Found 3 open opportunit(ies):
  • Contoso Cloud Migration — Propose — $250,000 (close 2026-09-30)
  • Contoso Security Uplift — Develop — $120,000 (close 2026-08-15)
  • Contoso Data Platform — Qualify — $90,000 (close 2026-11-01)
Total pipeline: $460,000
```

## Live mode (real MSX / Dynamics CRM + a model)

Install the live extra and configure the environment (see
[`.env.example`](.env.example)):

```bash
pip install -e ".[live]"
export SEAGENT_CRM_URL="https://<org>.crm.dynamics.com"
export SEAGENT_ENTRA_TENANT_ID=... SEAGENT_ENTRA_CLIENT_ID=... SEAGENT_ENTRA_CLIENT_SECRET=...
export SEAGENT_LLM_PROVIDER=azure-openai SEAGENT_LLM_API_KEY=... SEAGENT_LLM_DEPLOYMENT=gpt-4o
export SEAGENT_LLM_ENDPOINT="https://<resource>.openai.azure.com"
```

The `msx` tool mirrors MSX Helper: it enforces the `/api/data/v9.2/` path prefix, sends
`Prefer: odata.include-annotations="*"`, and caps query/body length. Tokens are acquired
via MSAL and never logged.

## Extending the agent

Add a new capability by implementing `Tool` and registering it — no agent-loop changes:

```python
from se_agent.tools.base import Tool, ToolResult

class WeatherTool(Tool):
    name = "weather"
    description = "Get the weather for a city."
    input_schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    }
    def run(self, args):
        return ToolResult.success({"city": args["city"], "forecast": "sunny"})
```

The `Tool.descriptor()` shape (`name` / `description` / `inputSchema`) is MCP-compatible,
so SE-Agent can later be exposed as an MCP server and plugged into MSX Helper's MCP
manager.

## Tests

```bash
pytest -q
```

All tests run with zero network access and no credentials.

## Project layout

```text
src/se_agent/        agent core, tools, LLM adapters, CLI
src/se_agent/worker/ Cloud MSX Worker (FastAPI) — hosted replacement for MSX Helper
tests/               unit + integration tests (network-free)
infra/               Bicep for azd (Container App, Key Vault, Managed Identity, logs)
azure.yaml           azd service definition
specs/001-se-agent-msx/    spec, plan, research, data-model, contracts, tasks
specs/002-chief-of-staff/  orchestrator prompt, architecture, build doc, cloud deployment
.specify/            spec-kit scaffolding + constitution
```

## Cloud MSX Worker

To run fully cloud-hosted (no `localhost` MSX Helper dependency), the `se_agent` `msx` tool
is exposed as a hosted HTTPS service in [src/se_agent/worker](src/se_agent/worker/README.md)
and deployed with `azd up`. A cloud orchestrator (Copilot Studio / Foundry) calls it as the
Pipeline/MSX tool. See [specs/002-chief-of-staff/cloud-deployment.md](specs/002-chief-of-staff/cloud-deployment.md).
