# Teams Adaptive Card samples

Cards the Chief of Staff orchestrator posts to Teams. They use Adaptive Card **templating**
(`${...}` bindings), so you bind a data object at send time.

| File | Purpose |
|------|---------|
| [morning-brief.card.json](./morning-brief.card.json) | The 7:30 AM brief: meetings, decisions (with Approve/Edit/Skip), handled, deadlines, pipeline |
| [morning-brief.data.json](./morning-brief.data.json) | Example data binding for the brief card |
| [approval.card.json](./approval.card.json) | A single APPROVE-FIRST card (customer reply, MSX commit, manager message) |

## Preview

Paste a card + its data into the [Adaptive Cards Designer](https://adaptivecards.io/designer/)
to preview. For the brief, load `morning-brief.card.json` as the card and
`morning-brief.data.json` as the sample data.

## How the buttons drive actions

Each `Action.Submit` sends a `data` object back to the orchestrator:

- **Approve** → `{ "decision": "approve", "action_id": ..., "draft_id": ... }`
  - If `draft_id` is present (an MSX write), the orchestrator calls the connector's
    `CommitDraft` action with the `x-approval-token` (APPROVE-FIRST). The worker applies the
    CRM write-back.
  - If it's an outbound message, the orchestrator sends the staged email/Teams reply.
- **Edit** → reopens the draft for changes, then re-posts the approval card.
- **Skip** → discards the staged action and logs it.

## Populating the brief from worker data

Use the helper [`se_agent.worker.brief.build_brief_data`](../../src/se_agent/worker/brief.py)
to turn the worker's `/msx/query` output into the card's data binding:

```python
from se_agent.worker.brief import build_brief_data

data = build_brief_data(
    user="Amira",
    date="Thursday, June 18",
    meetings=[{"time": "10:00", "customer": "Contoso", "kind": "ADS", "status": "brief ready ✅"}],
    decisions=[{"summary": "Commit Fabrikam milestone", "action_id": "act-1", "draft_id": "draft-abc"}],
    handled=["Built Contoso brief", "Archived 11 FYIs"],
    deadlines=[{"item": "AZ-204 M4", "due": "Fri", "blocked": "15:00–16:00"}],
    pipeline_query=worker_open_opportunities_result,  # the `data` from /msx/query
)
# Bind `data` to morning-brief.card.json when posting to Teams.
```
