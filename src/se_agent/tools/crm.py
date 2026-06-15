"""Dynamics CRM Web API client.

Mirrors the MSX Helper desktop app: requests target the ``/api/data/v9.2/`` path prefix,
send ``Prefer: odata.include-annotations="*"``, and enforce query/body length caps.
The interface allows a deterministic fake for tests and dry mode.
"""

from __future__ import annotations

import abc
from typing import Any

from .auth import TokenProvider
from .base import ToolError

CRM_PATH_PREFIX = "/api/data/v9.2/"
MAX_QUERY_LENGTH = 8192
MAX_BODY_LENGTH = 1_000_000


class CrmClient(abc.ABC):
    @abc.abstractmethod
    def get(self, entity_set: str, query: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """GET an entity set with OData query params; return the ``value`` array."""
        raise NotImplementedError

    @abc.abstractmethod
    def patch(self, entity_set: str, entity_id: str, body: dict[str, Any]) -> None:
        """PATCH (update) a single entity by id. Used for approved write-backs."""
        raise NotImplementedError


def _validate_body(body: dict[str, Any]) -> str:
    """Serialize and length-check a write body (mirrors MSX Helper safety checks)."""
    import json

    payload = json.dumps(body or {})
    if len(payload) > MAX_BODY_LENGTH:
        raise ToolError("validation", "CRM body exceeds maximum allowed length")
    return payload


def _validate_query(query: dict[str, str] | None) -> str:
    """Build and length-check the OData query string (mirrors MSX Helper safety checks)."""
    if not query:
        return ""
    parts = []
    for key, value in query.items():
        parts.append(f"{key}={value}")
    qs = "&".join(parts)
    if len(qs) > MAX_QUERY_LENGTH:
        raise ToolError("validation", "CRM query exceeds maximum allowed length")
    return qs


class FakeCrmClient(CrmClient):
    """In-memory CRM with seeded sample records. Performs no network I/O."""

    def __init__(self, data: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self._data = data if data is not None else _sample_data()

    def get(self, entity_set: str, query: dict[str, str] | None = None) -> list[dict[str, Any]]:
        _validate_query(query)
        rows = list(self._data.get(entity_set, []))
        # Lightweight, best-effort support for the filters our MsxTool emits.
        if query:
            filt = query.get("$filter", "")
            rows = _apply_fake_filter(rows, filt)
            orderby = query.get("$orderby")
            if orderby:
                field = orderby.split()[0]
                desc = orderby.endswith("desc")
                rows = sorted(rows, key=lambda r: r.get(field, ""), reverse=desc)
            top = query.get("$top")
            if top and top.isdigit():
                rows = rows[: int(top)]
        return rows

    def patch(self, entity_set: str, entity_id: str, body: dict[str, Any]) -> None:
        _validate_body(body)
        rows = self._data.setdefault(entity_set, [])
        id_field = _ID_FIELDS.get(entity_set, "id")
        for row in rows:
            if row.get(id_field) == entity_id:
                row.update(body)
                return
        # If not found, record it so dry-mode commits are observable.
        new_row = {id_field: entity_id}
        new_row.update(body)
        rows.append(new_row)


def _apply_fake_filter(rows: list[dict[str, Any]], filt: str) -> list[dict[str, Any]]:
    if not filt:
        return rows
    out = rows
    # statecode eq 0  (Open)
    if "statecode eq 0" in filt:
        out = [r for r in out if r.get("statecode", 0) == 0]
    # contains(name,'Foo') or _accountname annotation contains
    if "contains(" in filt:
        start = filt.index("contains(")
        try:
            inner = filt[start + len("contains(") : filt.index(")", start)]
            field, needle = inner.split(",", 1)
            field = field.strip()
            needle = needle.strip().strip("'").lower()
            out = [r for r in out if needle in str(r.get(field, "")).lower()]
        except ValueError:
            pass
    return out


class HttpCrmClient(CrmClient):
    """Live CRM client. Lazily imports ``httpx`` (the 'live' extra)."""

    def __init__(self, crm_url: str, token_provider: TokenProvider, timeout: float = 30.0) -> None:
        self._base = crm_url.rstrip("/")
        self._tokens = token_provider
        self._timeout = timeout

    def _scope(self) -> str:
        return f"{self._base}/.default"

    def get(self, entity_set: str, query: dict[str, str] | None = None) -> list[dict[str, Any]]:
        try:
            import httpx  # type: ignore
        except ImportError as exc:  # pragma: no cover - only in live installs
            raise ToolError(
                "transport",
                "httpx is not installed; install the 'live' extra to call CRM",
            ) from exc

        qs = _validate_query(query)
        path = f"{CRM_PATH_PREFIX}{entity_set}"
        if not path.startswith(CRM_PATH_PREFIX):  # defensive; always true here
            raise ToolError("validation", "CRM path must start with /api/data/v9.2/")
        url = f"{self._base}{path}"
        if qs:
            url = f"{url}?{qs}"

        token = self._tokens.get_token(self._scope())
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Prefer": 'odata.include-annotations="*"',
        }
        try:
            resp = httpx.get(url, headers=headers, timeout=self._timeout)
        except Exception as exc:  # network failure
            raise ToolError("transport", f"CRM request failed: {type(exc).__name__}") from exc

        if resp.status_code in (401, 403):
            raise ToolError("auth", f"CRM returned {resp.status_code} (token rejected)")
        if resp.status_code >= 400:
            raise ToolError("transport", f"CRM returned HTTP {resp.status_code}")

        body = resp.json()
        return body.get("value", []) if isinstance(body, dict) else []

    def patch(self, entity_set: str, entity_id: str, body: dict[str, Any]) -> None:
        try:
            import httpx  # type: ignore
        except ImportError as exc:  # pragma: no cover - only in live installs
            raise ToolError(
                "transport",
                "httpx is not installed; install the 'live' extra to call CRM",
            ) from exc

        payload = _validate_body(body)
        path = f"{CRM_PATH_PREFIX}{entity_set}({entity_id})"
        if not path.startswith(CRM_PATH_PREFIX):  # defensive; always true here
            raise ToolError("validation", "CRM path must start with /api/data/v9.2/")
        url = f"{self._base}{path}"

        token = self._tokens.get_token(self._scope())
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "If-Match": "*",
        }
        try:
            resp = httpx.patch(url, headers=headers, content=payload, timeout=self._timeout)
        except Exception as exc:  # network failure
            raise ToolError("transport", f"CRM request failed: {type(exc).__name__}") from exc

        if resp.status_code in (401, 403):
            raise ToolError("auth", f"CRM returned {resp.status_code} (token rejected)")
        if resp.status_code >= 400:
            raise ToolError("transport", f"CRM returned HTTP {resp.status_code}")


