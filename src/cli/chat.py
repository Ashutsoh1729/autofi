import logging
from typing import Any

import click
from pydantic_ai import Agent

from agents.orchestrator import _default_deps, orchestrator_agent
from data.db import get_session, init_db

from data.models import ConversationMessage, new_conversation_id

from util.config import get_db_path

logger = logging.getLogger(__name__)


def _store_message(conv_id: str, role: str, content: str) -> None:
    db_path = get_db_path()
    init_db(db_path)
    for session in get_session(db_path):
        msg = ConversationMessage(
            conversation_id=conv_id,
            role=role,
            content=content,
        )
        session.add(msg)
        session.commit()


def _run_agent(
    agent: Agent[Any, Any],
    question: str,
    message_history: list | None = None,
) -> tuple[str, list]:
    deps = _default_deps()
    result = agent.run_sync(
        question,
        deps=deps,
        message_history=message_history,
    )
    return result.output, result.new_messages()


@click.command()
@click.argument("question", required=False)
@click.option("--interactive", "-i", is_flag=True, help="Interactive REPL mode")
def chat(question: str | None, interactive: bool):
    """Chat with the AutoFi financial assistant.

    Ask natural-language questions about your finances.

    Examples:

        autofi chat "Show my recent transactions"

        autofi chat "Categorise transaction 5 as Food"

        autofi chat --interactive
    """
    if interactive:
        _repl()
        return

    if not question:
        click.echo("Usage: autofi chat <question>  or  autofi chat --interactive")
        return

    conv_id = new_conversation_id()
    _store_message(conv_id, "user", question)

    message_history: list | None = None
    current_question = question

    try:
        while True:
            click.echo()
            click.echo("⏳ AutoFi is thinking...", nl=False)
            logger.info("Chat request: %s", current_question)
            answer, messages = _run_agent(
                orchestrator_agent,
                current_question,
                message_history=message_history,
            )
            message_history = messages
            _store_message(conv_id, "agent", answer)
            click.echo("\r" + " " * 60 + "\r", nl=False)
            click.echo(answer)

            follow_up = click.prompt(
                "\nFollow-up (or press Enter to finish)",
                default="",
                show_default=False,
            )
            if not follow_up.strip():
                break

            _store_message(conv_id, "user", follow_up)
            current_question = follow_up
    except Exception as exc:
        logger.error("Chat failed: %s", exc)
        msg = str(exc)
        # Extract user-friendly message from pydantic-ai HTTP errors
        if "status_code:" in msg and "body:" in msg:
            import re
            match = re.search(r"body: (.+)", msg)
            if match:
                import json
                try:
                    body = json.loads(match.group(1).replace("'", '"'))
                    err_msg = body.get("error", {}).get("message", msg)
                except Exception:
                    err_msg = msg
            else:
                err_msg = msg
        else:
            err_msg = msg
        click.echo(f"Error: {err_msg}", err=True)
        raise click.Abort()


def _repl() -> None:
    """Multi-turn interactive REPL."""
    conv_id = new_conversation_id()
    message_history: list | None = None
    click.echo("AutoFi Chat — interactive mode. Type '/exit' to quit.")
    click.echo()

    while True:
        try:
            user_input = click.prompt("You", prompt_suffix="> ")
        except (EOFError, click.Abort):
            break

        if user_input.strip().lower() in ("/exit", "/quit", "/q"):
            break
        if not user_input.strip():
            continue

        _store_message(conv_id, "user", user_input)
        try:
            logger.info("Interactive chat: %s", user_input)
            answer, message_history = _run_agent(
                orchestrator_agent,
                user_input,
                message_history=message_history,
            )
            _store_message(conv_id, "agent", answer)
            click.echo(f"AutoFi> {answer}")
        except Exception as exc:
            logger.error("Chat error: %s", exc)
            click.echo(f"Error: {exc}")
