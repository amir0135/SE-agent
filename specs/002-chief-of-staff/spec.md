# Feature Specification: Chief of Staff Orchestrator

**Feature Branch**: `002-chief-of-staff`
**Created**: 2026-06-14
**Status**: Draft
**Input**: An autonomous "brain" agent that reads Outlook/Calendar/Teams (and MSX),
decides what matters, delegates to worker agents, and reports to the user via a brief +
approval taps.

## Overview

The Chief of Staff is the **orchestrator** layer above the worker agents. It runs a
continuous **perceive → decide → delegate → report** loop and is the only agent the user
interacts with. Its **Pipeline/MSX** worker connects to the **MSX Helper application** you
already have (an MCP server over Dynamics CRM); the heavier workers (Account Intelligence,
Demo Builder, Envisioning Prep, Compete) are called as tools and are to-be-built.

The deliverable for this feature is the **orchestrator system prompt**
([orchestrator-prompt.md](./orchestrator-prompt.md)) — paste-ready for Copilot Studio —
plus the trigger/approval design below.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Morning brief drives the day (Priority: P1)

At 7:30 AM the orchestrator has already swept Outlook, Calendar, Teams, and MSX, decided
what matters, prepped briefs, drafted replies, and blocked time. The user reads one brief
and acts only on the "decisions needed" items.

**Acceptance Scenarios**:

1. **Given** a customer TDM emailed asking for an AI Foundry POC overnight, **When** the
   brief is generated, **Then** it is classified P1/TECHNICAL_WIN, Demo Builder +
   Envisioning Prep were fired, and a drafted reply is staged for approval.
2. **Given** a newsletter arrived, **When** the brief is generated, **Then** it is treated
   as NOISE and not surfaced as an action.

### User Story 2 - Approval guardrails hold (Priority: P1)

Nothing customer-facing, MSX-committed, or manager-facing goes out without an explicit
Approve. Research, briefs, calendar blocks, and MSX *drafts* happen automatically.

**Acceptance Scenarios**:

1. **Given** a drafted customer reply, **When** the orchestrator finishes, **Then** the
   reply is staged (not sent) and waits for Approve / Edit / Skip.
2. **Given** a stale MSX milestone, **When** the orchestrator updates it, **Then** the
   update is a draft until the user approves the commit.

### User Story 3 - Meeting prep arrives ahead of time (Priority: P2)

A new customer meeting on the calendar triggers Account Intelligence to deliver a 1-page
brief 24h before the meeting.

### Edge Cases

- A source (Teams/MSX) is unavailable → orchestrator reports the gap and proceeds.
- A worker returns empty/low-confidence → orchestrator says so; never fabricates.
- A signal is ambiguous (low confidence) → orchestrator drafts and asks rather than acting.

## Requirements *(mandatory)*

- **FR-001**: MUST perceive signals from Outlook, Calendar, and Teams; MSX optional.
- **FR-002**: MUST classify every signal via the priority rubric (customer win > pod/manager
  > compliance > hygiene > noise) with priority, urgency, and confidence.
- **FR-003**: MUST select worker agents itself and run them in parallel when needed, then
  stitch outputs into one staged deliverable.
- **FR-004**: MUST surface output as a 7:30 AM brief, quiet decision pings, and a 5 PM
  wrap-up — and nothing else.
- **FR-005**: MUST enforce APPROVE-FIRST for customer/manager/leadership messages and
  committed MSX writes; MUST allow AUTO for research, briefs, calendar blocks, drafts, and
  archiving.
- **FR-006**: MUST use the **MSX Helper application** (via its MCP `streamable-http`
  endpoint on localhost) as the Pipeline/MSX worker for CRM reads and draft updates; the
  repo's `se_agent` `msx` tool is the offline/dev stand-in for the same contract.
- **FR-007**: MUST never fabricate customer data, numbers, or commitments, and MUST redact
  secrets/private content in summaries.

## Success Criteria *(mandatory)*

- **SC-001**: On a normal day the user touches only the brief, approval taps, and wrap-up.
- **SC-002**: 100% of customer/manager-facing or MSX-committed actions pass through an
  explicit approval.
- **SC-003**: No P1 customer/technical-win signal is ever filed as noise.
- **SC-004**: Meeting briefs arrive ≥ 24h before customer meetings.

## What exists today vs. what to build

- **Exists:** the **MSX Helper application** (`/Applications/MSX Helper.app`) — an Electron
  app that authenticates with Entra (MSAL), talks to the Dynamics CRM Web API
  (`/api/data/v9.2/`), and exposes an **MCP server** (MCP manager with `stdio` +
  `streamable-http` transports, local HTTP server). This is the real Pipeline/MSX backend.
- **To build:** the Copilot Studio orchestrator (the brain) and the heavier workers
  (Account Intelligence, Demo Builder, Envisioning Prep, Compete). There is no deployed
  "SE-Agent" — the `se_agent` package in this repo is a local reference implementation that
  mirrors MSX Helper's CRM behavior and can stand in for the worker during development.

## Assumptions

- Built in **Copilot Studio** (native Outlook/Calendar/Teams connectors + event triggers +
  approval cards); heavier workers wired as **Azure AI Foundry** agents called as tools.
- Identity/governance via **Entra Agent ID + Purview/Defender**.
- The **Pipeline/MSX worker connects to the MSX Helper app over MCP** (`streamable-http` on
  localhost) for CRM reads and draft updates; read-only v1, writes staged as drafts. The
  repo's `se_agent` `msx` tool is the offline/dev stand-in for the same contract.
- **Cloud-hosted option:** for production the localhost dependency is removed by deploying a
  **Cloud MSX Worker** (the same `se_agent` `msx` contract hosted on Azure Container Apps,
  MSAL→Dynamics CRM). See [cloud-deployment.md](./cloud-deployment.md). MSX Helper then
  remains a local/dev convenience, not a runtime dependency.
