# Transaction Processing — Deep Dive

## 1. Scope

Transaction processing covers every movement of money into and out of an SMB. It is the highest-frequency financial activity (anything from 5 to 500+ transactions per day) and the foundation on which all other financial operations — reconciliation, reporting, forecasting, compliance — are built. If transactions are wrong, everything downstream is wrong.

---

## 2. Sub-Domains

```
Transaction Processing
├── A. Inbound (Money In)
│   ├── A1. Sales invoicing
│   ├── A2. Payment collection (cards, bank transfer, cash, checks)
│   ├── A3. Payment-to-invoice matching
│   ├── A4. Overdue / dunning management
│   └── A5. Refunds & chargebacks
│
├── B. Outbound (Money Out)
│   ├── B1. Purchase order creation & management
│   ├── B2. Vendor bill receipt & validation
│   ├── B3. Expense submission & approval
│   ├── B4. Payment execution (ACH, wire, check, card)
│   └── B5. Recurring subscription management
│
└── C. Data & Enrichment
    ├── C1. Bank feed ingestion
    ├── C2. Merchant & transaction enrichment
    ├── C3. Chart-of-accounts categorisation
    ├── C4. Duplicate detection
    └── C5. Currency conversion recording
```

---

## 3. Detailed Breakdown

### A1. Sales Invoicing

Creating and delivering invoices to customers for goods or services rendered.

| Aspect         | Detail                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------- |
| Inputs         | Timesheets, delivery logs, subscription records, manual entry                               |
| Outputs        | PDF/email invoice, Accounts Receivable ledger entry                                         |
| Frequency      | Daily or on-demand (could be batch or real-time per sale)                                   |
| Typical volume | 10–200 invoices/month for an SMB                                                            |
| Pain points    | Manual data entry, inconsistent formatting, late delivery, tracking sent/opened/paid status |

### A2. Payment Collection

Receiving funds from customers via various channels.

| Aspect      | Detail                                                                                   |
| ----------- | ---------------------------------------------------------------------------------------- |
| Inputs      | Raw payment webhooks (Stripe), bank statements, check scans                              |
| Outputs     | Updated invoice status, cash receipt entries in ledger                                   |
| Frequency   | Daily, often real-time                                                                   |
| Channels    | Credit card (Stripe/Square), bank transfer (ACH/wire), cash, check, BNPL (Klarna, etc.)  |
| Pain points | Fragmented data across multiple processors, delayed settlement (Stripe T+2, checks T+5+) |

### A3. Payment-to-Invoice Matching

Connecting an incoming payment to the specific invoice(s) it settles.

| Aspect      | Detail                                                                                             |
| ----------- | -------------------------------------------------------------------------------------------------- |
| Inputs      | Payment record + open invoices                                                                     |
| Outputs     | Paid/open/overpaid/underpaid status per invoice                                                    |
| Difficulty  | Low for single-invoice payments; high for bulk payments or partials                                |
| Pain points | Customers pay without remittance info, pay multiple invoices in one transfer, short-pay or overpay |

### A4. Overdue / Dunning Management

Proactively chasing unpaid invoices.

| Aspect      | Detail                                                                                                            |
| ----------- | ----------------------------------------------------------------------------------------------------------------- |
| Inputs      | Aged AR report, customer contact info                                                                             |
| Outputs     | Sent reminder emails, escalated accounts                                                                          |
| Frequency   | Weekly or per configurable schedule                                                                               |
| Pain points | Manual tracking, inconsistent follow-up, awkward customer conversations, damaging relationships if too aggressive |

### A5. Refunds & Chargebacks

Handling money going back to customers.

| Aspect      | Detail                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------ |
| Inputs      | Refund request, chargeback notification                                                          |
| Outputs     | Credit memo, reversed journal entry, updated AR                                                  |
| Frequency   | Low (1–5% of transactions)                                                                       |
| Pain points | Tracking reason codes (chargebacks), timing of refunds vs bank settlement, inventory adjustments |

---

### B1. Purchase Order Management

Creating, approving, and tracking POs before vendor purchases.

| Aspect      | Detail                                                                         |
| ----------- | ------------------------------------------------------------------------------ |
| Inputs      | Internal requisition, vendor quote                                             |
| Outputs     | PO document, committed expense in ledger                                       |
| Frequency   | On-demand (1–50/month)                                                         |
| Pain points | Bypassed POs (employees buy first, ask later), no budget check before approval |

### B2. Vendor Bill Receipt & Validation

Receiving and verifying bills from vendors.

| Aspect      | Detail                                                                                                               |
| ----------- | -------------------------------------------------------------------------------------------------------------------- |
| Inputs      | PDF/paper/email bill, PO reference                                                                                   |
| Outputs     | Bill recorded in Accounts Payable, matched against PO                                                                |
| Frequency   | Daily (10–100 bills/month)                                                                                           |
| Pain points | Bills arrive via email/paper/portal with no standard format; matching to POs is manual; quantity/price discrepancies |

### B3. Expense Submission & Approval

