from se_agent.tools.crm import FakeCrmClient
from se_agent.tools.msx import MsxTool


def test_patch_updates_existing_opportunity():
    crm = FakeCrmClient()
    tool = MsxTool(crm)
    # Before: stage label is "Propose"
    before = tool.run({"operation": "open_opportunities", "account_name": "Contoso"})
    assert before.ok
    # Apply an approved write-back to opp-1.
    res = tool.commit_update(
        "opportunities", "opp-1",
        {"salesstage@OData.Community.Display.V1.FormattedValue": "Develop"},
    )
    assert res.ok
    assert res.data["id"] == "opp-1"
    # After: the row reflects the new stage.
    rows = crm.get("opportunities", {"$filter": "statecode eq 0"})
    opp1 = next(r for r in rows if r["opportunityid"] == "opp-1")
    assert opp1["salesstage@OData.Community.Display.V1.FormattedValue"] == "Develop"


def test_commit_update_requires_id():
    tool = MsxTool(FakeCrmClient())
    import pytest
    from se_agent.tools.base import ToolError
    with pytest.raises(ToolError) as exc:
        tool.commit_update("opportunities", "", {"x": 1})
    assert exc.value.code == "validation"


def test_commit_update_unavailable_without_crm():
    tool = MsxTool(None)
    res = tool.commit_update("opportunities", "opp-1", {"x": 1})
    assert not res.ok
    assert "unavailable" in res.error.lower()


def test_patch_body_length_capped():
    import pytest
    from se_agent.tools.base import ToolError
    crm = FakeCrmClient()
    huge = {"note": "x" * 2_000_000}
    with pytest.raises(ToolError) as exc:
        crm.patch("opportunities", "opp-1", huge)
    assert exc.value.code == "validation"
