"""SE-Agent: a Solution Engineer agent with pluggable tools, including MSX (Dynamics CRM)."""

from .agent import Agent, AgentResult
from .config import Settings
from .tools.registry import ToolRegistry

__all__ = ["Agent", "AgentResult", "Settings", "ToolRegistry"]
__version__ = "0.1.0"
