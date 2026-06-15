import pytest

from se_agent.tools.echo import EchoTool
from se_agent.tools.msx import MsxTool
from se_agent.tools.base import ToolError
from se_agent.tools.registry import ToolRegistry


def test_register_and_list():
    reg = ToolRegistry()
    reg.register(EchoTool())
    reg.register(MsxTool(None))
    assert reg.has("echo")
    assert reg.has("msx")
    names = {t.name for t in reg.list()}
    assert names == {"echo", "msx"}


def test_duplicate_registration_rejected():
    reg = ToolRegistry()
    reg.register(EchoTool())
    with pytest.raises(ValueError):
        reg.register(EchoTool())


def test_unknown_tool_raises_structured_error():
    reg = ToolRegistry()
    with pytest.raises(ToolError) as exc:
        reg.get("nope")
    assert exc.value.code == "unknown_tool"


def test_descriptors_available_only():
    reg = ToolRegistry()
    reg.register(MsxTool(None))  # unavailable (no CRM)
    reg.register(EchoTool())
    available = reg.descriptors(available_only=True)
    names = {d["name"] for d in available}
    assert names == {"echo"}
