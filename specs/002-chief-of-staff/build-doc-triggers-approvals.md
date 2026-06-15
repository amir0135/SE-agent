# Chief of Staff — Build Doc: Triggers & Approval Flows

A hackathon-ready build guide. It maps the orchestrator design to concrete Copilot Studio
triggers, Azure AI Foundry worker tools, the approval (human-in-the-loop) flows, and the
governance wiring. Pair this with [orchestrator-prompt.md](./orchestrator-prompt.md) (the
brain) and [architecture.md](./architecture.md) (the picture).

## 0. Components & where they live

| Component | Platform | Role | Status |
|-----------|----------|------|--------|
| Chief of Staff orchestrator | **Copilot Studio** (custom agent) | Brain: triggers, decide, delegate, report, approvals | To build |
| Account Intelligence, Demo Builder, Envisioning Prep, Compete | **Azure AI Foundry** agents | Heavy workers, called as tools | To build |
| **MSX Helper application** | **Existing desktop app** (`/Applications/MSX Helper.app`) | Real Pipeline/MSX backend — Dynamics CRM via Entra/MSAL, exposes an **MCP server** (`stdio` + `streamable-http`, local HTTP) | **Exists ✅** |
| `se_agent` `msx` tool | This repo (Python) | Offline/dev stand-in mirroring MSX Helper's CRM contract | Exists (dev only) |
| Identity | **Entra Agent ID** | Agent identity, least-privilege scopes | To configure |
| Governance | **Purview + Defender for Cloud Apps** | DLP, audit, data classification | To configure |

> **Grounding:** there is no deployed "SE-Agent." The only real CRM asset is the **MSX
> Helper app**. The orchestrator's Pipeline/MSX worker connects to it over MCP
> (`streamable-http` on `http://localhost:<port>/`); use the repo's `se_agent` `msx` tool
> as the offline stand-in while building, then point the worker at MSX Helper for the demo.

## 1. Triggers (Copilot Studio)

Configure these event triggers on the orchestrator. Each one builds a Signal, runs the
DECIDE rubric, and routes per the prompt.

| # | Trigger | Type | Fires when | First action |
|---|---------|------|-----------|--------------|
| T1 | **New email** | Outlook event (`When a new email arrives`) | Mail lands in Inbox/Focused | Build Signal → classify (skip auto-foldered noise) |
| T2 | **Meeting created/updated** | Calendar event | Event added/changed in next 48h | If customer-facing → MEETING_PREP |
| T3 | **Teams message / @-mention** | Teams event | Pod chat message or @-mention to user | Classify POD_ORCHESTRATION vs noise |
| T4 | **Morning sweep** | Scheduled (07:15) | Daily | Full sweep of all sources → build 07:30 brief |
| T5 | **Midday sweep** | Scheduled (12:30) | Daily | Re-rank; surface new P1s only |
| T6 | **Wrap-up** | Scheduled (17:00) | Daily | Generate end-of-day summary |
| T7 | **Pipeline sweep** | Scheduled (08:00, Mon/Wed/Fri) | MSX connected | Detect UC 14+ days / stale milestones → PIPELINE_RISK |

> Tip: T4–T7 use the **Scheduled trigger**; T1–T3 use **connector event triggers**. Keep a
> short dedupe window so a meeting edit doesn't double-fire MEETING_PREP.

## 2. Topics ↔ decision outcomes

Model each rubric outcome as a Copilot Studio **topic** the orchestrator routes to:

```
Topic: Technical Win        → call Demo Builder + Envisioning Prep (parallel) → stage reply (APPROVE-FIRST)
Topic: Meeting Prep         → call Account Intelligence → deliver brief 24h prior (AUTO)
Topic: Pod Orchestration    → call Pipeline/MSX (milestone) → draft Teams reply (APPROVE-FIRST to send)
Topic: Manager Prep         → call Pipeline/MSX → assemble numbers + talking points
Topic: Compliance Deadline  → create calendar block + reminder (AUTO)
Topic: Pipeline Risk        → call Pipeline/MSX → flag + suggested next action; draft (AUTO), commit (APPROVE-FIRST)
Topic: Noise                → summarize/file/archive (AUTO, silent)
```

## 3. Worker tool contracts (Foundry agents as tools)

Register each worker as a tool/connector on the orchestrator. Suggested I/O:

```yaml
account_intelligence:
  input:  { account_name: string, meeting_id?: string }
  output: { brief_md: string, stakeholders: [], open_opps: [], talking_points: [] }

demo_builder:
  input:  { scenario: string, product: string, customer?: string }
  output: { asset_url: string, summary: string, setup_steps: [] }

envisioning_prep:
  input:  { customer: string, scenario: string }
  output: { outline_md: string, discovery_questions: [], success_metrics: [] }

pipeline_msx:                 # connects to the MSX Helper app over MCP (streamable-http, localhost)
  transport: streamable-http   # MSX Helper MCP server: http://localhost:<port>/
  input:  { operation: enum[open_opportunities, accounts, contacts, recent_activities, draft_milestone_update],
            account_name?: string, opportunity_id?: string, payload?: object }
  output: { data: object, draft?: object }    # writes return a DRAFT, never committed
  dev_fallback: se_agent `msx` tool            # offline stand-in with same contract

compete:
  input:  { competitor: string, product: string }
  output: { battlecard_md: string }
```

