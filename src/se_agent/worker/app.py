"""Cloud MSX Worker — a hosted HTTP service exposing the `msx` tool.

This is the cloud replacement for the local MSX Helper app. It reuses the exact same
`MsxTool` + `HttpCrmClient` + `MsalTokenProvider` from `se_agent`, so there is no separate
CRM implementation to maintain. The orchestrator (Copilot Studio / Foundry) calls these
HTTPS endpoints instead of a localhost MCP server.

Endpoints:
- GET  /healthz        liveness
- GET  /msx/tools      tool descriptor (MCP-compatible) + availability
- POST /msx/query      read operations (open_opportunities, accounts, contacts, recent_activities)
- POST /msx/draft      stage a draft write (never committed)
- POST /msx/commit     commit a previously-staged draft — requires an approval token

Writes are draft-only by design: `/msx/draft` stages a change and returns a `draft_id`;
`/msx/commit` only proceeds when given a valid approval token (the orchestrator supplies it
after the user taps Approve). This mirrors the APPROVE-FIRST guardrail in the cloud.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

try:
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - only when extras missing
    raise SystemExit(
        "The Cloud MSX Worker needs the 'worker' extra: pip install -e '.[worker]'"
    ) from exc

from se_agent.config import Settings
from se_agent.logging import get_logger, redact
from se_agent.tools.auth import MsalTokenProvider
from se_agent.tools.crm import FakeCrmClient, HttpCrmClient
from se_agent.tools.msx import MsxTool

log = get_logger()


# --------------------------------------------------------------------------------------
# Wiring: build the same MsxTool the CLI uses, choosing live vs. fake from the environment.
# --------------------------------------------------------------------------------------

def _build_msx_tool() -> MsxTool:
    settings = Settings.from_env()
    if settings.force_dry_run or not settings.crm.configured or not settings.crm.client_secret:
        # Dry/dev: sample data, no network. Lets the worker run with no secrets.
        log.info("Cloud MSX Worker starting with FakeCrmClient (dry mode)")
        return MsxTool(FakeCrmClient())
    provider = MsalTokenProvider(
        tenant_id=settings.crm.tenant_id or "",
        client_id=settings.crm.client_id or "",
        client_secret=settings.crm.client_secret,
    )
    log.info("Cloud MSX Worker starting with live HttpCrmClient")
    return MsxTool(HttpCrmClient(crm_url=settings.crm.crm_url or "", token_provider=provider))


# In-memory draft store. Swap for Dataverse/Table storage in production.
_DRAFTS: dict[str, dict[str, Any]] = {}

# Maps a staged draft operation to the CRM entity set it writes to.
_ENTITY_FOR_OPERATION: dict[str, str] = {
    "draft_milestone_update": "opportunities",
    "draft_opportunity_update": "opportunities",
}

# Approval token the orchestrator must present to commit. From env (Key Vault in cloud).
_APPROVAL_TOKEN = os.environ.get("SEAGENT_APPROVAL_TOKEN", "")


# --------------------------------------------------------------------------------------
# Request/response models
# --------------------------------------------------------------------------------------

class QueryRequest(BaseModel):
    operation: str = Field(..., description="open_opportunities | accounts | contacts | recent_activities")
    account_name: str | None = None
    top: int = Field(10, ge=1, le=50)


class DraftRequest(BaseModel):
    operation: str = Field(..., description="e.g. draft_milestone_update")
    opportunity_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CommitRequest(BaseModel):
    draft_id: str


def create_app() -> "FastAPI":
    application = FastAPI(title="Cloud MSX Worker", version="0.1.0")
    msx = _build_msx_tool()

    @application.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ok", "msx_available": msx.available()}

    @application.get("/msx/tools")
    def tools() -> dict[str, Any]:
        return {"tool": msx.descriptor(), "available": msx.available()}

    @application.post("/msx/query")
    def query(req: QueryRequest) -> dict[str, Any]:
        if req.operation not in {"open_opportunities", "accounts", "contacts", "recent_activities"}:
            raise HTTPException(status_code=400, detail="Unsupported read operation")
        args = {"operation": req.operation, "top": req.top}
        if req.account_name:
            args["account_name"] = req.account_name
        log.info("query %s", redact(args))
        result = msx.run(args)
        if not result.ok:
            raise HTTPException(status_code=502, detail=result.error)
        return {"ok": True, "data": result.data}

    @application.post("/msx/draft")
    def draft(req: DraftRequest) -> dict[str, Any]:
        # Staged only — never written to CRM here.
        draft_id = uuid.uuid4().hex
        _DRAFTS[draft_id] = {
            "operation": req.operation,
            "opportunity_id": req.opportunity_id,
            "payload": req.payload,
        }
        log.info("staged draft %s op=%s", draft_id, req.operation)
        return {"ok": True, "draft_id": draft_id, "staged": _DRAFTS[draft_id]}

    @application.post("/msx/commit")
    def commit(req: CommitRequest, x_approval_token: str = Header(default="")) -> dict[str, Any]:
        # APPROVE-FIRST: commits require the approval token the orchestrator supplies
        # only after the user taps Approve.
        if not _APPROVAL_TOKEN or x_approval_token != _APPROVAL_TOKEN:
            raise HTTPException(status_code=403, detail="Missing or invalid approval token")
        staged = _DRAFTS.pop(req.draft_id, None)
        if staged is None:
            raise HTTPException(status_code=404, detail="Unknown draft_id")

        # Map the staged draft to a CRM write-back and apply it.
        entity_set = _ENTITY_FOR_OPERATION.get(staged["operation"])
        if entity_set is None:
            raise HTTPException(
                status_code=400, detail=f"Unsupported draft operation '{staged['operation']}'"
            )
        if not staged.get("opportunity_id"):
            raise HTTPException(status_code=400, detail="Draft is missing the target id")
        try:
            result = msx.commit_update(
                entity_set=entity_set,
                entity_id=staged["opportunity_id"],
                body=staged.get("payload") or {},
            )
        except Exception as exc:  # never leak internals
            log.exception("commit failed for draft %s", req.draft_id)
            raise HTTPException(status_code=502, detail="CRM write-back failed") from exc
        if not result.ok:
            raise HTTPException(status_code=502, detail=result.error)
        log.info("committed draft %s op=%s", req.draft_id, staged["operation"])
        return {"ok": True, "committed": staged, "result": result.data}

    return application


# Module-level app for `uvicorn se_agent.worker.app:app`
app = create_app()
