# Project State

## Overview

Autonomous AI agent system for SMB financial operations. Currently implementing bank feed ingestion (CSV-first approach).

## Architecture

```
┌──────────────────────┐
│   CLI (Click)        │
│   autofi bank / tx   │
└──────┬───────────────┘
       │
┌──────▼───────────────┐
│  Ingestion Service   │
│  (bank_feed_ingestion)│
└──────┬───────────────┘
       │
┌──────▼───────────────┐
│  SQLite (SQLModel)   │
│  accounts + txs      │
└──────────────────────┘
```

---

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `docs/plan/ingestion/bank-feed-ingestion.md` | ~110 | Active plan for CSV-first bank feed ingestion |
| `src/util/config.py` | 25 | Config: DB path, data dir, config dir |
| `src/data/models.py` | 30 | SQLModel definitions: Account, Transaction |
| `src/data/db.py` | 20 | DB engine + session helper |
| `src/util/csv_parser.py` | 217 | CSV format detection, parsing, RawTransaction |
| `src/util/bank_feed_ingestion.py` | 154 | Ingestion: import_csv, list, stats, dedup |
| `src/cli/main.py` | 12 | Root `autofi` Click group, registers bank + tx |
| `src/cli/bank.py` | 59 | CLI: `bank import`, `bank list`, `bank add-account` |
| `src/cli/transactions.py` | 59 | CLI: `tx list`, `tx show`, `tx stats` |
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
| `Transaction.compute_hash(date, desc, amount)` | SHA-256 dedup hash |
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

## Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI framework |
| `python-dateutil` | Flexible date parsing for CSVs |
| `sqlmodel` | ORM for SQLite (built on SQLAlchemy + Pydantic) |

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `XDG_CONFIG_HOME` | Override config directory (default: `~/.config`) |
| `XDG_DATA_HOME` | Override data directory (default: `~/.local/share`) |

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
