# Phase 0 — Research: MSX Helper & Design Decisions

## What MSX Helper does (inspected from `/Applications/MSX Helper.app`)

The MSX Helper is an Electron app (`com.msx-helper.app`, "Dynamics CRM automation helper")
whose extracted source reveals:

- **Auth**: Microsoft Entra ID via MSAL (SSO / loopback redirect). Tokens are acquired
  silently when possible and cached in memory.
- **CRM access**: a `crm` service builds requests against the Dynamics CRM Web API. Paths
  are normalized to the `/api/data/v9.2/` prefix; requests send
  `Prefer: odata.include-annotations="*"`.
- **Methods**: GET/POST/PATCH/DELETE plus OData `$batch` POST. Raw request bodies are only
  permitted on `$batch` POST; otherwise structured payloads are required.
- **Safety**: path-prefix validation, query-length and body-length caps before sending.
- **MCP**: it also ships an MCP manager (`mcpManager.js`) supporting `stdio` and
  `streamable-http` transports, i.e. it can host/connect MCP tool servers.

## Decisions

| # | Decision | Rationale | Alternatives rejected |
|---|----------|-----------|-----------------------|
| D1 | Model the `msx` tool as a Dynamics CRM Web API client (v9.2) | Faithfully mirrors MSX Helper; CRM Web API is stable and documented | Reverse-engineering MSX Helper's private IPC/local port — brittle, undocumented |
| D2 | Hide LLM, CRM, and token providers behind small ABCs with fakes | Deterministic, network-free tests per the constitution | Mocking `httpx`/`msal` directly — couples tests to library internals |
| D3 | Make `msal`/`httpx`/OpenAI SDK lazy optional deps | Package installs and tests run with stdlib only; secrets-free CI | Hard dependencies — would force network libs and break dry mode |
| D4 | Default to dry mode when env is unconfigured | Smooth onboarding; honors offline principle | Failing fast on missing creds — poor DX, blocks demos |
| D5 | Shape Tool descriptors like MCP (name/description/inputSchema) | Lets SE-Agent later be exposed as an MCP server plugged into MSX Helper | Bespoke descriptor format — future rework |
| D6 | Read-only CRM scenarios in v1 | Lowest-risk, highest-value SE use case (pipeline questions) | Read+write — larger surface, auth scope, and safety burden |

## Open questions (deferred, non-blocking)

- Exact Entra app registration / scopes for live CRM access are environment-specific and
  supplied at runtime; not needed for the deterministic core or tests.
- Whether to expose SE-Agent as an MCP `streamable-http` server is a future enhancement
  (the tool descriptor shape already anticipates it).
