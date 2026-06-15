from se_agent.agent import Agent
from se_agent.llm.fake import FakeLLM
from se_agent.tools.crm import FakeCrmClient
from se_agent.tools.echo import EchoTool
from se_agent.tools.msx import MsxTool
from se_agent.tools.registry import ToolRegistry


def _registry(crm=None):
    reg = ToolRegistry()
    reg.register(MsxTool(crm if crm is not None else FakeCrmClient()))
    reg.register(EchoTool())
    return reg


def test_pipeline_question_end_to_end():
    agent = Agent(FakeLLM(), _registry(), dry_run=True)
    result = agent.run("What are my open opportunities for Contoso and the total pipeline?")
    assert result.dry_run
    assert len(result.tool_trace) == 1
    inv = result.tool_trace[0]
    assert inv.tool == "msx"
    assert inv.ok
    assert "Total pipeline: $460,000" in result.answer
    assert "Contoso Cloud Migration" in result.answer


def test_empty_account_pipeline_is_graceful():
    agent = Agent(FakeLLM(), _registry(), dry_run=True)
    result = agent.run("Show open opportunities for Northwind")
    assert result.tool_trace[0].ok
    assert "No open opportunities" in result.answer


def test_no_tool_question_answers_directly():
    agent = Agent(FakeLLM(), _registry(), dry_run=True)
    result = agent.run("Hello there")
    assert result.tool_trace == []
    assert "MSX" in result.answer
