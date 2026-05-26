# AutoFi — Spec

Here this project is inpired from the company named - [Balance](https://getbalance.ai/)

## 1. Vision

AutoFi is an autonomous team of AI agents, each specialised in a financial domain, that collectively manages the full financial operations of an SMB (small-to-medium business). The system ingests bank transactions, invoices, bills, and payroll data, then handles bookkeeping, reconciliations, cash flow forecasting, compliance monitoring, and financial reporting — with minimal human oversight.

The user interacts via a chat interface (like this one) to ask questions, approve actions, or review summaries. Agents coordinate behind the scenes.

---

## 2. Agent Roles

| Agent            | Role                                                                                                                                                       |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Orchestrator** | Receives user requests, decomposes them into tasks, routes to specialist agents, synthesises responses. Maintains conversation state and escalation rules. |
| **Bookkeeper**   | Categorises transactions, maintains the chart of accounts, posts journal entries, runs trial balances.                                                     |
| **Reconciler**   | Matches bank statements against ledger entries, flags discrepancies, suggests corrections.                                                                 |
| **Payments**     | Manages accounts payable/receivable, schedules payments, sends invoice reminders, detects late payments.                                                   |
| **Forecaster**   | Produces cash flow projections, flags runway risks, models scenario impacts (e.g. "what if client X pays 30 days late?").                                  |
| **Compliance**   | Monitors filing deadlines (GST/VAT, income tax, payroll tax), tracks regulatory changes, alerts on filing windows.                                         |
| **Analyst**      | Generates P&L, balance sheet, cash flow statements, variance analysis, board-ready dashboards.                                                             |
| **Auditor**      | Periodically reviews agent decisions for consistency, detects anomalies, logs audit trails.                                                                |

---

## 3. Core Workflows

### 3.1 Daily Reconciliation

1. Reconciler pulls overnight bank feed (via Plaid / Open Banking API).
2. Bookkeeper maps incoming transactions to GL accounts using rules + user history.
3. Reconciler matches transactions to open invoices/bills.
4. If match rate < 95%, flags remaining items to user with suggested categories.
5. Orchestrator summarises: "12 new transactions reconciled. 1 uncategorised: $42.00 at 'Staples' — office supplies?"

### 3.2 Month-End Close

1. Bookkeeper runs trial balance.
2. Reconciler confirms all bank accounts reconciled.
3. Analyst generates draft P&L and balance sheet.
4. Auditor reviews for anomalies (e.g. sudden COGS spike, missing accruals).
5. Orchestrator presents closing package to user for sign-off.

### 3.3 Cash Flow Forecasting

1. Forecaster reads upcoming AP/AR from Payments agent.
2. Combines with historical spending patterns and seasonality.
3. Produces 13-week rolling forecast.
4. If projected balance < buffer threshold, alerts user with recommended actions.

### 3.4 Compliance Calendar

1. Compliance agent tracks jurisdiction-specific deadlines.
2. Nudges user N days before each filing.
3. Orchestrator offers: "GST is due in 7 days. Shall I prepare the return?"

---

## 4. Architecture

```
┌─────────────────────────────────────────────────┐
│                   User (Chat CLI)                │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Orchestrator Agent                  │
│  (LLM + router + state manager + tool dispatch) │
└──┬───┬───┬───┬───┬───┬───┬───┬─────────────────┘
   │   │   │   │   │   │   │   │
   ▼   ▼   ▼   ▼   ▼   ▼   ▼   ▼
   BK  RC  PM  FC  CP  AN  AU   (specialist agents)
                                   │
                                   ▼
                          ┌────────────────┐
                          │  Data Layer    │
                          │  (SQLite/Postgres +   │
                          │   object storage)     │
                          └────────────────┘
```

- **Orchestrator** is the only agent that talks to the user.
- Each specialist agent exposes a tool interface (e.g. `categorise_tx(tx_id, account_code)`).
- Agents share a read/write data layer (relational DB for ledgers, file store for receipts).
- Communication is event-driven: the orchestrator publishes tasks to a queue; agents pick up, process, and emit results.

---

## 5. Data Model (Core Entities)

- **Account** — chart of accounts (asset, liability, equity, revenue, expense).
- **Transaction** — single bank or card movement. Linked to an Account.
- **Invoice** — outgoing receivable. Has line items, status (draft, sent, paid, overdue).
- **Bill** — incoming payable. Same lifecycle as Invoice.
- **Reconciliation** — pairing of a Transaction with an Invoice/Bill or a journal entry.
- **Forecast** — projected cash position per day for N weeks.
- **ComplianceEvent** — a filing or regulatory deadline. Has jurisdiction, form, due date.
- **Report** — generated P&L, balance sheet, cash flow statement, variance report.

---

## 6. Implementation Phases

### Phase 1 — Agent Scaffold (Current)

- Build the Orchestrator + Bookkeeper agents in a local CLI.
- Support manual transaction entry and categorisation.
- Store everything in SQLite.

### Phase 2 — Bank Integration

- Add Reconciler + Payments agents.
- Plaid/Open Banking feed ingestion.
- Auto-matching engine for reconciliation.

### Phase 3 — Intelligence

- Forecaster + Analyst + Compliance agents.
- ML-powered categorisation suggestions.
- Cash flow predictions with what-if modelling.

### Phase 4 — Production

- Auditor agent (ongoing anomaly detection).
- Multi-entity support (accountant view across clients).
- Web dashboard for visual reports.
- Role-based access (business owner vs bookkeeper).

---

## 7. Tech Stack (Proposed)

| Layer      | Choice                                                               |
| ---------- | -------------------------------------------------------------------- |
| Framework  | Python (FastAPI for API, LangGraph / CrewAI for agent orchestration) |
| DB         | SQLite (dev), Postgres (prod)                                        |
| LLM        | GPT-4 / Claude for agent reasoning                                   |
| Bank Feeds | Plaid API (US) / Teller.io or GoCardless (UK/EU)                     |
| Reporting  | Matplotlib / Plotly (static), or Metabase (dashboard)                |
| Queue      | Redis + Celery (or in-process for MVP)                               |
| Auth       | Clerk / Auth0 (prod)                                                 |

---

## 8. Open Questions

- Should agents operate synchronously (request-reply) or asynchronously (pub/sub)?
- How do we handle user approvals that block workflows (e.g. approve payment > $5K)?
- What is the fallback when the LLM is unavailable / rate-limited?
- Do we store receipts/docs in the DB or in object storage with DB pointers?
- Should we support multi-currency from day one?
