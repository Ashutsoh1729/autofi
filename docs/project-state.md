# Project State

## Overview

Autonomous AI agent system for SMB financial operations. Currently implementing bank feed ingestion (CSV-first approach).

## Architecture

```
┌──────────────────────────────────┐
│   CLI (Click)                    │
│   autofi bank / tx / chat       │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Orchestrator (Pydantic AI)     │
│  model: claude / gpt / gemini   │
│                                 │
│  Delegation tools (auto-wired)  │
│   ┌─ bookkeeper(task) ───────┐ │
│   │  → BookkeeperAgent       │ │
│   │    (own model + deps)    │ │
│   └──────────────────────────┘ │
│   ┌─ reconciler(task) ──────┐ │  ← future
│   │  → ReconcilerAgent       │ │
│   └──────────────────────────┘ │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  Ingestion Service               │
│  (bank_feed_ingestion)           │
└──────────────┬───────────────────┘
               │
┌──────────────▼───────────────────┐
│  SQLite (SQLModel)               │
│  accounts + txs + conversation   │
└──────────────────────────────────┘
```

---

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `docs/plan/ingestion/bank-feed-ingestion.md` | ~110 | Active plan for CSV-first bank feed ingestion |
| `src/util/config.py` | 25 | Config: DB path, data dir, config dir |
| `src/data/models.py` | 50 | SQLModel definitions: Account, Transaction, ConversationMessage, AppConfig |
| `src/data/db.py` | 20 | DB engine + session helper |
| `src/data/config.py` | 36 | **NEW** — AppConfig key-value helpers: `get_setting`, `set_setting`, `delete_setting` |
| `src/util/csv_parser.py` | 217 | CSV format detection, parsing, RawTransaction |
| `src/util/bank_feed_ingestion.py` | 154 | Ingestion: import_csv, list, stats, dedup |
| `src/util/crypto.py` | 56 | **NEW** — Fernet-based encrypt/decrypt with PBKDF2 key derivation |
| `src/cli/main.py` | 18 | Root `autofi` Click group, registers bank + tx + chat + setup |
| `src/cli/bank.py` | 59 | CLI: `bank import`, `bank list`, `bank add-account` |
| `src/cli/transactions.py` | 59 | CLI: `tx list`, `tx show`, `tx stats` |
| `src/cli/setup.py` | 200 | **NEW** — Interactive `autofi setup` for LLM model + API key config |
| `main.py` | 4 | CLI entry point — calls `autofi()` |
| `tests/test_csv_parser.py` | 217 | Unit tests for CSV parser (all 4 formats) |
| `tests/test_ingestion.py` | 150 | Unit tests for ingestion (dedup, dry-run, stats) |
| `tests/test_db.py` | 149 | Existing tests for models and DB |

---

## Key Functions

| Function | Description |
|----------|-------------|
| **Config** | |
| `get_config_dir()` | Returns XDG-compliant config directory |
| `get_data_dir()` | Returns XDG-compliant data directory |
| `get_db_path()` | Returns path to SQLite DB, creates data dir if needed |
| **DB** | |
| `get_engine(db_path)` | Creates SQLAlchemy engine for SQLite |
| `init_db(db_path)` | Creates all tables via SQLModel metadata |
| `get_session(db_path)` | Yields a SQLModel Session (context manager) |
| **Models** | |
| `ConversationMessage` | SQLModel table: id, conversation_id, role, content, created_at |
| `Transaction.compute_hash(date, desc, amount)` | SHA-256 dedup hash |
| **Agent Registry** | |
| `register_agent(name, entry)` | Register a specialist agent with deps factory |
| `wire_orchestrator_tools(orchestrator_agent)` | Auto-generate delegation tools for all registered agents |
| `_make_delegation_tool(name, entry)` | Build a tool function that calls `entry.agent.run_sync()` at runtime |
| `get_model_for_agent(name)` | Read per-agent model from DB → `AUTOFI_{NAME}_MODEL` → default |
| `create_agent_model(name)` | **NEW** — Build Model instance with API key injection (DB → env) |
| `resolve_api_key(provider)` | **NEW** — Resolve API key from DB (decrypted) → env var |
| **Encryption** | |
| `encrypt_value(plaintext)` | Encrypt string with Fernet + PBKDF2-derived local key |
| `decrypt_value(token)` | Decrypt Fernet token back to plaintext |
| **AppConfig DB** | |
| `get_setting(db_path, key)` | Read setting from AppConfig table |
| `set_setting(db_path, key, value)` | Upsert setting into AppConfig table |
| `delete_setting(db_path, key)` | Delete setting from AppConfig table |
| **Setup CLI** | |
| `autofi setup` | Interactive wizard: pick provider → model → enter API key → save encrypted |
| **CSV Parser** | |
| `detect_format(headers)` | Auto-detect bank format by column headers |
| `parse_csv(filepath)` | Parse CSV into list of RawTransaction |
| `_build_column_map(headers)` | Map canonical names to CSV columns |
| **Ingestion Service** | |
| `import_csv(filepath, account_id, dry_run)` | Parse, dedup, insert CSV — returns ImportResult |
| `list_transactions(account_id, days, limit)` | Query transactions with filters |
| `get_transaction_stats()` | Total count, per-account counts, date range |
| **CLI Commands** | |
| `autofi bank import <csv>` | Import CSV (--account-id, --dry-run) |
| `autofi bank list` | List accounts with tx counts |
| `autofi bank add-account <name>` | Create new account (--type, --currency) |
| `autofi tx list` | List transactions (--account-id, --days, --limit) |
| `autofi tx show <id>` | Full transaction details |
| `autofi tx stats` | Summary counts and date range |

