# Feature Specification: SE-Agent — Solution Engineer Agent with Pluggable Tools (incl. MSX)

**Feature Branch**: `001-se-agent-msx`
**Created**: 2026-06-14
**Status**: Draft
**Input**: User description: "Solution Engineer agent with pluggable tools including an MSX Dynamics CRM tool"

## Overview

SE-Agent is an AI assistant for Solution / Sales Engineers. It answers natural-language
questions and performs tasks by reasoning over a registry of **Tools**. The flagship Tool
is **MSX** — it reads Microsoft Sales Experience / Dynamics CRM data (opportunities,
accounts, contacts, recent activities) exactly the way the MSX Helper desktop app does:
via Microsoft Entra (MSAL) auth and the Dynamics CRM Web API (`/api/data/v9.2/`). The
agent is extensible: new abilities are added by registering additional Tools, not by
changing the agent core.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask about a customer's pipeline using MSX (Priority: P1)

A Solution Engineer asks, in plain language, "What are my open opportunities for Contoso,
and what's the total pipeline value?" SE-Agent recognizes it needs CRM data, calls the
MSX Tool to query open opportunities for the account, and returns a concise summary with
names, stages, estimated values, and the total.

**Why this priority**: This is the core reason the agent exists — turning CRM data into
fast answers — and it directly exercises the MSX Tool, the required integration.

**Independent Test**: With the MSX Tool backed by a fake CRM client returning canned
opportunity records, ask the pipeline question and assert the agent's answer lists the
opportunities and the correct total. No network or real credentials required.

**Acceptance Scenarios**:

1. **Given** the MSX Tool is configured and three open opportunities exist for an account,
   **When** the user asks for that account's open pipeline, **Then** the agent returns all
   three with their estimated values and a correct summed total.
2. **Given** an account has no open opportunities, **When** the user asks for its pipeline,
   **Then** the agent clearly states there are none rather than erroring.

---

### User Story 2 - Run with no credentials in dry mode (Priority: P1)

A developer or evaluator runs SE-Agent without any CRM credentials configured to explore
its behavior. The agent starts, lists its tools, and either answers from non-CRM tools or
clearly reports that MSX is unavailable because no credentials are configured — without
crashing and without attempting any network calls.

**Why this priority**: The constitution mandates a secrets-free, offline/dry mode so the
full pipeline is testable and demoable. It de-risks onboarding and CI.

**Independent Test**: Launch the agent with no environment variables set, invoke the CLI
with a prompt, and assert it returns a graceful, structured response and makes zero
network calls.

**Acceptance Scenarios**:

1. **Given** no CRM credentials are set, **When** the agent starts, **Then** it loads and
   reports MSX as "unavailable (no credentials)" while remaining usable.
2. **Given** dry mode, **When** any tool would perform network I/O, **Then** no network
   request is made.

---

### User Story 3 - Extend the agent with a new Tool (Priority: P2)

A developer adds a new capability (e.g., a notes/scratchpad tool, or a web-fetch tool) by
implementing the Tool interface and registering it. The agent picks it up automatically;
no changes to the agent loop are required.

**Why this priority**: Extensibility via tools is a constitutional principle and the
primary maintenance pathway, but it is not required for the first end-to-end demo.

**Independent Test**: Register a trivial echo Tool in a test, run the agent, and assert
the tool appears in the registry and can be invoked through the normal dispatch path.

**Acceptance Scenarios**:

1. **Given** a new Tool class is registered, **When** the agent lists tools, **Then** the
   new tool appears with its name, description, and input schema.
2. **Given** the LLM selects the new tool with valid arguments, **When** the agent
   dispatches it, **Then** the tool runs and its result is incorporated into the answer.

---

### Edge Cases

- The LLM requests a tool that does not exist → the agent returns a structured "unknown
  tool" error and continues rather than crashing.
- The LLM supplies arguments that violate a tool's input schema → arguments are rejected
  before execution and the agent reports a validation error.
- The CRM Web API returns 401/403 (expired or insufficient token) → the MSX Tool surfaces
  a clear auth error and the agent does not leak token values.
- The CRM Web API is unreachable or times out → the tool returns a structured transport
  error; the agent degrades gracefully.
- A CRM query would exceed configured query/body length limits → the request is rejected
  locally before being sent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a Tool registry where each Tool provides a unique name,
  a description, a JSON input schema, and a single execution entry point.
- **FR-002**: System MUST provide an `msx` Tool that authenticates via MSAL and queries
  the Dynamics CRM Web API at the `/api/data/v9.2/` path prefix with the header
  `Prefer: odata.include-annotations="*"`.
- **FR-003**: The `msx` Tool MUST support, at minimum, retrieving open opportunities,
  accounts, contacts, and recent activities, with optional filtering by account name.
- **FR-004**: System MUST validate every tool's arguments against that tool's JSON schema
  before execution and reject invalid arguments with a structured error.
- **FR-005**: System MUST run in a dry/offline mode that performs no authentication and no
  network I/O, enabling full pipeline testing without secrets.
- **FR-006**: System MUST read all credentials, tenant/CRM URLs, and model configuration
  from environment variables (or an OS keychain); none may be hard-coded.
- **FR-007**: System MUST enforce CRM request safety: path-prefix restriction, query- and
  body-length caps, and raw bodies only on `$batch` POST requests.
- **FR-008**: System MUST provide a text-in/text-out CLI that accepts a prompt and prints
  the answer, supporting both human-readable and JSON output.
- **FR-009**: System MUST log every tool invocation with tool name, redacted arguments,
  latency, and outcome.
- **FR-010**: System MUST treat all model output as untrusted and MUST NOT execute shell
  commands or arbitrary code derived from model output.
- **FR-011**: The agent loop, dispatch, schema validation, and CRM client MUST be unit
  testable with the LLM and CRM dependencies replaced by fakes.

### Key Entities

- **Tool**: A named capability with a description, JSON input schema, and a `run(args)`
  method returning a structured result.
- **ToolRegistry**: The collection of available Tools, queryable by name and enumerable
  for presentation to the model.
- **Opportunity**: A CRM sales opportunity — name, account, stage, estimated value, close
  date, status (open/won/lost).
- **Account**: A CRM customer organization — name, identifier, owner.
- **Activity**: A recent CRM interaction (email, call, appointment, task) tied to an
  account or opportunity.
- **AgentResult**: The agent's final structured response — answer text plus the trace of
  tools invoked.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Solution Engineer can get a correct open-pipeline summary for a named
  account in a single natural-language prompt.
- **SC-002**: The full agent pipeline runs and passes its test suite with zero network
  access and no credentials configured.
- **SC-003**: A new Tool can be added and made available to the agent by implementing the
  Tool interface and registering it, with no edits to the agent loop.
- **SC-004**: 100% of tool invocations produced by the model are schema-validated before
  execution; invalid invocations never reach a tool's `run()`.
- **SC-005**: No secret value (token, client secret, credential) ever appears in logs,
  source, or committed files.

## Assumptions

- The MSX Tool targets the Dynamics CRM Web API v9.2, matching the MSX Helper app; the
  CRM org URL and Entra app registration are provided via environment when running live.
- A language model endpoint (Azure OpenAI or OpenAI-compatible) is available via
  environment configuration for live runs; in tests it is replaced by a fake.
- Initial scope is read-focused CRM scenarios (querying pipeline/accounts/activities);
  write-back to CRM is out of scope for v1.
- Single-user, local CLI usage for v1; multi-user hosting and a web UI are out of scope.
- Python is the implementation language (consistent with the spec-kit Python toolchain).
