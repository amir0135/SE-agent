# Cloud MSX Worker — Copilot Studio / Power Platform Connector

One-click import of the Cloud MSX Worker's tools into **Copilot Studio** (or any Power
Platform environment) so the Chief of Staff orchestrator can call them as the
**Pipeline/MSX** tool.

Files:

- [apiDefinition.swagger.json](./apiDefinition.swagger.json) — OpenAPI 2.0 (Swagger) for the
  worker's endpoints (`QueryMsx`, `StageDraft`, `CommitDraft`, plus health/descriptor).
- [apiProperties.json](./apiProperties.json) — connector metadata (brand color, capabilities).

## Actions exposed

| Action | Endpoint | Use in orchestrator |
|--------|----------|---------------------|
| `QueryMsx` | `POST /msx/query` | Read open opportunities, accounts, contacts, recent activities |
| `StageDraft` | `POST /msx/draft` | Stage a milestone/CRM update (AUTO — draft only) |
| `CommitDraft` | `POST /msx/commit` | Commit a draft — **APPROVE-FIRST** (needs `x-approval-token`) |
| `GetToolDescriptor` | `GET /msx/tools` | Discover the MSX tool schema |
| `HealthCheck` | `GET /healthz` | Liveness |

## Before importing

1. Deploy the worker (`azd up`) and copy the `MSX_WORKER_URL` output, e.g.
   `https://seagent-msx-worker.<region>.azurecontainerapps.io`.
2. In [apiDefinition.swagger.json](./apiDefinition.swagger.json), set `host` to that domain
   (no scheme, no trailing slash), e.g. `seagent-msx-worker.<region>.azurecontainerapps.io`.

## Import options

### A. Copilot Studio (recommended)

1. Open your agent → **Tools** → **Add a tool** → **New tool** → **Custom connector**.
2. Power Apps opens → **Custom connectors** → **New custom connector** → **Import an
   OpenAPI file** → select `apiDefinition.swagger.json`.
3. Review → **Create connector**. Add it back in Copilot Studio as a tool.

### B. Power Platform CLI (paconn)

```bash
pip install paconn
paconn login
paconn create --api-def connector/apiDefinition.swagger.json \
              --api-prop connector/apiProperties.json
```

## Wiring into the orchestrator

- Map the rubric outcomes to actions:
  - Reads (briefs, pipeline risk, manager prep) → `QueryMsx`.
  - Pod/pipeline updates → `StageDraft` (AUTO) → on Approve → `CommitDraft` with the
    `x-approval-token`.
- Keep the approval token out of the connector definition; supply it at call time from the
  approval flow (Key Vault-backed). The worker rejects commits without it.

## Note on auth

This definition gates only **commits** with the `x-approval-token` header (the APPROVE-FIRST
boundary). For network-level protection, also restrict the Container App ingress to the
Copilot Studio / Power Platform egress, or front it with Entra ID (Easy Auth) and add a
matching `securityDefinition`.
