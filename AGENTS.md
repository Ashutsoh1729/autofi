# AGENTS.md - Project Guidelines

This file provides guidelines for AI agents working in this repository.

## Project Overview

[Brief description of the project]

## Tech Stack

- **Project Type**: Python CLI
- **Package Manager**: `uv` (use `uv add`, `uv sync`, `uv run`, `uv tool`)
- **CLI Framework**: `click`
- **ORM / DB**: `sqlmodel` (SQLite via SQLAlchemy)
- **Python**: >=3.13

---

## Build / Lint / Test Commands

- `uv sync` — install dependencies
- `uv add <package>` — add a dependency
- `uv run python main.py` — run the CLI
- `uv run pytest` — run tests
- `uv run ruff check` — lint


---

## Conventions

- Use `uv` for all package management (never pip/poetry/pipenv)
- Use `sqlmodel` for DB — models in `src/data/models.py`, session helpers in `src/data/db.py`
- CLI commands via `click` groups in `src/cli/`

## Code Style Guidelines

### Styling
- 4 spaces Python indentation
- Max line length: 100 characters
- Use trailing commas in multi-line structures

### Naming
- Files: `snake_case.py`
- Functions: `snake_case`
- Classes: `PascalCase`

### Error Handling
- Always log errors before raising
- Never swallow exceptions silently

---

## Key Principles

1. **Read project-state.md first** - Before exploring or modifying code
2. **Keep project-state.md updated** - After any code changes
3. **Be specific** - Each task should be actionable and verifiable