Employees spend money and submit expenses for reimbursement.

| Aspect      | Detail                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------- |
| Inputs      | Receipt images, mileage logs, credit card charges                                           |
| Outputs     | Approved/denied expense, reimbursement entry                                                |
| Frequency   | Weekly (5–50 submissions/month per employee)                                                |
| Pain points | Lost receipts, policy violations, slow approval cycles, miscategorised personal vs business |

### B4. Payment Execution

Actually sending money to vendors, employees, and other payees.

| Aspect      | Detail                                                                         |
| ----------- | ------------------------------------------------------------------------------ |
| Inputs      | Approved bills, POs, expense reports                                           |
| Outputs     | ACH/wire/check, updated AP ledger                                              |
| Frequency   | Weekly or bi-weekly (batch)                                                    |
| Channels    | ACH, wire transfer, physical check, virtual card                               |
| Pain points | Cutoff times, bank holidays, fraud risk (new vendor verification), cash timing |

### B5. Recurring Subscription Management

Managing ongoing SaaS, software, and service subscriptions.

| Aspect      | Detail                                                                                |
| ----------- | ------------------------------------------------------------------------------------- |
| Inputs      | Subscription invoices, bank charges                                                   |
| Outputs     | Categorised recurring charges, cancellation list                                      |
| Frequency   | Monthly                                                                               |
| Pain points | Forgotten subscriptions bleeding cash, price increases unnoticed, no central register |

---

### C1. Bank Feed Ingestion

Pulling transaction data from bank and card accounts.

| Aspect      | Detail                                                                               |
| ----------- | ------------------------------------------------------------------------------------ |
| Inputs      | Bank API (Plaid, Teller, GoCardless, OFX, CSV)                                       |
| Outputs     | Unprocessed transaction records in the system                                        |
| Frequency   | Daily (configurable: every 6h, 12h, 24h)                                             |
| Pain points | API reliability, credential re-authentication, bank transaction naming inconsistency |

### C2. Merchant & Transaction Enrichment

Cleaning up raw bank transaction descriptions into usable data.

| Aspect      | Detail                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------ |
| Inputs      | Raw bank line: `DEBIT 12.99 SQ*SUBWAY 5TH AVE NEW YORK NY`                                       |
| Outputs     | Structured: `{ merchant: "Subway", amount: 12.99, category: "Meals", location: "New York, NY" }` |
| Frequency   | Daily (per ingested transaction)                                                                 |
| Pain points | Inconsistent naming (SQ*, PayPal *AMAZON, etc.), no merchant metadata, international vs domestic |

### C3. Chart-of-Accounts Categorisation

Assigning each transaction to the correct GL account.

| Aspect      | Detail                                                                                                                      |
| ----------- | --------------------------------------------------------------------------------------------------------------------------- |
| Inputs      | Enriched transaction + existing category rules + user history                                                               |
| Outputs     | Categorised transaction (e.g. `Account: 5010 — Office Supplies`)                                                            |
| Frequency   | Daily                                                                                                                       |
| Pain points | Large COA (50–200 accounts), split transactions (one receipt across multiple categories), inconsistent human categorisation |

### C4. Duplicate Detection

Identifying and flagging transactions that appear more than once.

| Aspect      | Detail                                                                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Inputs      | Transaction stream                                                                                                                          |
| Outputs     | Flagged duplicates for review                                                                                                               |
| Frequency   | Daily                                                                                                                                       |
| Pain points | Bank vs credit card double-recording, manual entry + feed duplication, same transaction appearing in two accounts (transfer recorded twice) |

### C5. Currency Conversion Recording

Handling multi-currency transactions.

| Aspect      | Detail                                                                                              |
| ----------- | --------------------------------------------------------------------------------------------------- |
| Inputs      | Foreign-currency transaction, exchange rate                                                         |
| Outputs     | Recorded transaction in base currency + FX gain/loss entry                                          |
| Frequency   | Per cross-currency transaction                                                                      |
| Pain points | Choosing the right rate (spot vs daily average vs month-end), unrealised vs realised gains tracking |

---

## 4. Importance Ranking

These are ranked by **impact if done wrong** — errors cascade downstream.

| Rank | Sub-Domain                            | Impact of Error                                                                |
| ---- | ------------------------------------- | ------------------------------------------------------------------------------ |
| 1    | **Chart-of-accounts categorisation**  | Wrong categories misstate P&L, hide real costs, cause incorrect tax deductions |
| 2    | **Payment-to-invoice matching**       | AR/AP balances become unreliable; cash flow visibility breaks                  |
| 3    | **Bank feed ingestion**               | If feeds stop, the entire system goes dark                                     |
| 4    | **Sales invoicing**                   | Cash doesn't come in; relationship damage from incorrect invoices              |
| 5    | **Payment execution**                 | Late payments hurt vendor relationships; duplicate payments lose money         |
| 6    | **Expense submission & approval**     | Undetected policy violations, reimbursement delays frustrate employees         |
| 7    | **Duplicate detection**               | Inflated expenses, wasted cash on double-payments                              |
| 8    | **Overdue / dunning management**      | Slow collections extend DSO; no reminders = no urgency                         |
| 9    | **Merchant & transaction enrichment** | Manual cleanup downstream; classification accuracy suffers                     |
| 10   | **PO management**                     | Budget overspend; unapproved commitments                                       |
| 11   | **Vendor bill validation**            | Paying incorrect amounts, paying for undelivered goods                         |
| 12   | **Recurring subscription management** | Slow bleed of forgotten subscriptions                                          |
| 13   | **Refunds & chargebacks**             | Low volume but high-touch; impacts merchant processor relationship             |
| 14   | **Currency conversion**               | Low for domestic SMBs; high for cross-border businesses                        |

