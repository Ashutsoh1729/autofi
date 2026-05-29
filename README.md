# AutoFi

**Autonomous financial operations for SMBs.**

AutoFi is an AI-powered system that ingests bank transactions, categorises them, and manages financial operations — bookkeeping, reconciliations, cash flow forecasting, compliance tracking, and reporting — through a chat interface. Think of it as an autonomous team of AI agents (Bookkeeper, Reconciler, Forecaster, etc.) coordinated by an Orchestrator agent that you talk to.

---

## Status

| Layer | Status |
|-------|--------|
| CSV ingestion | ✅ Done |
| Transaction storage & queries | ✅ Done |
| Duplicate detection | ✅ Done |
| CLI (`bank import`, `tx list`, etc.) | ✅ Done |
| `autofi setup` (interactive LLM config) | ✅ Done |
| Agent system (Orchestrator + Bookkeeper) | ✅ Done |
| Chat interface (`autofi chat`) | ✅ Done |

---

## Quick Start

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) (package manager)

### Setup

```sh
git clone <repo-url> && cd autofi
uv sync
```

### Import transactions

```sh
# Import a bank CSV
uv run autofi bank import path/to/statement.csv

# Dry-run to preview without writing
uv run autofi bank import path/to/statement.csv --dry-run
```

### Query transactions

```sh
# List recent transactions
uv run autofi tx list

# Filter by account, date range, or limit
uv run autofi tx list --account-id 1 --days 30 --limit 10

# Show full details
uv run autofi tx show <id>

# Summary statistics
uv run autofi tx stats
```

### Configure LLM

```sh
# Interactive wizard: pick provider, model, enter API key
uv run autofi setup
```

### Chat with AI agents

```sh
# Single-turn query
uv run autofi chat "How much did I spend on groceries last month?"

# Interactive REPL
uv run autofi chat -i
```

### Manage accounts

```sh
uv run autofi bank list
uv run autofi bank add-account "My Account" --type savings --currency USD
```

---

## Supported Bank Formats

| Format | Detected By |
|--------|-------------|
| HDFC | `Narration`, `Withdrawal Amt.(INR)` / `Deposit Amt.(INR)` |
| HDFC (alt) | `Narration`, `Withdrawal Amount` / `Deposit Amount` |
| Chase | `Transaction Date`, `Amount` or `Details`, `Amount`, `Type` |
| Generic | `Date`, `Description`, `Amount` |
| Generic (debit/credit) | `Date`, `Description`, `Debit`, `Credit` |

CSV files with BOM, quoted fields, commas in amounts, empty rows, and currency symbols are handled automatically.

---

## Architecture

```
┌──────────────────────┐
│     User (Chat/CLI)   │
└─────────┬────────────┘
          │
┌─────────▼────────────┐
│  Orchestrator Agent   │  (LLM-powered router)
│  ┌────────────────┐   │
│  │ Agent Registry  │   │  auto-wires delegation tools
│  └──┬───┬───┬─────┘   │
└─────┼───┼───┼─────────┘
      │   │   │
      ▼   ▼   ▼
   BK   RC   FC  ...   (specialist agents)
                         each with own model + tools
      │
      ▼
┌────────────────┐
│   Data Layer    │
│  (SQLite +       │
│   SQLModel)      │
└────────────────┘
```

- **Orchestrator** is the only agent that talks to the user
- **Agent Registry** in `src/agents/registry.py` auto-discovers and wires specialist agents as delegation tools
- Each specialist agent (Bookkeeper, etc.) exposes typed Python **tools** backed by the DB layer
- Per-agent model selection via `AUTOFI_{AGENT}_MODEL` env vars or DB-backed config
- All agent actions are logged in the `ConversationMessage` table for audit

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python >= 3.13 |
| Package manager | `uv` |
| CLI framework | `click` |
| ORM / DB | `sqlmodel` (SQLite) |
| Agent framework | `pydantic-ai` |
| LLM providers | Anthropic, OpenAI, Gemini, Groq, OpenRouter (via env var or `autofi setup`) |
| Encryption | `cryptography` (Fernet + PBKDF2 for API key storage) |

---

## Project Structure

```
autofi/
├── main.py                  # CLI entry point
├── pyproject.toml           # Dependencies & package config
├── src/
│   ├── cli/                 # Click CLI commands
│   │   ├── main.py          # Root `autofi` group
│   │   ├── bank.py          # `bank import`, `bank list`, `bank add-account`
│   │   ├── transactions.py  # `tx list`, `tx show`, `tx stats`
│   │   ├── chat.py          # `chat` command (single-turn + interactive REPL)
│   │   └── setup.py         # `setup` command (interactive LLM config)
│   ├── agents/              # AI agents
│   │   ├── __init__.py      # Logging config
│   │   ├── orchestrator.py  # Orchestrator agent (LLM-powered router)
│   │   ├── bookkeeper.py    # Bookkeeper agent with DB tools
│   │   ├── registry.py      # Agent registry & delegation tool factory
│   │   ├── settings.py      # Per-agent model selection & API key resolution
│   │   └── memory/          # (future) conversation memory
│   ├── data/                # Database layer
│   │   ├── models.py        # Account, Transaction, ConversationMessage, AppConfig
│   │   ├── db.py            # Engine, sessions, init
│   │   └── config.py        # AppConfig key-value store helpers
│   └── util/                # Utilities
│       ├── config.py        # XDG paths, env vars
│       ├── csv_parser.py    # Format detection & parsing
│       ├── bank_feed_ingestion.py  # Import, dedup, stats
│       └── crypto.py        # Fernet encryption for API key storage
├── docs/
│   ├── SPEC.md              # Full spec & agent roles
│   ├── project-state.md     # Current project reference
│   ├── release-plan.md      # Publishing plan
│   ├── plan/                # Feature plans
│   ├── work/                # Work tracking
│   ├── research/            # Research docs
│   └── test/                # Test results
├── src/test/                # Legacy test suites
│   ├── test_csv_parser.py   # CSV parser (23 tests)
│   ├── test_db.py           # Models & DB (7 tests)
│   └── test_ingestion.py    # Ingestion (13 tests)
└── tests/                   # Current test suites
    ├── test_bookkeeper_tools.py  # Bookkeeper agent tools (6 tests)
    └── test_orchestrator.py      # Orchestrator delegation (3 tests)
```

---

## Development

```sh
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint
uv run ruff check
```

---

## Vision

Inspired by [Balance](https://getbalance.ai/), AutoFi aims to be an autonomous team of AI agents that collectively manages the full financial operations of a small-to-medium business:

1. **Ingest** — bank statements, invoices, bills, payroll data
2. **Organise** — categorise, reconcile, maintain books
3. **Forecast** — cash flow projections, what-if scenarios
4. **Comply** — track filing deadlines, flag anomalies
5. **Report** — P&L, balance sheet, board-ready dashboards

The user interacts via chat to ask questions, approve actions, or review summaries. Agents coordinate behind the scenes.

---

## License

MIT
