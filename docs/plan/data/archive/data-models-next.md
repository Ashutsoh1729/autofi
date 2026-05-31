# Next Data Models — Foundation for Phase 2

<!--  Payment Reconciliation: Invoice/Bill are now mapped to Transaction via invoice_id / bill_id FKs. -->

## Description

Define and implement the core financial data models needed to support Phase 2 agents (Reconciler, Payments) and the next layer of transaction processing — sales invoicing, vendor bills, formal chart-of-accounts categorisation, and merchant/vendor management.

Current models (`Account` [bank account], `Transaction`, `ConversationMessage`, `AppConfig`) handle CSV ingestion and basic chat. The models below add receivables, payables, GL structure, and counterparty tracking.

## Goals

- Introduce a proper **Chart of Accounts** separate from bank accounts
- Model **Vendors** (counterparties you pay) and **Customers** (counterparties who pay you)
- Model **Invoices** (sales / receivables) with status lifecycle and line items
- Model **Bills** (vendor / payables) with the same lifecycle as invoices
- Add **Category Rules** for auto-categorising transactions by description pattern
- Add **payment reconciliation** — link Transactions to Invoices/Bills via FK
- Keep everything backward-compatible: existing fields and data unchanged

---

## Data Models (in priority order)

### 1. GLAccount — Chart of Accounts

A formal general-ledger account code. **Distinct from the existing `Account` model** (which represents a bank/card account).

| Field        | Type       | Notes                                               |
| ------------ | ---------- | --------------------------------------------------- |
| `id`         | `int` PK   |                                                     |
| `code`       | `str`      | e.g. `"5010"`, `"1100"`. Unique.                    |
| `name`       | `str`      | e.g. `"Office Supplies"`                            |
| `type`       | `str`      | `asset`, `liability`, `equity`, `income`, `expense` |
| `parent_id`  | `int?`     | FK to self; for hierarchical COA                    |
| `is_active`  | `bool`     | Default `True`                                      |
| `created_at` | `datetime` |                                                     |

**Why separate from `Account`?** The existing `Account` is a bank account (checking, savings, credit card). GL accounts are the categorisation hierarchy (e.g. Revenue → Sales Revenue → Product Sales). Mixing them causes confusion.

### 2. Vendor — Vendors / Merchants

Entities you pay money to (suppliers, service providers, subscriptions).

| Field        | Type       | Notes                  |
| ------------ | ---------- | ---------------------- |
| `id`         | `int` PK   |                        |
| `name`       | `str`      |                        |
| `gstin`      | `str?`     | India GSTIN (optional) |
| `email`      | `str?`     |                        |
| `phone`      | `str?`     |                        |
| `created_at` | `datetime` |                        |

### 3. Customer — Customers / Clients

Entities who pay you money.

| Field        | Type       | Notes                  |
| ------------ | ---------- | ---------------------- |
| `id`         | `int` PK   |                        |
| `name`       | `str`      |                        |
| `gstin`      | `str?`     | India GSTIN (optional) |
| `email`      | `str?`     |                        |
| `phone`      | `str?`     |                        |
| `created_at` | `datetime` |                        |

**Design choice:** Separate `Vendor` and `Customer` tables (not a single `Contact`) because SMBs often have distinct AR and AP workflows. A future release could unify via a `Party` table with a type discriminator if needed.

### 3b. Transaction — New Reconciliation Fields

The existing `Transaction` model gets three new nullable FK columns for payment reconciliation and GL categorisation. These are optional — old data works unchanged.

| Field            | Type     | Notes                                        |
| ---------------- | -------- | -------------------------------------------- |
| `gl_account_id`  | `int?`   | FK → `glaccount.id` — what the tx was for    |
| `invoice_id`     | `int?`   | FK → `invoice.id` — which invoice this payment settled |
| `bill_id`        | `int?`   | FK → `bill.id` — which bill this payment settled      |

A Transaction now captures:
- **where** (account_id → bank account)
- **how much** (amount)
- **when** (date)
- **what-for** (gl_account_id → GLAccount)
- **which document** (invoice_id / bill_id → Invoice/Bill)

