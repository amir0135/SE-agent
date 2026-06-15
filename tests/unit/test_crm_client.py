from se_agent.tools.crm import (
    MAX_QUERY_LENGTH,
    FakeCrmClient,
    _validate_query,
)
from se_agent.tools.base import ToolError
import pytest


def test_fake_filters_open_state():
    client = FakeCrmClient()
    rows = client.get("opportunities", {"$filter": "statecode eq 0"})
    assert all(r["statecode"] == 0 for r in rows)
    assert len(rows) == 3


def test_fake_orderby_desc():
    client = FakeCrmClient()
    rows = client.get("activitypointers", {"$orderby": "modifiedon desc"})
    assert rows[0]["modifiedon"] >= rows[-1]["modifiedon"]


def test_query_length_cap_enforced():
    too_long = {"$filter": "x" * (MAX_QUERY_LENGTH + 10)}
    with pytest.raises(ToolError) as exc:
        _validate_query(too_long)
    assert exc.value.code == "validation"