The orchestrator **chooses** these — the user never names one. For Technical Win it fans
out to `demo_builder` + `envisioning_prep` and stitches both into one staged deliverable.

### 3.1 Connecting the MSX Helper app (the one thing you already have)

1. Launch **MSX Helper** and open its MCP config (it ships an MCP manager UI). Note the
   local server URL it prints: `Server is now listening on found open port: <port>` →
   `http://localhost:<port>/`.
2. In Copilot Studio (or the Foundry worker), register an **MCP tool / connector** with
   transport `streamable-http` pointing at that URL. MSX Helper handles Entra/MSAL auth and
   the `/api/data/v9.2/` CRM calls for you.
3. Map the `pipeline_msx` operations above to the MCP tools MSX Helper exposes (`tools/list`
   to discover them). Keep writes as **drafts** — gate any commit behind APPROVE-FIRST.
4. For offline dev / CI where the app isn't running, swap in the repo's `se_agent` `msx`
   tool, which implements the same operations against sample data.

## 4. Approval flow (human-in-the-loop)

Use Copilot Studio **Adaptive Card** approvals for every APPROVE-FIRST action.

### 4.1 Gate logic (pseudocode)

```
on action_ready(action):
    if action.kind in {EMAIL_TO_CUSTOMER, MSG_TO_MANAGER, MSG_TO_LEADERSHIP, MSX_COMMIT}:
        post_approval_card(action)          # APPROVE-FIRST
        wait_for: Approve | Edit | Skip
        on Approve: execute(action)
        on Edit:    reopen_draft(action); re-gate
        on Skip:    discard(action); log
    else:
        execute(action)                     # AUTO: research, briefs, blocks, drafts, archive
```

### 4.2 Approval card (schema sketch)

```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    { "type": "TextBlock", "weight": "Bolder", "text": "Approve outbound: Reply to Maersk (customer)" },
    { "type": "TextBlock", "wrap": true, "text": "Drafted answer to their AKS architecture question." },
    { "type": "TextBlock", "isSubtle": true, "wrap": true, "text": "${draft_preview}" }
  ],
  "actions": [
    { "type": "Action.Submit", "title": "Approve", "data": { "decision": "approve", "action_id": "${id}" } },
    { "type": "Action.Submit", "title": "Edit",    "data": { "decision": "edit",    "action_id": "${id}" } },
    { "type": "Action.Submit", "title": "Skip",    "data": { "decision": "skip",    "action_id": "${id}" } }
  ]
}
```

### 4.3 Autonomy matrix (single source of truth)

| Action | Default | Rationale |
|--------|---------|-----------|
| Research / account brief | AUTO | Read-only |
| Calendar focus/compliance block | AUTO | Reversible, personal |
| Draft email/Teams reply | AUTO (draft only) | Not sent |
| MSX draft milestone update | AUTO (draft only) | Not committed |
| Archive/file noise | AUTO | Reversible |
| **Email/message to customer** | **APPROVE-FIRST** | External, reputational |
| **Message to manager/leadership** | **APPROVE-FIRST** | Visibility |
| **Commit to MSX** | **APPROVE-FIRST** | System of record |

## 5. Identity & governance wiring

- **Entra Agent ID**: give the orchestrator its own agent identity. Grant least-privilege
  Graph scopes: `Mail.Read`, `Calendars.ReadWrite` (own calendar), `Chat.Read`,
  `ChannelMessage.Read.All` (as needed). MSX access via the Pipeline/MSX worker's own
  identity (delegated/app-only, read + draft).
- **Approval = the write boundary**: no Graph/MSX *write* scope is exercised without an
  approved card. Drafts use create-draft APIs, not send.
- **Purview**: apply DLP + sensitivity labels so the agent never summarizes or forwards
  classified content beyond policy; redact in briefs.
- **Defender for Cloud Apps**: monitor the agent identity for anomalous activity.
- **Audit**: log every Signal → decision → action → approval outcome for review (also your
  AI-security scorecard story).

## 6. Hackathon build order (½–1 day)

1. **Brain first** — create the Copilot Studio agent, paste
   [orchestrator-prompt.md](./orchestrator-prompt.md) into Instructions.
2. **One trigger** — wire T1 (new email) + T4 (07:30 brief). Demo the loop end-to-end.
3. **One worker** — connect **MSX Helper** over MCP (§3.1) so briefs cite real opps; use
   the `se_agent` `msx` tool as the offline fallback.
4. **One approval** — add the APPROVE-FIRST card for a customer reply.
5. **Two more triggers** — T2 (meeting prep) + T3 (Teams ping).
6. **Govern** — attach Entra Agent ID + a Purview DLP policy; turn on audit.
7. **Demo** — run the morning brief ([brief-template.md](./brief-template.md)); approve one
   reply; show it sent.

## 7. Demo script (2 min)

1. "It's 7:30." Show the brief: 3 meetings, 1 customer POC drafted, AZ-204 blocked, 2 MSX
   updates staged.
2. Tap **Approve** on the Maersk reply → show it sent.
3. Tap **Edit** on an MSX milestone → tweak → **Approve** → committed.
4. New email arrives from a customer TDM (POC ask) → quiet ping with staged deliverable.
5. Newsletter arrives → silently archived, never surfaced. "That's the brain."
