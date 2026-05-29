"""Agent registry — holds agent metadata and auto-generates delegation tools."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorDeps:
    """Dependencies for the orchestrator agent."""

    db_path: Path
    model: Any = None


@dataclass
class AgentEntry:
    """Metadata for a registered specialist agent."""

    agent: Agent[Any, Any]
    description: str
    deps_factory: Callable[[OrchestratorDeps], Any]


AGENT_REGISTRY: dict[str, AgentEntry] = {}


def register_agent(name: str, entry: AgentEntry) -> None:
    """Register a specialist agent in the global registry."""
    AGENT_REGISTRY[name] = entry


def _make_delegation_tool(
    name: str,
    entry: AgentEntry,
) -> Callable[[RunContext[OrchestratorDeps], str], str]:
    """Build a delegation tool function that routes to a sub-agent."""

    def delegator(ctx: RunContext[OrchestratorDeps], task: str) -> str:
        sub_deps = entry.deps_factory(ctx.deps)
        kwargs: dict[str, Any] = {"deps": sub_deps}
        if ctx.deps.model is not None:
            kwargs["model"] = ctx.deps.model
        try:
            logger.info("Delegating task to '%s': %s", name, task)
            result = entry.agent.run_sync(task, **kwargs)
        except Exception as exc:
            logger.exception("Delegation to '%s' failed", name)
            return f"Error in {name}: {exc}"
        else:
            return result.output

    delegator.__name__ = name
    delegator.__qualname__ = name
    delegator.__doc__ = (
        f"Delegate a task to the {name} specialist agent.\n\n"
        f"Args:\n    task: The task description in natural language.\n\n"
        f"Returns:\n    The {name} agent's response."
    )
    return delegator


def wire_orchestrator_tools(orchestrator_agent: Agent[OrchestratorDeps, Any]) -> None:
    """Auto-generate delegation tools for all registered agents."""
    for name, entry in AGENT_REGISTRY.items():
        tool_func = _make_delegation_tool(name, entry)
        orchestrator_agent.tool(tool_func)
        logger.info("Registered delegation tool: '%s'", name)
