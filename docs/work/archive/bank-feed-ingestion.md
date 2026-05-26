# Bank Feed Ingestion — Work File

## What functions each step accomplishes

---

### Step 1 & 2: Project Setup & Data Model ✅ (Done)

**Functions enabled:**
- `src/util/config.py` knows where to store/read the SQLite DB (`~/.local/share/autofi/autofi.db`)
- `src/data/db.py` can create the DB and tables, and hand out sessions for read/write
- `src/data/models.py` defines what an `Account` and a `Transaction` look like in code and in the DB
- `Transaction.compute_hash()` prevents duplicate rows when the same CSV is imported twice

**Business capability:** None yet at the CLI level, but the plumbing is ready — you can call `init_db()` and start inserting rows programmatically.

---

### Step 3: CSV Parser ✅ (Done)

**Functions it solves:**
- Reads a CSV file from disk and auto-detects which bank format it is (Generic, HDFC, Chase)
- Parses rows into a canonical `RawTransaction` (date, description, amount, currency, type)
- Handles messy CSV quirks: BOM, quoted fields, commas in amounts, empty rows
- Strips currency symbols and whitespace from amounts

**Implemented in:** `src/util/csv_parser.py` (217 lines)

**Business capability:** Turns a bank's exported CSV into structured data the system can understand.

---

### Step 4: Ingestion Service ✅ (Done)

**Functions it solves:**
- `import_csv()` — parses CSV, deduplicates via hash, inserts new rows, reports what happened
- `list_transactions()` — queries transactions with filters (account, date range, limit)
- `get_transaction_stats()` — counts and date ranges per account
- `--dry-run` mode to preview imports without writing

**Implemented in:** `src/util/bank_feed_ingestion.py` (154 lines)

**Business capability:** The core "get my bank data in" operation. Without this, nothing downstream (categorisation, reconciliation, forecasting) has data to work on.

---

### Step 5: CLI Commands ✅ (Done)

**Functions it solves:**
- `autofi bank import <file.csv>` — the user-facing way to invoke Step 4
- `autofi bank list` — see all connected accounts
- `autofi bank add-account <name>` — create a new account
- `autofi tx list` — see transactions with filters (--account-id, --days, --limit)
- `autofi tx show <id>` — full transaction details
- `autofi tx stats` — quick summary of what's in the DB

**Implemented in:** `src/cli/bank.py` (71 lines), `src/cli/transactions.py` (62 lines)

**Business capability:** The user can actually interact with the system. This is the first point where `autofi` does something useful from the terminal.

---

### Step 6: Validation & Error Handling ✅ (Done)

**Functions it solves:**
- Rejects bad CSVs before they reach the DB (empty file, no headers, unrecognised format)
- Reports per-row errors with line numbers (bad dates, missing amounts)
- Partial import — valid rows go in, invalid rows are reported, no rollback
- Unknown account IDs raise clear errors; multiple accounts require explicit `--account-id`

**Handling embedded in:** `src/util/csv_parser.py` and `src/util/bank_feed_ingestion.py`

**Business capability:** Robustness. Users can't break the system with a malformed export, and they know exactly which rows to fix.

---

### Step 7: Testing ✅ (Done)

**Functions it solves:**
- Unit tests prove the CSV parser handles all formats correctly (217 test lines)
- Ingestion tests prove dedup, dry-run, stats, and partial import work (139 test lines)
- CLI tests prove the commands produce correct output

**Tests in:** `tests/test_csv_parser.py`, `tests/test_ingestion.py`

**Business capability:** Confidence. Changes won't silently break the ingestion pipeline.

---

### Step 8: Future — Plaid / AA Integration (Deferred)

**Functions it will solve:**
- Replace manual CSV with automated bank feeds
- Same `transactions` table, same schema, same queries
- Polling or webhook-based sync

**Business capability:** Zero-touch data ingestion. User links their bank once, transactions flow in automatically.
