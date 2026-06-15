"""The MSX tool — the flagship capability.

Reads Microsoft Sales Experience / Dynamics CRM data (opportunities, accounts, contacts,
recent activities) via the CRM Web API, mirroring the MSX Helper desktop app.
"""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolError, ToolResult
from .crm import CrmClient

_ACCOUNT_FMT = "_parentaccountid_value@OData.Community.Display.V1.FormattedValue"
_STAGE_FMT = "salesstage@OData.Community.Display.V1.FormattedValue"
_OWNER_FMT = "_ownerid_value@OData.Community.Display.V1.FormattedValue"
_CUSTOMER_FMT = "_parentcustomerid_value@OData.Community.Display.V1.FormattedValue"
_REGARDING_FMT = "_regardingobjectid_value@OData.Community.Display.V1.FormattedValue"

_STATE_LABELS = {0: "open", 1: "won", 2: "lost"}


class MsxTool(Tool):
    name = "msx"
    description = (
        "Query Microsoft Sales Experience (Dynamics CRM): open opportunities, accounts, "
        "contacts, and recent activities, optionally filtered by account name."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "open_opportunities",
                    "accounts",
                    "contacts",
                    "recent_activities",
                ],
            },
            "account_name": {
                "type": "string",
                "description": "Optional account display name to filter by.",
            },
            "top": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        },
        "required": ["operation"],
        "additionalProperties": False,
    }

    def __init__(self, crm: CrmClient | None) -> None:
        self._crm = crm

    def available(self) -> bool:
        return self._crm is not None

    def run(self, args: dict[str, Any]) -> ToolResult:
        if self._crm is None:
            return ToolResult.failure("MSX unavailable: no CRM credentials configured")

        operation = args["operation"]
        account = args.get("account_name")
        top = int(args.get("top", 10))

        try:
            handler = {
                "open_opportunities": self._open_opportunities,
                "accounts": self._accounts,
                "contacts": self._contacts,
                "recent_activities": self._recent_activities,
            }[operation]
        except KeyError:
            raise ToolError("validation", f"Unknown operation '{operation}'")

        return ToolResult.success(handler(account, top))

    # -- write-back (approved commits) ------------------------------------------------

    def commit_update(self, entity_set: str, entity_id: str, body: dict[str, Any]) -> ToolResult:
        """Apply an approved write-back to CRM (PATCH a single entity).

        Called only after an APPROVE-FIRST tap; the caller (worker) gates on the approval
        token before invoking this.
        """
        if self._crm is None:
            return ToolResult.failure("MSX unavailable: no CRM credentials configured")
        if not entity_id:
            raise ToolError("validation", "entity_id is required to commit an update")
        self._crm.patch(entity_set, entity_id, body)
        return ToolResult.success({"entity_set": entity_set, "id": entity_id, "applied": body})

    # -- operations -------------------------------------------------------------------

    def _open_opportunities(self, account: str | None, top: int) -> dict[str, Any]:
        filters = ["statecode eq 0"]
        if account:
            filters.append(f"contains({_ACCOUNT_FMT},'{account}')")
        rows = self._crm.get(
            "opportunities",
            {"$filter": " and ".join(filters), "$top": str(top)},
        )
        opps = [
            {
                "id": r.get("opportunityid"),
                "name": r.get("name"),
                "account_name": r.get(_ACCOUNT_FMT),
                "stage": r.get(_STAGE_FMT),
                "estimated_value": r.get("estimatedvalue"),
                "close_date": r.get("estimatedclosedate"),
                "status": _STATE_LABELS.get(r.get("statecode", 0), "open"),
            }
            for r in rows
        ]
        total = sum(o["estimated_value"] or 0 for o in opps)
        return {"opportunities": opps, "count": len(opps), "total_estimated_value": total}

    def _accounts(self, account: str | None, top: int) -> dict[str, Any]:
        query: dict[str, str] = {"$top": str(top)}
        if account:
            query["$filter"] = f"contains(name,'{account}')"
        rows = self._crm.get("accounts", query)
        return {
            "accounts": [
                {"id": r.get("accountid"), "name": r.get("name"), "owner": r.get(_OWNER_FMT)}
                for r in rows
            ]
        }

    def _contacts(self, account: str | None, top: int) -> dict[str, Any]:
        query: dict[str, str] = {"$top": str(top)}
        if account:
            query["$filter"] = f"contains({_CUSTOMER_FMT},'{account}')"
        rows = self._crm.get("contacts", query)
        return {
            "contacts": [
                {
                    "id": r.get("contactid"),
                    "name": r.get("fullname"),
                    "account_name": r.get(_CUSTOMER_FMT),
                    "email": r.get("emailaddress1"),
                }
                for r in rows
            ]
        }

    def _recent_activities(self, account: str | None, top: int) -> dict[str, Any]:
        query: dict[str, str] = {"$orderby": "modifiedon desc", "$top": str(top)}
        rows = self._crm.get("activitypointers", query)
        activities = [
            {
                "id": r.get("activityid"),
                "type": r.get("activitytypecode"),
                "subject": r.get("subject"),
                "modified_on": r.get("modifiedon"),
                "regarding": r.get(_REGARDING_FMT),
            }
            for r in rows
        ]
        if account:
            activities = [
                a for a in activities if account.lower() in str(a.get("regarding", "")).lower()
            ]
        return {"activities": activities}
