# Bank Feed Ingestion (CSV First)

## Description
Build the bank feed ingestion pipeline starting with **manual CSV import**. Users export transactions from their bank as CSV and import them via CLI. This gets the data flowing immediately without any third-party API dependency. Plaid / Account Aggregator integration can be layered on later.

## Goals
- Parse CSV exports from common Indian/US bank formats
- Store transactions and accounts in local SQLite
- Detect and skip duplicate imports
- Provide CLI commands for importing, listing, and managing transactions
- Model accounts and transactions per the spec's data model (Phase 1 compatible)
- Keep the architecture ready for Plaid/AA integration later

## Future: Plaid / India AA Integration
Once CSV ingestion is stable, add automated bank feed support:
- **US**: Plaid API wrapper (`src/util/plaid_client.py`) with Link token flow and `/transactions/sync`
- **India**: Account Aggregator framework integration via a registered AA (e.g. Finvu, CAMS Finserv)
- Both feed into the same `transactions` and `accounts` tables

## Implementation Steps

### Step 1: Project Setup & Dependencies
- [x] Add deps with `uv add click python-dateutil sqlmodel`
- [x] Create config module at `src/util/config.py` (DB path, etc.)
- [x] Define SQLModel models in `src/data/models.py` — tables auto-created via `SQLModel.metadata.create_all()`

### Step 2: Data Model (SQLModel)
- [x] Create `src/data/models.py` with SQLModel table definitions:
  - `Account` — bank accounts (id, name, type, currency, created_at)
  - `Transaction` — individual transactions (id, account_id, date, description, amount, currency, category, notes, hash, created_at)
- [x] Use a content hash of (date, description, amount) as a dedup key on `Transaction`
- [x] Add `__table_args__` unique constraint on `Transaction.hash` *(via `Field(unique=True)` — equivalent)*
- [x] Create `src/data/db.py` with `get_session(db_path)` helper using `create_engine` + `Session`

### Step 3: CSV Parser
- [x] Create `src/util/csv_parser.py` with:
  - `detect_format(headers: list[str]) -> CSVFormat` — auto-detect bank format by column headers
  - `parse_csv(filepath: str) -> list[RawTransaction]` — parse CSV into a canonical form
- [x] Support at least 3 common formats:
  - **Generic**: columns like `Date`, `Description`, `Amount`, `Debit`, `Credit`
  - **HDFC Bank**: standard Indian bank export format
  - **Chase / US Bank**: common US format with `Transaction Date`, `Description`, `Amount`
- [x] Normalise: map all formats to (date, description, amount, currency, type)
- [x] Handle edge cases: BOM in CSV, quoted fields, commas in amounts, empty rows, headers with spaces

### Step 4: Ingestion Service
- [x] Create `src/util/bank_feed_ingestion.py` implementing:
  - `import_csv(filepath: str, account_id: str | None = None) -> ImportResult` — parse CSV, dedup against existing, insert new rows, return summary (imported, skipped, errors)
  - `list_transactions(account_id: str | None, days: int | None, limit: int) -> list[Transaction]`
  - `get_transaction_stats() -> dict` — total count, per-account counts, date range
- [x] Compute a deterministic hash per row for dedup
- [x] Support `--dry-run` flag to show what would be imported without writing
- [x] Use SQLModel sessions for all DB operations (no raw SQL)

### Step 5: CLI Root Command & Groups
- [x] Create root CLI group `autofi` in `src/cli/main.py` via `@click.group()`
- [x] Create `src/cli/bank.py` with `@bank.group()`:
  - `autofi bank import <csv-file> [--account-id] [--dry-run]` — import CSV, auto-create account if needed
  - `autofi bank list` — list accounts with transaction counts and date ranges
  - `autofi bank add-account <name> [--type] [--currency]` — manually add an account
- [x] Create `src/cli/transactions.py` with `@tx.group()`:
  - `autofi tx list [--account-id] [--days N] [--limit]` — list transactions
  - `autofi tx show <tx-id>` — show full transaction details
  - `autofi tx stats` — summary counts and date range
- [x] Register both sub-groups (`bank`, `tx`) onto the root `autofi` group in `src/cli/main.py`
- [x] Root `main.py` imports `autofi` group from `src/cli/main.py` and calls `autofi()` as entry point

### Step 6: Validation & Error Handling
- [x] Validate CSV structure before parsing (non-empty, valid headers)
- [x] Report per-row errors with line numbers (e.g. unparseable date, negative amount)
- [ ] Handle partial imports: import valid rows, report invalid rows, don't roll back valid ones *(current implementation rolls back entire batch on any error)*

### Step 7: Testing
- [x] Write unit tests for CSV parser with sample CSVs for each supported format (`src/test/test_csv_parser.py`)
- [x] Write unit tests for ingestion service (dedup, dry-run, stats) (`src/test/test_ingestion.py`)
- [x] Write unit tests for CLI commands (invoke Click runner, assert output) (`src/test/test_cli.py`)
- [x] Test with real CSV exports from HDFC, Chase, and a generic format (inline samples in test_csv_parser.py)

### Step 8: Future — Plaid Integration (not yet)
- [ ] When ready: create `src/util/plaid_client.py` — Plaid API wrapper
- [ ] When ready: create `src/util/aa_client.py` — India Account Aggregator client
- [ ] Both write into the same `transactions` table, reusing the CSV workflow's schema

## Files to Modify
- `pyproject.toml` — deps managed via `uv add` (no manual editing)
- `src/util/config.py` — NEW: configuration loader
- `src/util/csv_parser.py` — NEW: CSV format detection and parsing
- `src/util/bank_feed_ingestion.py` — implement ingestion service (was empty stub)
- `src/data/models.py` — NEW: SQLModel table definitions
- `src/data/db.py` — NEW: DB engine + session helper
- `src/cli/bank.py` — NEW: bank/import CLI commands
- `src/cli/transactions.py` — NEW: transaction display commands
- `main.py` — update CLI entry point with command groups
- `tests/test_csv_parser.py` — NEW: CSV parser tests
- `tests/test_ingestion.py` — NEW: ingestion service tests

## Considerations
- No external API dependencies for MVP — CSV only
- CSV format varies wildly between banks; design the parser to be extensible (add new formats by registering a new format handler)
- Use `hashlib.sha256` of normalised (date, description, amount) for dedup — this catches re-imports of the same file
- Store `transactions.hash` as a UNIQUE index to prevent duplicates across imports
- `click` is lightweight and stdlib-friendly (no FastAPI/Flask dependency for CLI)
- `python-dateutil` handles the wide variety of date formats (DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, "Jan 15, 2024", etc.)
- For production CSV import, support detecting the delimiter (comma, tab, semicolon) — some Indian banks use semicolons
- Keep models simple — SQLModel handles table creation automatically via `metadata.create_all()`
- Use `uv` for all package operations: `uv add`, `uv sync`, `uv run`
