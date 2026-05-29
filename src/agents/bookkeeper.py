"""Bookkeeper agent — transaction management and chart of accounts."""

import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from sqlmodel import Session, col, select

from agents.settings import create_agent_model
from data.db import get_session, init_db
from data.models import Account, Transaction
from util.config import get_db_path as _config_get_db_path

logger = logging.getLogger(__name__)


@dataclass
class BookkeeperDeps:
    """Dependencies for the bookkeeper agent."""

    db_path: Path


def _default_deps() -> BookkeeperDeps:
    return BookkeeperDeps(db_path=_config_get_db_path())


# ---------------------------------------------------------------------------
# Standalone tool functions (registered on bookkeeper_agent below)
# ---------------------------------------------------------------------------


def categorise_transaction(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
    category: str,
) -> str:
    """Categorise a transaction by its ID.

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The ID of the transaction to categorise.
        category: The category label (e.g. "Food", "Rent", "Salary").

    Returns:
        A confirmation message.

    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        t = session.get(Transaction, tx_id)
        if t is None:
            logger.warning("categorise_transaction: tx %s not found", tx_id)
            return f"Transaction {tx_id} not found."
        old = t.category
        t.category = category
        session.add(t)
        session.commit()
        logger.info("Categorised tx %s: '%s' → '%s'", tx_id, old, category)
        return f"Transaction {tx_id} categorised as '{category}'."

    logger.error("categorise_transaction: no DB session available")
    return "Error: could not connect to database."


def list_transactions(
    ctx: RunContext[BookkeeperDeps],
    query: str = "",
    limit: int = 20,
) -> str:
    """List transactions, optionally filtered by description search.

    Args:
        ctx: Bookkeeper agent context with DB path.
        query: Search term to filter by transaction description.
              Leave empty to list all transactions.
        limit: Maximum number of results (default 20).

    Returns:
        A formatted table of matching transactions.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Transaction).order_by(col(Transaction.date).desc()).limit(limit)
        if query:
            stmt = stmt.where(col(Transaction.description).ilike(f"%{query}%"))
        txs = list(session.exec(stmt).all())
        if not txs:
            return "No transactions found."

        header = (
            f"{'ID':>5}  {'Date':<12}  {'Description':<50}  "
            f"{'Amount':>10}  {'Category':<20}"
        )
        lines = [header, "-" * 100]
        for t in txs:
            cat = t.category or "—"
            lines.append(
                f"{t.id:>5}  {t.date!s:<12}  {t.description:<50}  "
                f"{t.amount:>10.2f}  {cat:<20}",
            )
        return "\n".join(lines)

    logger.error("list_transactions: no DB session available")
    return "Error: could not connect to database."


def get_transaction_stats(ctx: RunContext[BookkeeperDeps]) -> str:
    """Get summary statistics for all transactions.

    Args:
        ctx: Bookkeeper agent context with DB path.

    Returns:
        A formatted summary (total count, per-account counts, date range).
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        total = session.exec(select(Transaction)).all()
        total_count = len(total)

        accts = session.exec(select(Account)).all()
        per_account: dict[str, int] = {}
        for acct in accts:
            cnt = len(
                session.exec(
                    select(Transaction).where(Transaction.account_id == acct.id),
                ).all(),
            )
            per_account[acct.name] = cnt

        dates = [t.date for t in total]
        date_range: str | None = None
        if dates:
            date_range = f"{min(dates).isoformat()} to {max(dates).isoformat()}"

        lines = [f"Total transactions: {total_count}"]
        lines.append("Per account:")
        for name, count in per_account.items():
            lines.append(f"  {name}: {count}")
        if date_range:
            lines.append(f"Date range: {date_range}")
        return "\n".join(lines)

    return "No transactions found."


def list_accounts(ctx: RunContext[BookkeeperDeps]) -> str:
    """List all accounts in the chart of accounts with transaction counts.

    Args:
        ctx: Bookkeeper agent context with DB path.

    Returns:
        A formatted table of accounts.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        accounts = session.exec(select(Account).order_by(Account.name)).all()
        if not accounts:
            return "No accounts found."

        header = (
            f"{'ID':>3}  {'Name':<30}  {'Type':<15}  "
            f"{'Currency':<10}  {'Transactions':>12}"
        )
        lines = [header, "-" * 75]
        for acct in accounts:
            count = len(
                session.exec(
                    select(Transaction).where(Transaction.account_id == acct.id),
                ).all(),
            )
            lines.append(
                f"{acct.id:>3}  {acct.name:<30}  {acct.type:<15}  "
                f"{acct.currency:<10}  {count:>12}",
            )
        return "\n".join(lines)

    logger.error("list_accounts: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Agent instance
# ---------------------------------------------------------------------------

bookkeeper_agent = Agent(
    create_agent_model("bookkeeper"),
    system_prompt=(
        "You are a bookkeeper agent specialised in financial management.\n"
        "You can categorise transactions, list transactions, get transaction stats, "
        "and show the chart of accounts.\n"
        "When asked to list, show, or view data — output the raw tool result directly. "
        "Do NOT say 'a table has been printed' or rephrase the data. "
        "Always confirm before making changes."
    ),
    deps_type=BookkeeperDeps,
    defer_model_check=True,
)

bookkeeper_agent.tool(categorise_transaction)
bookkeeper_agent.tool(list_transactions)
bookkeeper_agent.tool(get_transaction_stats)
bookkeeper_agent.tool(list_accounts)
