# Bookkeeper Agent Upgrade — Full Data Model Access

## Description
Give the Bookkeeper agent full access to all existing data models: GL accounts, auto-categorisation rules, vendors, customers, invoices, bills, and transaction reconciliation.

## Implementation Steps

### Step 1: GL Account Tools
- [x] Add `list_gl_accounts(acct_type: str | None)` — list chart of accounts optionally filtered by type

### Step 2: Auto-Categorisation via CategoryRule
- [x] Add `auto_categorise(tx_id: int)` — match transaction description against CategoryRule patterns, apply best match

### Step 3: Vendor & Customer Tools
- [x] Add `list_vendors(query: str)` — search vendors by name
- [x] Add `list_customers(query: str)` — search customers by name
- [x] Add `add_vendor(name, ...)` — create a new vendor
- [x] Add `add_customer(name, ...)` — create a new customer

### Step 4: Invoice & Bill Tools
- [x] Add `list_invoices(status: str | None)` — list invoices with optional status filter
- [x] Add `list_bills(status: str | None)` — list bills with optional status filter
- [x] Add `show_invoice(id: int)` — full invoice details with line items
- [x] Add `show_bill(id: int)` — full bill details with line items

### Step 5: Reconciliation Tools
- [x] Add `link_to_invoice(tx_id: int, invoice_id: int)` — link a transaction to an invoice
- [x] Add `link_to_bill(tx_id: int, bill_id: int)` — link a transaction to a bill

### Step 6: Tests
- [x] Unit tests for all new tools
- [x] Agent integration test with TestModel

## Files to Modify
- `src/agents/bookkeeper.py` — add all new tools, register on agent
- `tests/test_bookkeeper_tools.py` — add tests for new tools

## Files to Create
- `docs/plan/agents/bookkeeper-upgrade.md` — this plan