---

## 5. Automation Potential

| Sub-Domain                       | Automatable? | How                                                                                             | Confidence |
| -------------------------------- | ------------ | ----------------------------------------------------------------------------------------------- | ---------- |
| Bank feed ingestion              | ✅ Fully     | Pre-built connectors (Plaid, etc.)                                                              | Very high  |
| Merchant enrichment              | ✅ Fully     | Merchant database lookup + regex parsing                                                        | Very high  |
| Chart-of-accounts categorisation | ✅ Mostly    | ML classifier trained on historical categorisations; user confirmation for low-confidence items | High       |
| Duplicate detection              | ✅ Fully     | Deterministic rules (amount + merchant + date within N days)                                    | Very high  |
| Sales invoicing                  | ✅ Mostly    | Template + data source → auto-generate; manual review for one-offs                              | High       |
| Overdue / dunning management     | ✅ Fully     | Conditional email sequences; escalate at configurable thresholds                                | Very high  |
| Recurring subscription detection | ✅ Mostly    | Pattern detection on monthly charges; flag for user                                             | High       |
| Payment-to-invoice matching      | ⚠️ Partial   | Deterministic (invoice ref in memo) + fuzzy (amount + date proximity); edge cases need human    | Medium     |
| Expense submission               | ⚠️ Partial   | OCR receipts, auto-categorise; approval routing automated; policy checks automated              | Medium     |
| PO creation & approval routing   | ⚠️ Partial   | Auto-generate from requisition; auto-route for approval; budget check                           | Medium     |
| Vendor bill validation           | ⚠️ Partial   | OCR bill, auto-match to PO; discrepancy flags; human signs off                                  | Medium     |
| Payment execution                | ⚠️ Partial   | Batch payment file generation; human approval for new vendors / above threshold                 | Medium     |
| Refunds & chargebacks            | ❌ Low       | Triage and data gathering can be automated; judgment and communication need human               | Low        |
| Currency conversion recording    | ❌ Low       | Rate fetching can be automated; FX gain/loss calculation needs accounting rules                 | Low        |

### Automation Priority Matrix

```
                     HIGH AUTOMATION POTENTIAL
                             │
    DUPLICATE DETECTION       │     BANK FEED INGESTION
    DUNNING MANAGEMENT        │     MERCHANT ENRICHMENT
    RECURRING SUB DETECTION   │     COA CATEGORISATION
                             │     SALES INVOICING
                             │
    ──────────────── LOW EFFORT ───────────────── HIGH EFFORT ──
                             │
    REFUNDS / CHARGEBACKS    │     PAYMENT MATCHING
    CURRENCY CONVERSION      │     EXPENSE SUBMISSION
                             │     BILL VALIDATION
                             │     PAYMENT EXECUTION
                             │     PO MANAGEMENT
                             │
                     LOW AUTOMATION POTENTIAL
```

**Sweet spot (top-right quadrant):** Bank feed ingestion, merchant enrichment, COA categorisation, and sales invoicing are high-impact, high-automation, and relatively straightforward to build.

---

## 6. Key Takeaways for AutoFi

1. **Build bank feed ingestion first.** Without live transaction data, nothing else works. Plaid is the default choice for US-based SMBs.

2. **Invest in COA categorisation early.** This is the single highest-impact automation. A good ML categoriser (trained on the business's own history + common merchant mappings) saves more bookkeeper time than any other single feature.

3. **Sales invoicing is the "aha moment" for the business owner.** Being able to say "Invoice #1042 for $5,000 was automatically generated and sent to Acme Corp" makes the value of the system tangible immediately.

4. **Payment matching is harder than it looks.** Partial payments, bulk payments, and missing remittance info are common. Start with deterministic matching (reference numbers) and add fuzzy matching in phases.

5. **Expense management is a gateway feature.** Employees who submit expenses are often the ones who convince the owner to adopt a full system. Make the employee experience frictionless (OCR + SMS receipt capture + fast approval).

6. **Don't build payment execution in-house.** Partner with Stripe (for cards), Plaid Transfer or Dwolla (for ACH), or a full AP automation API. The compliance and fraud surface area is significant.

7. **Dunning is free money.** Automating payment reminders recovers cash with near-zero ongoing effort. Build this early — it pays for itself on day one.
