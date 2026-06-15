# Cloud MSX Worker

The hosted replacement for the local **MSX Helper** app. It exposes the `se_agent` `msx`
tool over HTTPS so a cloud-hosted orchestrator (Copilot Studio / Foundry) can reach it
without any `localhost` dependency. Same MSAL → Dynamics CRM (`/api/data/v9.2/`) behavior,
draft-only writes, approval-gated commits.

See [specs/002-chief-of-staff/cloud-deployment.md](../specs/002-chief-of-staff/cloud-deployment.md)
for the full architecture.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthz` | Liveness + MSX availability |
| GET | `/msx/tools` | MCP-compatible tool descriptor |
| POST | `/msx/query` | Reads: open_opportunities, accounts, contacts, recent_activities |
| POST | `/msx/draft` | Stage a draft write → returns `draft_id` |
| POST | `/msx/commit` | Commit a draft — requires `x-approval-token` header (APPROVE-FIRST) |

## Run locally (dry mode — no secrets, no network)

```bash
pip install -e ".[worker]"
export SEAGENT_DRY_RUN=1 SEAGENT_APPROVAL_TOKEN=demo
uvicorn se_agent.worker.app:app --port 8000

curl localhost:8000/healthz
curl -X POST localhost:8000/msx/query -H 'content-type: application/json' \
  -d '{"operation":"open_opportunities","account_name":"Contoso"}'
```

## Run live (real CRM)

Set the same env vars MSX Helper uses, then start the worker:

```bash
export SEAGENT_DRY_RUN=
export SEAGENT_CRM_URL="https://<org>.crm.dynamics.com"
export SEAGENT_ENTRA_TENANT_ID=... SEAGENT_ENTRA_CLIENT_ID=... SEAGENT_ENTRA_CLIENT_SECRET=...
export SEAGENT_APPROVAL_TOKEN="$(openssl rand -hex 24)"
uvicorn se_agent.worker.app:app --port 8000
```

## Deploy to Azure (azd)

From the repo root:

```bash
azd auth login
azd up        # builds the Docker image, provisions infra, deploys the Container App
```

`azd up` provisions: Container Apps env + the worker (scale-to-zero), ACR, a User-Assigned
Managed Identity (AcrPull + Key Vault Secrets User), Key Vault (approval token + optional
client secret), and Log Analytics / App Insights. On completion it prints `MSX_WORKER_URL`
— wire that into Copilot Studio as the Pipeline/MSX tool.

By default it deploys in **dry mode** (`dryRun=true`, sample data). To go live, set the
`SEAGENT_*` env vars in your azd environment (`azd env set ...`) and `dryRun=false`.

## Tests

```bash
pytest -q tests/integration/test_worker_api.py
```

Runs in dry mode; no network or secrets required.
