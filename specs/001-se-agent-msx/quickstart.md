# Quickstart — SE-Agent

## Prerequisites

- Python 3.11+

## Install (editable)

```bash
cd /Users/Amira/Desktop/SE-Agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # dev extras = pytest
```

The base install uses only the Python standard library. Live LLM/CRM access pulls in
optional extras:

```bash
pip install -e ".[live]"     # msal, httpx, openai
```

## Run in dry mode (no secrets, no network)

```bash
se-agent "What open opportunities do we have for Contoso?"
# or
python -m se_agent.cli "List my tools"
```

In dry mode the agent uses a scripted FakeLLM and a FakeCrmClient seeded with sample
records, so you can see the full plan → validate → dispatch → answer flow offline.

JSON output for scripting:

```bash
se-agent --json "Summarize Contoso pipeline"
```

## Run live (against real MSX / Dynamics CRM + a model)

Set environment variables (never commit these):

```bash
export SEAGENT_CRM_URL="https://<org>.crm.dynamics.com"
export SEAGENT_ENTRA_TENANT_ID="<tenant-guid>"
export SEAGENT_ENTRA_CLIENT_ID="<app-client-id>"
# one of: client secret (app-only) or interactive/device-code (delegated)
export SEAGENT_ENTRA_CLIENT_SECRET="<secret>"   # optional

export SEAGENT_LLM_PROVIDER="azure-openai"       # or "openai"
export SEAGENT_LLM_ENDPOINT="https://<resource>.openai.azure.com"
export SEAGENT_LLM_API_KEY="<key>"
export SEAGENT_LLM_DEPLOYMENT="<deployment-or-model>"
```

Copy `.env.example` to `.env` for local development; `.env` is git-ignored.

## Test

```bash
pytest -q
```

All tests run with zero network access and no credentials.