This enables the Phase 2 Reconciler agent to trace: *which bank movement settled which invoice/bill.*

### 4. Invoice — Sales Invoices (Receivables)

| Field         | Type       | Notes                                           |
| ------------- | ---------- | ----------------------------------------------- |
| `id`          | `int` PK   |                                                 |
| `invoice_no`  | `str`      | User-facing number, unique                      |
| `customer_id` | `int` FK   | References `customer.id`                        |
| `issue_date`  | `date`     |                                                 |
| `due_date`    | `date`     |                                                 |
| `status`      | `str`      | `draft`, `sent`, `paid`, `overdue`, `cancelled` |
| `subtotal`    | `float`    | Before tax                                      |
| `tax_amount`  | `float`    | Total tax                                       |
| `total`       | `float`    | subtotal + tax_amount                           |
| `paid_amount` | `float`    | How much has been paid (default 0)              |
| `notes`       | `str?`     |                                                 |
| `created_at`  | `datetime` |                                                 |

**Status lifecycle:** `draft` → `sent` → `paid` (or `overdue` if past due date, or `cancelled`).

### 5. InvoiceLineItem — Invoice Line Items

| Field           | Type      | Notes                     |
| --------------- | --------- | ------------------------- |
| `id`            | `int` PK  |                           |
| `invoice_id`    | `int` FK  | Cascade delete            |
| `description`   | `str`     |                           |
| `quantity`      | `float`   | Default 1                 |
| `unit_price`    | `float`   |                           |
| `amount`        | `float`   | quantity x unit_price     |
| `gl_account_id` | `int?` FK | References `glaccount.id` |

### 6. Bill — Vendor Bills (Payables)

Same structure as Invoice, mirrored for AP.

| Field         | Type       | Notes                                      |
| ------------- | ---------- | ------------------------------------------ |
| `id`          | `int` PK   |                                            |
| `bill_no`     | `str`      | Vendor's bill reference, unique            |
| `vendor_id`   | `int` FK   | References `vendor.id`                     |
| `issue_date`  | `date`     | Bill date from vendor                      |
| `due_date`    | `date`     |                                            |
| `status`      | `str`      | `pending`, `approved`, `paid`, `cancelled` |
| `subtotal`    | `float`    |                                            |
| `tax_amount`  | `float`    |                                            |
| `total`       | `float`    |                                            |
| `paid_amount` | `float`    | Default 0                                  |
| `notes`       | `str?`     |                                            |
| `created_at`  | `datetime` |                                            |

### 7. BillLineItem — Bill Line Items

Same as InvoiceLineItem, linked to Bill.

| Field           | Type      | Notes                     |
| --------------- | --------- | ------------------------- |
| `id`            | `int` PK  |                           |
| `bill_id`       | `int` FK  | Cascade delete            |
| `description`   | `str`     |                           |
| `quantity`      | `float`   |                           |
| `unit_price`    | `float`   |                           |
| `amount`        | `float`   | quantity x unit_price     |
| `gl_account_id` | `int?` FK | References `glaccount.id` |

### 8. CategoryRule — Auto-Categorisation Rules

Pattern-based rules that the Bookkeeper agent uses to suggest/apply categories to transactions.

| Field           | Type       | Notes                               |
| --------------- | ---------- | ----------------------------------- |
| `id`            | `int` PK   |                                     |
| `pattern`       | `str`      | SQL LIKE pattern (e.g. `"UBER%"`)   |
| `gl_account_id` | `int` FK   | References `glaccount.id`           |
| `category`      | `str`      | Free-text label for backward compat |
| `priority`      | `int`      | Lower number = higher priority      |
| `is_active`     | `bool`     | Default `True`                      |
| `created_at`    | `datetime` |                                     |

---

## Implementation Steps

### Step 1: GLAccount Model

- [x] Add `GLAccount` SQLModel table to `src/data/models.py`
- [x] Add a `Transaction.gl_account_id` nullable FK to `glaccount.id` to link transactions to GL accounts
- [x] Ensure backward compat: existing `Transaction.category` stays as fallback

