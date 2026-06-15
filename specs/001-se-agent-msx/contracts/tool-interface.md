# Contract: Tool Interface

All tools implement this contract. The agent loop depends only on this surface.

## Properties

- `name: str` — unique, lowercase, no spaces.
- `description: str` — concise capability description for the model.
- `input_schema: dict` — JSON Schema (draft-07 subset) describing `args`.
- `available() -> bool` — whether the tool can run in the current environment
  (e.g., `msx` returns False when no CRM credentials are configured).

## Method

```python
def run(self, args: dict) -> ToolResult: ...
```

### Preconditions

- `args` has already been validated against `input_schema` by the agent. Tools MAY
  re-assert critical invariants but MUST NOT assume the model is trustworthy.

### Postconditions

- Returns `ToolResult(ok=True, data=...)` on success.
- Returns `ToolResult(ok=False, error="...")` OR raises `ToolError` on failure.
- MUST NOT raise raw third-party exceptions to the agent; wrap them in `ToolError`.
- MUST NOT include secret values in `data`, `error`, or logs.

## Validation rules (enforced by the agent, not the tool)

- Unknown tool name → structured `unknown_tool` error, agent continues.
- `args` failing `input_schema` → `validation` error, tool not invoked.
