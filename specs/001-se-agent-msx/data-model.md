# Phase 1 — Data Model

## Tool (concept)

| Field | Type | Notes |
|-------|------|-------|
| name | str | Unique registry key (e.g., `msx`, `echo`, `notes`) |
| description | str | Shown to the LLM for selection |
| input_schema | dict (JSON Schema) | Validated against before `run()` |

`run(args: dict) -> ToolResult`

## ToolResult

| Field | Type | Notes |
|-------|------|-------|
| ok | bool | Success flag |
| data | Any (JSON-serializable) | Result payload when `ok` |
| error | str \| None | Structured message when not `ok` |

## ToolError

Raised internally by tools; carries a `code` (e.g., `auth`, `transport`, `validation`,
`not_found`) and a human-readable message. Never includes secret values.

## Opportunity

| Field | Type | Notes |
|-------|------|-------|
| id | str | CRM `opportunityid` |
| name | str | `name` |
| account_name | str | Related account display name |
| stage | str | Sales stage / `salesstage` label |
| estimated_value | float | `estimatedvalue` |
| close_date | str (ISO date) \| None | `estimatedclosedate` |
| status | str | `open` \| `won` \| `lost` (from `statecode`) |

## Account

| Field | Type | Notes |
|-------|------|-------|
| id | str | CRM `accountid` |
| name | str | `name` |
| owner | str \| None | Owning user display name |

## Activity

| Field | Type | Notes |
|-------|------|-------|
| id | str | Activity id |
| type | str | email \| phonecall \| appointment \| task |
| subject | str | `subject` |
| modified_on | str (ISO datetime) | `modifiedon` |
| regarding | str \| None | Related account/opportunity name |

## AgentResult

| Field | Type | Notes |
|-------|------|-------|
| answer | str | Final natural-language answer |
| tool_trace | list[ToolInvocation] | Ordered tools called |
| dry_run | bool | True when no live LLM/CRM were used |

## ToolInvocation (trace element)

| Field | Type | Notes |
|-------|------|-------|
| tool | str | Tool name |
| args | dict | Redacted arguments |
| ok | bool | Outcome |
| latency_ms | int | Duration |
