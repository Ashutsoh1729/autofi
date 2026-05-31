# Bookkeeper — Reconciliation Tools

## Description
Add transaction reconciliation tools directly to the Bookkeeper agent instead of creating a separate agent. Bookkeepers handle reconciliation in SMBs, so these tools belong on the bookkeeper.

## Steps

### Step 1: find_unreconciled_transactions
- [x] Tool to list transactions where `invoice_id IS NULL AND bill_id IS NULL`
- [x] Returns formatted list with id, date, amount, description

### Step 2: suggest_matches
- [x] Fetch transaction by id
- [x] Score unmatched invoices/bills by amount, date proximity, description overlap
- [x] Return formatted list of candidates with scores

### Step 3: confirm_match
- [x] Link transaction to invoice or bill via FK
- [x] Update `paid_amount` on invoice/bill incrementally
- [x] Error handling: not found, already linked, wrong doc_type

### Step 4: Tests
- [x] Unit tests for all 3 tools with in-memory SQLite

## Files to Modify
- `src/agents/bookkeeper.py` — add 3 new tools + register
- `tests/test_bookkeeper_tools.py` — add tests
