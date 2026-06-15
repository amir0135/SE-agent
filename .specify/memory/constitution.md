# SE-Agent Constitution

## Core Principles

### I. Tool-First Architecture
Every external capability the agent gains is expressed as a discrete, self-contained Tool.
A Tool declares a stable name, a human-readable description, a JSON input schema, and a
single `run()` entry point. Tools must be independently testable without the agent loop,
must not depend on each other, and must fail loudly with structured errors rather than
silently returning partial data. New capabilities are added by registering a new Tool —
never by special-casing logic inside the agent loop.

### II. MSX Is a First-Class Tool
Access to Microsoft Sales Experience / Dynamics CRM data is provided exclusively through
the `msx` Tool. The `msx` Tool mirrors the behavior of the MSX Helper desktop app: it
authenticates with Microsoft Entra ID (MSAL) and talks to the Dynamics CRM Web API at
`/api/data/v9.2/` using `Prefer: odata.include-annotations="*"`. No other component may
reach into CRM directly; all CRM reads/writes flow through this Tool so auth, throttling,
and auditing live in one place.

### III. Deterministic Core, Probabilistic Edge
The agent loop, tool dispatch, schema validation, and CRM client are deterministic and
fully unit-testable with no network or model calls. Only the planning/return step may
invoke a language model. Any non-deterministic dependency (LLM, network, CRM) must sit
behind an interface that can be replaced with a fake in tests.

### IV. Secrets Never Touch the Repo
Credentials, tokens, tenant IDs, and CRM URLs are read from the environment (or an OS
keychain), never hard-coded and never committed. The agent must run in a "dry/offline"
mode that performs no authentication and no network I/O, so the full pipeline can be
exercised without secrets.

### V. Observability & Text I/O
Every tool invocation logs its name, redacted arguments, latency, and outcome via
structured logging. The agent exposes a text-in / text-out CLI: a prompt on stdin/args,
the answer on stdout, diagnostics on stderr. Output supports both human-readable and
JSON formats so the agent is scriptable and debuggable.

## Security Requirements

- Authenticate to Dynamics CRM with MSAL using delegated or app-only flows; tokens are
  cached in memory only and refreshed on expiry.
- Validate and constrain every CRM request: enforce the `/api/data/v9.2/` path prefix,
  cap query and body length, and only allow raw bodies on `$batch` POST requests.
- Treat all model output as untrusted: tool arguments produced by the LLM are validated
  against each Tool's JSON schema before execution.
- No tool may execute shell commands or arbitrary code derived from model output.

## Development Workflow

- Spec-Driven Development: every feature begins with a spec, then a plan, then tasks,
  then implementation. Code that has no corresponding spec/plan entry is out of scope.
- Tests accompany every Tool and the agent loop; the deterministic core must stay green
  without network access.
- Reviews verify: (a) new capability is a Tool, (b) no secrets in code, (c) schema
  validation present, (d) offline/dry mode still works.

## Governance

This Constitution supersedes other practices for the SE-Agent project. Amendments require
updating this document and the dependent spec/plan/tasks artifacts. Complexity must be
justified against the principles above; prefer adding a Tool over expanding the core.

**Version**: 1.0.0 | **Ratified**: 2026-06-14 | **Last Amended**: 2026-06-14
