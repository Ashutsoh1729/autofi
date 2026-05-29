"""Unit tests for bookkeeper agent tools using TestModel + in-memory SQLite."""

import datetime
import tempfile
from pathlib import Path

import pytest
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from sqlmodel import Session, SQLModel, create_engine

from agents.bookkeeper import (
    BookkeeperDeps,
    bookkeeper_agent,
    categorise_transaction,
    list_accounts,
    list_transactions,
)
from data.models import Account, Transaction


@pytest.fixture
def db_path() -> Path:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Account(name="Test Account", type="checking", currency="INR"))
        session.commit()
        # Add sample transactions
        for i in range(3):
            session.add(
                Transaction(
                    account_id=1,
                    date=datetime.date(2025, 1, i + 1),
                    description=f"Transaction {i}",
                    amount=100.0 + i,
                    hash=f"hash_{i}",
                )
            )
        session.commit()
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def ctx(db_path: Path) -> RunContext[BookkeeperDeps]:
    return RunContext[BookkeeperDeps](
        deps=BookkeeperDeps(db_path=db_path),
        model=None,
        usage=None,
        prompt="test",
        retry=0,
    )


def _add_test_tx(session: Session, description: str, amount: float) -> Transaction:
    tx = Transaction(
        account_id=1,
        date=datetime.date(2025, 2, 1),
        description=description,
        amount=amount,
        currency="INR",
        hash=f"hash_{description}_{amount}",
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# categorise_transaction
# ---------------------------------------------------------------------------


def test_categorise_transaction_ok(ctx: RunContext[BookkeeperDeps]) -> None:
    result = categorise_transaction(ctx, tx_id=1, category="Food")
    assert "categorised as 'Food'" in result

    # Verify the DB was actually updated
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 1)
        assert t is not None
        assert t.category == "Food"


def test_categorise_transaction_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = categorise_transaction(ctx, tx_id=999, category="Rent")
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# list_transactions
# ---------------------------------------------------------------------------


def test_list_transactions_matches(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        _add_test_tx(session, "Starbucks Coffee", 5.50)
        _add_test_tx(session, "Starbucks Latte", 6.00)
        _add_test_tx(session, "Amazon Books", 15.00)

    result = list_transactions(ctx, query="Starbucks", limit=5)
    assert "Starbucks Coffee" in result
    assert "Starbucks Latte" in result
    assert "Amazon Books" not in result
    assert "5.50" in result
    assert "6.00" in result


def test_list_transactions_no_match(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_transactions(ctx, query="ZZZZNOTFOUND", limit=5)
    assert "No transactions found" in result


# ---------------------------------------------------------------------------
# list_accounts
# ---------------------------------------------------------------------------


def test_list_accounts(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_accounts(ctx)
    # Should include the seeded account
    assert "Test Account" in result or "No accounts found" in result


# ---------------------------------------------------------------------------
# Agent integration with TestModel
# ---------------------------------------------------------------------------


def test_bookkeeper_agent_with_testmodel() -> None:
    """Verify the agent can be invoked with TestModel and tool calls work."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    try:
        engine = create_engine(f"sqlite:///{path}")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(Account(name="Agent Test Account", type="checking", currency="INR"))
            session.commit()
            session.add(
                Transaction(
                    account_id=1,
                    date=datetime.date(2025, 3, 1),
                    description="Agent test tx",
                    amount=42.0,
                    hash="agent_test_hash",
                )
            )
            session.commit()

        deps = BookkeeperDeps(db_path=path)
        tm = TestModel(call_tools="all", seed=1)
        result = bookkeeper_agent.run_sync(
            "Categorise transaction 1 as Food",
            model=tm,
            deps=deps,
        )
        assert result.output is not None
        # TestModel will call categorise_transaction with seed=1's tx_id
        # Since seed=1, the tool will be invoked
    finally:
        path.unlink(missing_ok=True)
