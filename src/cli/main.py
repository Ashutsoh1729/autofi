import click
from cli.bank import bank

from cli.chat import chat

from cli.setup import setup
from cli.transactions import tx


@click.group()
def autofi():
    """Autonomous financial operations CLI."""


autofi.add_command(bank)
autofi.add_command(tx)
autofi.add_command(chat)
autofi.add_command(setup)