---

## Key Files (continued)

| File | Lines | Purpose |
|------|-------|---------|
| `docs/plan/agents/orchestrator-bookkeeper.md` | ~67 | Active plan for Orchestrator + Bookkeeper agents |
| `docs/work/orchestrator-bookkeeper.md` | — | Work tracking file for agents |
| `src/agents/__init__.py` | 7 | Logging config (basicConfig, INFO level) |
| `src/agents/settings.py` | 55 | LLM model config: `AUTOFI_LLM_MODEL`, per-agent `AUTOFI_{AGENT}_MODEL` env vars, API key resolution |
| `src/agents/bookkeeper.py` | 190 | Bookkeeper Pydantic AI agent with DB-backed tools |
| `src/agents/orchestrator.py` | 65 | Orchestrator Pydantic AI agent with registry-based delegation to sub-agents |
| `src/agents/registry.py` | 75 | Agent registry (`OrchestratorDeps`, `AgentEntry`, `register_agent()`, `_make_delegation_tool()`, `wire_orchestrator_tools()`) |
| `src/cli/chat.py` | 106 | `autofi chat` CLI command (single-turn + interactive REPL) |
| `src/cli/setup.py` | 200 | `autofi setup` — interactive LLM model + API key configuration |
| `src/data/config.py` | 36 | AppConfig key-value store helpers |
| `src/util/crypto.py` | 56 | Fernet encrypt/decrypt with PBKDF2 key derivation |
| `tests/test_bookkeeper_tools.py` | 140 | Unit tests for bookkeeper tools (in-memory SQLite + TestModel) |
| `tests/test_orchestrator.py` | 75 | Unit tests for orchestrator delegation (TestModel, multi-turn) |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI framework |
| `python-dateutil` | Flexible date parsing for CSVs |
| `sqlmodel` | ORM for SQLite (built on SQLAlchemy + Pydantic) |
| `pydantic-ai` | Agent framework (model-agnostic LLM agent with type-safe tools) |
| `cryptography` | Fernet symmetric encryption for API key storage |

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `XDG_CONFIG_HOME` | Override config directory (default: `~/.config`) |
| `XDG_DATA_HOME` | Override data directory (default: `~/.local/share`) |
| `AUTOFI_LLM_MODEL` | Default LLM model string for all agents (default: `anthropic:claude-sonnet-4-20250514`) |
| `AUTOFI_ORCHESTRATOR_MODEL` | Override model for the orchestrator agent |
| `AUTOFI_BOOKKEEPER_MODEL` | Override model for the bookkeeper agent |
| `ANTHROPIC_API_KEY` | API key for Anthropic Claude models |
| `OPENAI_API_KEY` | API key for OpenAI models |
| `GOOGLE_API_KEY` | API key for Google Gemini models |
| `GROQ_API_KEY` | API key for Groq models |
| `OPENROUTER_API_KEY` | API key for OpenRouter models |

---

## API Endpoints

| Method | Path | Description |
|-------|------|-------------|
| | | |

---

## Workflow

1. User exports CSV from bank
2. CSV parsed into canonical format
3. Transactions deduped by content hash
4. New rows inserted into SQLite via SQLModel
5. User queries via CLI (`autofi tx list`, etc.)
