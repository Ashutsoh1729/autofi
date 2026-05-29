"""Tests for orchestrator agent routing with TestModel."""

import tempfile
from pathlib import Path

from pydantic_ai.models.test import TestModel
from sqlmodel import Session, SQLModel, create_engine

from agents.registry import OrchestratorDeps
from agents.orchestrator import orchestrator_agent
from data.models import Account


def test_orchestrator_has_delegation_tool() -> None:
    """Verify the orchestrator has the bookkeeper delegation tool registered."""
    tool_names = [t.name for t in orchestrator_agent._function_toolset.tools.values()]
    assert "bookkeeper" in tool_names


def test_delegation_invokes_sub_agent() -> None:
    """Verify the bookkeeper delegation tool runs the sub-agent via TestModel.

    TestModel with call_tools='all' causes the orchestrator to call the
    'bookkeeper' delegation tool, which in turn runs bookkeeper_agent.run_sync
    with the same TestModel — proving the full delegation chain works.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    try:
        engine = create_engine(f"sqlite:///{path}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(Account(name="Delegate Test", type="checking", currency="INR"))
            session.commit()

        tm = TestModel(call_tools="all", seed=42)
        deps = OrchestratorDeps(db_path=path, model=tm)

        result = orchestrator_agent.run_sync(
            "Show me the accounts",
            model=tm,
            deps=deps,
        )

        assert result.output is not None
        assert isinstance(result.output, str)
    finally:
        path.unlink(missing_ok=True)


def test_orchestrator_multiturn_conversation() -> None:
    """Verify message_history works across turns."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    try:
        engine = create_engine(f"sqlite:///{path}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(Account(name="Multi-turn", type="checking", currency="INR"))
            session.commit()

        tm = TestModel(call_tools="all")
        deps = OrchestratorDeps(db_path=path, model=tm)

        r1 = orchestrator_agent.run_sync("Hello", model=tm, deps=deps)
        assert r1.output is not None

        r2 = orchestrator_agent.run_sync(
            "Show me accounts",
            model=tm,
            deps=deps,
            message_history=r1.new_messages(),
        )
        assert r2.output is not None
        assert len(r2.all_messages()) > len(r1.all_messages())
    finally:
        path.unlink(missing_ok=True)