### Step 2: Vendor & Customer Models

- [x] Add `Vendor` SQLModel table to `src/data/models.py`
- [x] Add `Customer` SQLModel table to `src/data/models.py`

### Step 3: Invoice & InvoiceLineItem Models

- [x] Add `Invoice` SQLModel table
- [x] Add `InvoiceLineItem` SQLModel table
- [x] Define status enum / validation (draft → sent → paid / overdue / cancelled)

### Step 4: Bill & BillLineItem Models

- [x] Add `Bill` SQLModel table
- [x] Add `BillLineItem` SQLModel table
- [x] Define status enum / validation (pending → approved → paid / cancelled)

### Step 5: Payment Reconciliation FKs on Transaction

- [x] Add `Transaction.invoice_id` nullable FK to `invoice.id`
- [x] Add `Transaction.bill_id` nullable FK to `bill.id`
- [x] Verify backward compat: both fields are optional, existing transactions unaffected

### Step 6: CategoryRule Model

- [x] Add `CategoryRule` SQLModel table to `src/data/models.py`

### Step 7: Migration & init_db

- [x] Verify `init_db()` in `src/data/db.py` picks up new tables automatically via `SQLModel.metadata.create_all()`
- [x] Add `seed_gl_accounts()` in `src/data/seed.py` — creates default GLAccount rows (common SMB COA: Revenue, COGS, Rent, Utilities, Office Supplies, etc.)
- [x] Call `seed_gl_accounts()` at the end of `init_db()` in `src/data/db.py`, guarded by "only seed if GLAccount table is empty" to avoid duplicates on restart

### Step 8: Tests

- [x] Test CRUD for each new model (in-memory SQLite)
- [x] Test GLAccount to Transaction FK relationship
- [x] Test Invoice to LineItem cascade relationship
- [x] Test Bill to LineItem cascade relationship
- [x] Test Transaction → Invoice / Bill reconciliation FKs
- [x] Test CategoryRule matching logic

---

## Files to Modify

- `src/data/models.py` — added all new SQLModel tables; added `gl_account_id`, `invoice_id`, `bill_id` FK fields to `Transaction`
- `src/data/db.py` — added `PRAGMA foreign_keys=ON` event listener; calls `seed_gl_accounts()` after `create_all()`
- `src/test/test_db.py` — added tests for all new models, FKs, cascades, reconciliation, seeding

## Files to Create

- `src/data/seed.py` — `seed_gl_accounts()` function; called by `init_db()` when GLAccount table is empty

---

## Considerations

- **GL Account seeding**: Default GLAccount rows (common SMB COA) are created at `init_db()` time via `src/data/seed.py`. Seed runs only if GLAccount table is empty to avoid duplicates on restart.
- **Backward compatibility**: `Transaction.category` (free-text) remains. New `Transaction.gl_account_id`, `invoice_id`, and `bill_id` are all optional. Old data works unchanged.
- **Payment reconciliation**: The `invoice_id`/`bill_id` FKs on Transaction are the single source of truth for which bank movement settled which document. The Reconciler agent writes these links; the Payments agent reads them.
- **GL Account vs Bank Account**: The existing `Account` model is for bank/card accounts (checking, savings, credit). The new `GLAccount` is for the chart of accounts (e.g. "5010 - Office Supplies"). Keep them separate.
- **Invoice/Bill symmetry**: Invoices (AR) and Bills (AP) are structurally identical. Future refactor might unify into a `FinancialDocument` with a type discriminator, but separate tables are clearer for Phase 2.
- **Status enums**: Use plain strings for now (SQLite-compatible, easy to migrate). Move to Python `Enum` if status logic gets complex.
- **Line items**: Separate table (not JSON) so agents can query and update individual line items.
- **Vendor/Customer dedup**: Initially allow duplicates (no unique constraint on name). A cleanup/dedup step can come in a later phase.
- **Auto-categorisation**: `CategoryRule` feeds into the Bookkeeper agent's categorisation tool; the agent applies best-match rules before falling back to LLM suggestion.
