import click
from cli.bank import bank

from cli.transactions import tx


@click.group()
def autofi():
    """Autonomous financial operations CLI."""


autofi.add_command(bank)
autofi.add_command(tx)
