import click

from data.db import get_session, init_db

from data.models import Account, Transaction

from util.bank_feed_ingestion import import_csv

from util.config import get_db_path
from sqlmodel import select


@click.group()
def bank():
    """Manage bank accounts and import transactions."""


@bank.command()
@click.argument("csv_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--account-id", type=str, default=None, help="Target account ID")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without writing")
def import_cmd(csv_file: str, account_id: str | None, dry_run: bool):
    """Import transactions from a CSV file."""
    try:
        result = import_csv(csv_file, account_id=account_id, dry_run=dry_run)
        click.echo(f"Account: {result.account_name} (id={result.account_id})")
        click.echo(f"Imported: {result.imported}")
        click.echo(f"Skipped (duplicates): {result.skipped}")
        if result.errors:
            click.echo("Errors:")
            for row, msg in result.errors:
                click.echo(f"  Row {row}: {msg}")
        if dry_run:
            click.echo("(dry run — no data written)")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@bank.command(name="list")
def list_accounts():
    """List all bank accounts with transaction counts."""
    db_path = get_db_path()
    init_db(db_path)
    session: object
    for session in get_session(db_path):
        accounts = session.exec(select(Account).order_by(Account.name)).all()
        if not accounts:
            click.echo("No accounts found.")
            return
        for acct in accounts:
            count = len(
                session.exec(
                    select(Transaction).where(Transaction.account_id == acct.id)
                ).all()
            )
            click.echo(f"{acct.id}: {acct.name} ({acct.type}, {acct.currency}) — {count} transactions")


@bank.command(name="add-account")
@click.argument("name")
@click.option("--type", "acct_type", default="checking", help="Account type (checking, savings, credit_card)")
@click.option("--currency", default="INR", help="Currency code")
def add_account(name: str, acct_type: str, currency: str):
    """Manually add a new bank account."""
    db_path = get_db_path()
    init_db(db_path)
    session: object
    for session in get_session(db_path):
        acct = Account(name=name, type=acct_type, currency=currency)
        session.add(acct)
        session.commit()
        session.refresh(acct)
        click.echo(f"Created account: {acct.id} — {acct.name} ({acct.type}, {acct.currency})")
