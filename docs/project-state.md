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
| `docs/plan/ingestion/bank-feed-ingestion.md` | ~106 | Active — CSV-first bank feed ingestion (partial imports + Plaid/AA future) |
| `docs/plan/data/archive/data-models-next.md` | ~240 | ✅ Archived — Phase 2 data models |
| `src/util/config.py` | 25 | Config: DB path, data dir, config dir |
| `src/data/models.py` | 100+ | SQLModel definitions: Account, Transaction, ConversationMessage, AppConfig, GLAccount, Vendor, Customer, Invoice, InvoiceLineItem, Bill, BillLineItem, CategoryRule |
| `src/data/seed.py` | 30 | Default chart of accounts seeding (19 GL accounts) |
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
| `tests/test_db.py` | 149 | Existing tests for models and DB |

---

## Key Functions

| Function | Description |
|----------|-------------|
| **Config** | |
| `get_config_dir()` | Returns XDG-compliant config directory |
| `get_data_dir()` | Returns XDG-compliant data directory |
| `get_db_path()` | Returns path to SQLite DB, creates data dir if needed |
| **Seed** | |
| `seed_gl_accounts(engine)` | Seeds 19 default GLAccount rows; idempotent (no-op if table non-empty) |
| **DB** | |
| `get_engine(db_path)` | Creates SQLAlchemy engine for SQLite |
| `init_db(db_path)` | Creates all tables via SQLModel metadata |
| `get_session(db_path)` | Yields a SQLModel Session (context manager) |
| **Models** | |
| `ConversationMessage` | SQLModel table: id, conversation_id, role, content, created_at |
| `GLAccount` | Chart of Accounts: code, name, type, parent_id, is_active |
| `Vendor` | Payable counterparty: name, gstin, email, phone |
| `Customer` | Receivable counterparty: name, gstin, email, phone |
| `Invoice` / `InvoiceLineItem` | Sales invoice with cascading line items |
| `Bill` / `BillLineItem` | Vendor bill with cascading line items |
| `CategoryRule` | Auto-categorisation rule: pattern → gl_account_id |
| `Transaction.compute_hash(date, desc, amount)` | SHA-256 dedup hash |
| `Transaction.gl_account_id` | New nullable FK to GLAccount (what-for) |
| `Transaction.invoice_id` | New nullable FK to Invoice (payment reconciliation) |
| `Transaction.bill_id` | New nullable FK to Bill (payment reconciliation) |
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
| **Bookkeeper Agent — New Tools (Phase 2)** | |
| `list_gl_accounts(acct_type)` | List chart of accounts, filtered by type |
| `auto_categorise(tx_id)` | Auto-categorise by CategoryRule pattern matching |
| `list_vendors(query)` | Search vendors by name |
| `add_vendor(name, gstin, email, phone)` | Create vendor |
| `list_customers(query)` | Search customers by name |
| `add_customer(name, gstin, email, phone)` | Create customer |
| `list_invoices(status)` | List invoices by status |
| `show_invoice(id)` | Full invoice details with line items |
| `list_bills(status)` | List bills by status |
| `show_bill(id)` | Full bill details with line items |
| `link_to_invoice(tx_id, invoice_id)` | Reconcile transaction to invoice |
| `link_to_bill(tx_id, bill_id)` | Reconcile transaction to bill |
| `find_unreconciled_transactions(limit)` | List transactions not yet matched to invoice/bill |
| `suggest_matches(tx_id)` | Score and suggest candidate invoices/bills for a transaction |
| `confirm_match(tx_id, doc_id, doc_type)` | Confirm match and update paid_amount on invoice/bill |

---

## Key Files (continued)

| File | Lines | Purpose |
|------|-------|---------|
| `docs/plan/agents/bookkeeper-reconciliation.md` | ~27 | Active plan — Reconciliation tools added to bookkeeper agent |
| `docs/plan/agents/archive/orchestrator-bookkeeper.md` | ~67 | ✅ Archived — Orchestrator + Bookkeeper agents |
| `docs/plan/agents/archive/orchestrator-agent-delegation.md` | ~103 | ✅ Archived — Sub-agent delegation pattern |
| `docs/plan/agents/archive/bookkeeper-upgrade.md` | ~50 | ✅ Archived — Bookkeeper upgrade (full data model access) |
| `docs/work/orchestrator-bookkeeper.md` | — | Work tracking file for agents |
| `src/agents/__init__.py` | 7 | Logging config (basicConfig, INFO level) |
| `src/agents/settings.py` | 55 | LLM model config: `AUTOFI_LLM_MODEL`, per-agent `AUTOFI_{AGENT}_MODEL` env vars, API key resolution |
| `src/agents/bookkeeper.py` | ~220 | Bookkeeper Pydantic AI agent with DB-backed tools (GL accounts, vendors, customers, invoices, bills, reconciliation) |
| `src/agents/orchestrator.py` | 65 | Orchestrator Pydantic AI agent with registry-based delegation to sub-agents |
| `src/agents/registry.py` | 75 | Agent registry (`OrchestratorDeps`, `AgentEntry`, `register_agent()`, `_make_delegation_tool()`, `wire_orchestrator_tools()`) |
| `src/cli/chat.py` | 106 | `autofi chat` CLI command (single-turn + interactive REPL) |
| `src/cli/setup.py` | 200 | `autofi setup` — interactive LLM model + API key configuration |
| `src/data/config.py` | 36 | AppConfig key-value store helpers |
| `src/util/crypto.py` | 56 | Fernet encrypt/decrypt with PBKDF2 key derivation |
| `tests/test_bookkeeper_tools.py` | ~480 | Unit tests for bookkeeper tools (GL accounts, auto-categorise, vendors, customers, invoices, bills, reconciliation, match suggestions) |
| `tests/test_orchestrator.py` | 75 | Unit tests for orchestrator delegation (TestModel, multi-turn) |
| `src/test/test_csv_parser.py` | 217 | Unit tests for CSV parser (all 4 formats, BOM, edge cases) |
| `src/test/test_ingestion.py` | 139 | Unit tests for ingestion service (dedup, dry-run, stats, filters) |
| `src/test/test_db.py` | 524 | Unit tests for all SQLModel models (CRUD, FKs, cascades, seeding, reconciliation) |
| `src/test/test_cli.py` | ~200 | Unit tests for CLI commands (import, list, add-account, tx show, tx stats) |

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
