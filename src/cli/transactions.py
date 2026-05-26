import click

from data.db import get_session, init_db

from data.models import Transaction

from util.bank_feed_ingestion import get_transaction_stats, list_transactions

from util.config import get_db_path


@click.group()
def tx():
    """Query and manage transactions."""


@tx.command(name="list")
@click.option("--account-id", type=int, default=None, help="Filter by account ID")
@click.option("--days", type=int, default=None, help="Show transactions from last N days")
@click.option("--limit", type=int, default=100, help="Max transactions to show")
def list_cmd(account_id: int | None, days: int | None, limit: int):
    """List recent transactions."""
    txs = list_transactions(account_id=account_id, days=days, limit=limit)
    if not txs:
        click.echo("No transactions found.")
        return
    for t in txs:
        click.echo(
            f"{t.id:>5}  {t.date}  {t.description:<50}  {t.amount:>10.2f}  {t.currency}"
        )


@tx.command(name="show")
@click.argument("tx_id", type=int)
def show_cmd(tx_id: int):
    """Show full details of a single transaction."""
    db_path = get_db_path()
    init_db(db_path)
    session: object
    for session in get_session(db_path):
        t = session.get(Transaction, tx_id)
        if t is None:
            click.echo(f"Transaction {tx_id} not found.")
            return
        click.echo(f"ID:          {t.id}")
        click.echo(f"Account ID:  {t.account_id}")
        click.echo(f"Date:        {t.date}")
        click.echo(f"Description: {t.description}")
        click.echo(f"Amount:      {t.amount:.2f} {t.currency}")
        click.echo(f"Category:    {t.category or '—'}")
        click.echo(f"Notes:       {t.notes or '—'}")
        click.echo(f"Hash:        {t.hash}")
        click.echo(f"Created:     {t.created_at}")


@tx.command(name="stats")
def stats_cmd():
    """Show transaction statistics."""
    stats = get_transaction_stats()
    click.echo(f"Total transactions: {stats['total_transactions']}")
    click.echo("Per account:")
    for name, count in stats["per_account"].items():
        click.echo(f"  {name}: {count}")
    if stats["date_range"]:
        click.echo(f"Date range: {stats['date_range']}")
