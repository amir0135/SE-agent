# Contract: `msx` Tool

Reads Microsoft Sales Experience / Dynamics CRM data via the CRM Web API (`/api/data/v9.2/`),
mirroring the MSX Helper desktop app. Read-only in v1.

## name
`msx`

## description
"Query Microsoft Sales Experience (Dynamics CRM): open opportunities, accounts, contacts,
and recent activities, optionally filtered by account name."

## input_schema (JSON Schema)

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["open_opportunities", "accounts", "contacts", "recent_activities"]
    },
    "account_name": {
      "type": "string",
      "description": "Optional account display name to filter by."
    },
    "top": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 10
    }
  },
  "required": ["operation"],
  "additionalProperties": false
}
```

## Behavior

| operation | CRM entity set | Notes |
|-----------|----------------|-------|
| open_opportunities | `opportunities` | filter `statecode eq 0` (Open); optional account filter; returns Opportunity[] |
| accounts | `accounts` | optional name `contains`; returns Account[] |
| contacts | `contacts` | optional account filter; returns Contact summary[] |
| recent_activities | `activitypointers` | order by `modifiedon desc`; returns Activity[] |

## Request rules (mirrors MSX Helper)

- Path prefix MUST be `/api/data/v9.2/`.
- Header `Prefer: odata.include-annotations="*"` is sent on reads.
- Query length and body length are capped; over-limit requests are rejected locally.
- Only GET is used in v1 (no writes, no `$batch`).

## availability

`available()` returns True only when CRM URL + an Entra token source are configured via
env. Otherwise the tool reports `unavailable (no credentials)` and the agent stays usable.

## Errors

- `auth` — token acquisition or 401/403 from CRM (no token value leaked).
- `transport` — network failure/timeout.
- `not_found` — account filter matched nothing (returns empty list, not an error, for
  list operations; `not_found` only for single-entity lookups).
