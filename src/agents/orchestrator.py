"""Orchestrator agent — routes user requests to specialist sub-agents."""

import logging

from pydantic_ai import Agent

from agents.bookkeeper import (
    BookkeeperDeps,
    bookkeeper_agent,
)
from agents.registry import (
    AgentEntry,
    OrchestratorDeps,
    register_agent,
    wire_orchestrator_tools,
)
from agents.settings import create_agent_model
from util.config import get_db_path

logger = logging.getLogger(__name__)


def _default_deps() -> OrchestratorDeps:
    return OrchestratorDeps(db_path=get_db_path())


# Register specialist agents
register_agent(
    "bookkeeper",
    AgentEntry(
        agent=bookkeeper_agent,
        description=(
            "Categorises transactions, lists transactions, shows transaction stats, "
            "and manages the chart of accounts."
        ),
        deps_factory=lambda od: BookkeeperDeps(db_path=od.db_path),
    ),
)

# Create orchestrator agent
orchestrator_agent = Agent(
    create_agent_model("orchestrator"),
    system_prompt=(
        "You are the Orchestrator agent for AutoFi, an autonomous financial "
        "operations system.\n\n"
        "Your role:\n"
        "1. Receive and understand the user's financial questions and requests.\n"
        "2. Decompose complex requests into smaller tasks.\n"
        "3. Delegate tasks to specialist agents using your available tools.\n"
        "4. Synthesise results from specialist agents into a clear, "
        "concise response.\n"
        "   When a specialist returns tabular data or a list, "
        "pass it through verbatim — do NOT rephrase, summarize, or "
        "say 'a table was printed'.\n\n"
        "Available specialist agents (call them via tools):\n"
        "- bookkeeper: categorises transactions, lists transactions, "
        "shows transaction stats, and manages the chart of accounts.\n\n"
        "You must ALWAYS delegate to specialist agents — NEVER try to answer "
        "financial questions yourself. Describe the task in natural language "
        "when delegating.\n"
        "If a specialist agent returns an error, explain the issue to the user.\n"
        "Always confirm destructive actions before executing them."
    ),
    deps_type=OrchestratorDeps,
    defer_model_check=True,
)

# Auto-wire delegation tools from the registry
wire_orchestrator_tools(orchestrator_agent)
