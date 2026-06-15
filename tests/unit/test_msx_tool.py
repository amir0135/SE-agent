from se_agent.tools.crm import FakeCrmClient
from se_agent.tools.msx import MsxTool


def test_open_opportunities_for_account_with_total():
    tool = MsxTool(FakeCrmClient())
    assert tool.available() is True
    result = tool.run({"operation": "open_opportunities", "account_name": "Contoso"})
    assert result.ok
    data = result.data
    # Three open Contoso opportunities in the seed data (Fabrikam one is won/closed).
    assert data["count"] == 3
    names = {o["name"] for o in data["opportunities"]}
    assert "Contoso Cloud Migration" in names
    assert "Fabrikam Modern Workplace" not in names
    assert data["total_estimated_value"] == 250000 + 120000 + 90000


def test_open_opportunities_empty_account():
    tool = MsxTool(FakeCrmClient())
    result = tool.run({"operation": "open_opportunities", "account_name": "Northwind"})
    assert result.ok
    assert result.data["count"] == 0
    assert result.data["total_estimated_value"] == 0


def test_unavailable_without_crm():
    tool = MsxTool(None)
    assert tool.available() is False
    result = tool.run({"operation": "accounts"})
    assert not result.ok
    assert "unavailable" in result.error.lower()


def test_recent_activities_ordered():
    tool = MsxTool(FakeCrmClient())
    result = tool.run({"operation": "recent_activities"})
    assert result.ok
    acts = result.data["activities"]
    assert len(acts) == 2
    # Ordered by modifiedon desc -> the 06-13 phonecall first.
    assert acts[0]["type"] == "phonecall"