# Primary-key field names per entity set (used to locate records for PATCH).
_ID_FIELDS: dict[str, str] = {
    "opportunities": "opportunityid",
    "accounts": "accountid",
    "contacts": "contactid",
    "activitypointers": "activityid",
}


def _sample_data() -> dict[str, list[dict[str, Any]]]:
    """Seed data used in dry mode / tests. Mirrors common CRM fields."""
    return {
        "opportunities": [
            {
                "opportunityid": "opp-1",
                "name": "Contoso Cloud Migration",
                "_parentaccountid_value@OData.Community.Display.V1.FormattedValue": "Contoso",
                "salesstage@OData.Community.Display.V1.FormattedValue": "Propose",
                "estimatedvalue": 250000.0,
                "estimatedclosedate": "2026-09-30",
                "statecode": 0,
            },
            {
                "opportunityid": "opp-2",
                "name": "Contoso Security Uplift",
                "_parentaccountid_value@OData.Community.Display.V1.FormattedValue": "Contoso",
                "salesstage@OData.Community.Display.V1.FormattedValue": "Develop",
                "estimatedvalue": 120000.0,
                "estimatedclosedate": "2026-08-15",
                "statecode": 0,
            },
            {
                "opportunityid": "opp-3",
                "name": "Contoso Data Platform",
                "_parentaccountid_value@OData.Community.Display.V1.FormattedValue": "Contoso",
                "salesstage@OData.Community.Display.V1.FormattedValue": "Qualify",
                "estimatedvalue": 90000.0,
                "estimatedclosedate": "2026-11-01",
                "statecode": 0,
            },
            {
                "opportunityid": "opp-4",
                "name": "Fabrikam Modern Workplace",
                "_parentaccountid_value@OData.Community.Display.V1.FormattedValue": "Fabrikam",
                "salesstage@OData.Community.Display.V1.FormattedValue": "Close",
                "estimatedvalue": 60000.0,
                "estimatedclosedate": "2026-07-20",
                "statecode": 1,
            },
        ],
        "accounts": [
            {"accountid": "acc-1", "name": "Contoso", "_ownerid_value@OData.Community.Display.V1.FormattedValue": "Avery Engineer"},
            {"accountid": "acc-2", "name": "Fabrikam", "_ownerid_value@OData.Community.Display.V1.FormattedValue": "Avery Engineer"},
        ],
        "contacts": [
            {"contactid": "con-1", "fullname": "Nancy Davolio", "_parentcustomerid_value@OData.Community.Display.V1.FormattedValue": "Contoso", "emailaddress1": "nancy@contoso.example"},
            {"contactid": "con-2", "fullname": "Andrew Fuller", "_parentcustomerid_value@OData.Community.Display.V1.FormattedValue": "Fabrikam", "emailaddress1": "andrew@fabrikam.example"},
        ],
        "activitypointers": [
            {"activityid": "act-1", "activitytypecode": "email", "subject": "Follow up on migration POC", "modifiedon": "2026-06-12T10:00:00Z", "_regardingobjectid_value@OData.Community.Display.V1.FormattedValue": "Contoso Cloud Migration"},
            {"activityid": "act-2", "activitytypecode": "phonecall", "subject": "Security workshop scheduling", "modifiedon": "2026-06-13T14:30:00Z", "_regardingobjectid_value@OData.Community.Display.V1.FormattedValue": "Contoso Security Uplift"},
        ],
    }
