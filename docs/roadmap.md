# Roadmap — Future Directions

> Based on current project state (`docs/project-state.md`).

## Legend
- **Now** — ready to start, all dependencies in place
- **Next** — requires preceding work or external dependency
- **Future** — vision stage, not yet scoped

---

## 1. Reconciler Agent (Now)

Match bank transactions to invoices/bills automatically.

**Why now:** All data models are in place — `Transaction.invoice_id`, `Transaction.bill_id`, `Invoice`, `Bill`, `Vendor`, `Customer`. The agent registry + delegation pattern is proven.

**What:**
- Create `src/agents/reconciler.py` with `Pydantic AI Agent`
- Tools: `suggest_matches(tx_id)` → suggests candidate invoice/bill, `confirm_match(tx_id, doc_id, doc_type)` → writes FK
- Register as `reconciler` in agent registry
- Orchestrator auto-wires delegation tool

---

## 2. Partial Import Error Handling (Now)

**Why now:** Only unchecked item in bank-feed-ingestion plan (Step 6). Current code rolls back the entire batch on any parse error.

**What:**
- In `import_csv()`, catch per-row `ParseError`, collect errors in `ImportResult.errors`, commit valid rows
- Preserve valid transactions even when some rows fail

---

## 3. Financial Reports Agent (Next)

Generate P&L, balance sheet, cash flow from chart of accounts.

**Prerequisites:** Reconciler agent (to ensure GL accounts are assigned).

**What:**
- Create `src/agents/reporter.py`
- Tools: `profit_loss(start, end)`, `balance_sheet(as_of)`, `cash_flow(start, end)`
- Aggregate transactions by `gl_account_id` grouped by `GLAccount.type`

---

## 4. Plaid API Integration (Next)

Automated US bank feed — replaces manual CSV import.

**Prerequisites:** Plaid developer account, API credentials.

**What:**
- Create `src/util/plaid_client.py` — Plaid `/transactions/sync` wrapper
- Add `autofi plaid link` CLI for OAuth Link token flow
- Write into same `transactions` + `accounts` tables
- Store `plaid_access_token` encrypted in `AppConfig`

---

## 5. India Account Aggregator Integration (Next)

Automated Indian bank feed via AA framework (Finvu, CAMS Finserv).

**Prerequisites:** AA registration, consent flow implementation.

**What:**
- Create `src/util/aa_client.py`
- Implement consent artefact management
- Write into same `transactions` + `accounts` tables

---

## 6. Workflow Executor (Next)

Run multi-step business workflows by chaining agent/tool calls in a defined order.

**Prerequisites:** Agent registry + delegation pattern (done).

**What:**
- Define workflows as YAML/dict: `steps: [{agent, tool, params, output_key}]`
- Workflow engine tool on orchestrator: `run_workflow(workflow_id, inputs)` → iterates steps, passes outputs as next inputs
- Supports branching/conditionals (basic DAG)
- Store workflow definitions + execution history in DB
- Example workflow: `import_csv → auto_categorise_all → reconcile_all`

---

## 7. Payments Agent (Next)

Manage payment workflows — mark invoices as paid, update `paid_amount`, send payment reminders.

**Prerequisites:** Reconciler agent (invoice/bill data reliable).

**What:**
- Create `src/agents/payments.py`
- Tools: `pay_invoice(invoice_id, amount, tx_id)`, `pay_bill(bill_id, amount, tx_id)`
- Update `Invoice.paid_amount` / `Bill.paid_amount`, link to transaction

---

## 7. Web UI / Dashboard (Future)

Web frontend for non-CLI users.

**Prerequisites:** Stable agent API, auth mechanism.

**What:**
- FastAPI/Starlette server wrapping the same agents
- React or minimal HTMX dashboard
- Charts: spending by category, cash flow timeline, invoice aging

---

## 8. Multi-Company / Multi-User (Future)

Isolate data per company or user.

**Prerequisites:** Web UI (for user management).

**What:**
- Add `company_id` / `user_id` to all models
- Scoped sessions via SQLAlchemy query filters
- CLI `--company` flag or env-based selection

---

## Current Test Coverage

| Area | Tests |
|------|-------|
| CSV Parser | 22 |
| Ingestion Service | 10 |
| DB Models | 17 |
| CLI Commands | 15 |
| Bookkeeper Agent | 48 |
| Orchestrator Delegation | 3 |
| **Total** | **120** |
