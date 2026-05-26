# SMB Financial Operations — A Comprehensive Breakdown

## 1. Categorisation of Financial Activities

Every SMB's financial operations fall into eight major categories. Each represents a distinct domain with its own workflows, data, and stakeholders.

```
Financial Activities
├── A. Transaction Processing       — daily money movement
├── B. Reconciliation               — verifying records match reality
├── C. Payroll & Employee Finance   — paying people
├── D. Tax & Compliance             — obligations to government
├── E. Reporting & Analysis         — understanding performance
├── F. Planning & Forecasting       — looking ahead
├── G. Treasury & Cash Management   — managing liquidity & debt
└── H. Record Keeping & Audit       — the paper trail
```

---

## 2. Operations by Category

### A. Transaction Processing

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Sales invoicing | Daily / on-demand | Generate and send invoices to customers |
| Recording sales receipts | Daily | Log payments received (cash, card, bank transfer) |
| Purchasing / procurement | Daily / on-demand | Raise POs, receive vendor bills |
| Expense recording | Daily | Log employee / business expenses (receipts) |
| Payment disbursement | Daily / weekly | Pay bills, vendors, subscriptions |
| Customer payment follow-up | Weekly | Send reminders on overdue invoices |
| Bank feed ingestion | Daily | Pull overnight bank transactions |

### B. Reconciliation

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Bank account reconciliation | Monthly (weekly for high-volume) | Match bank statement lines to ledger entries |
| Credit card reconciliation | Monthly | Match credit card statement to expenses |
| Merchant account reconciliation | Monthly | Match Stripe/Square/etc. payouts to invoices |
| Inter-account transfer verification | Monthly | Confirm transfers between business accounts |
| Petty cash reconciliation | Monthly | Count physical cash vs ledger |

### C. Payroll & Employee Finance

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Payroll processing | Weekly / bi-weekly / monthly | Calculate pay, deductions, withholdings |
| Payroll disbursement | Per pay cycle | Transfer salaries to employees |
| Employee expense reimbursement | Weekly / monthly | Review and reimburse approved claims |
| Contractor payments | Per agreement | Pay 1099 / freelance workers |
| Benefits administration | Monthly | Manage health insurance, retirement deductions |
| Time tracking verification | Per pay cycle | Approve timesheets |

### D. Tax & Compliance

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Sales tax (VAT/GST) calculation | Per transaction | Apply correct tax rate |
| Sales tax filing | Monthly / quarterly | File return and remit tax collected |
| Payroll tax filing | Quarterly | File employment taxes (FUTA, SUTA, etc.) |
| Estimated income tax payments | Quarterly | Pay estimated corporate / self-employment tax |
| Annual income tax return | Annually | File federal and state returns |
| Business license renewal | Annually | Renew local / state operating licences |
| 1099 filing | Annually | File contractor payment summaries |
| Informational returns | Annually | 1098, FBAR, etc. |

### E. Reporting & Analysis

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Profit & Loss statement | Monthly | Revenue - expenses = net income |
| Balance sheet | Monthly | Assets, liabilities, equity snapshot |
| Cash flow statement | Monthly | Operating, investing, financing cash movements |
| Budget vs actuals | Monthly | Compare actual results to budget |
| Management accounts | Monthly | Detailed internal financial package |
| KPI dashboard | Weekly / real-time | Revenue, burn, ARR, margin, etc. |
| Variance analysis | Monthly / quarterly | Explain differences from prior periods or budget |
| Board / investor reporting | Quarterly | Formal presentation for stakeholders |

### F. Planning & Forecasting

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Cash flow forecast | Weekly (rolling 13-week) | Project cash in/out, identify shortfalls |
| Annual budget preparation | Annually | Set revenue, expense, and capex targets |
| Quarterly reforecast | Quarterly | Update budget with actuals + new information |
| Scenario modelling | On-demand | What-if analysis (e.g. "30% revenue drop") |
| Tax planning | Quarterly / annually | Estimate liabilities, plan payments |
| Capital expenditure planning | Annually | Plan major asset purchases |

### G. Treasury & Cash Management

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Cash position monitoring | Daily | Check all account balances |
| Debt servicing | Per loan schedule | Make principal + interest payments |
| Credit line management | Monthly | Monitor revolver usage, renewals |
| Investment management | Quarterly | Manage excess cash (sweep accounts, T-bills) |
| Foreign exchange management | Per need | Convert / hedge currency for cross-border business |

### H. Record Keeping & Audit

| Operation | Frequency | Description |
|-----------|-----------|-------------|
| Receipt / document capture | Daily | Scan and store receipts, contracts, invoices |
| Audit trail maintenance | Continuous | Log all changes to financial records |
| Journal entry documentation | As needed | Record adjustments, accruals, depreciation |
| Annual audit support | Annually | Prepare schedules, answer auditor queries |
| Record retention | Annually | Archive closed year's records per retention policy |

---

## 3. Importance Ranking by Stakeholder Viewpoint

Not all operations are equally critical. Importance depends on **who** is asking and **why**.

### 3.1 From the Business Owner's View

*The owner cares about survival, growth, and peace of mind.*

| Rank | Operation | Why |
|------|-----------|-----|
| 1 | Cash flow forecast | The #1 cause of SMB failure is running out of cash. Owners need to know runway. |
| 2 | Cash position monitoring | Daily visibility into what's available to spend. |
| 3 | Payment disbursement | Late payments damage relationships and supply chain. |
| 4 | Sales invoicing | Cash doesn't come in unless invoices go out. |
| 5 | P&L reporting (monthly) | Am I making money? This is the headline number. |
| 6 | Accounts receivable follow-up | Getting paid on time is the second biggest cash risk. |
| 7 | Customer payment follow-up | Chasing overdue invoices directly impacts cash. |
| 8 | Budget vs actuals | Is the business on track against its plan? |
| 9 | Annual income tax filing | Legal obligation; penalties for missing it are severe. |
| 10 | Payroll processing | Employees must be paid accurately and on time. |

### 3.2 From the Bookkeeper / Accountant's View

*They care about accuracy, completeness, and efficient workflows.*

| Rank | Operation | Why |
|------|-----------|-----|
| 1 | Bank account reconciliation | Foundation of all financial accuracy. If this is wrong, everything is wrong. |
| 2 | Transaction recording & categorisation | Garbage in, garbage out. Correct categories make everything downstream work. |
| 3 | Receipt / document capture | Missing documentation is the #1 headache during tax prep and audit. |
| 4 | Sales tax (VAT/GST) filing | High penalty risk, requires specific calculations, strict deadlines. |
| 5 | Payroll processing | Complex calculations (tax, super, deductions), high compliance risk. |
| 6 | Journal entry documentation | Adjustments, accruals, depreciation — easy to forget, hard to reconstruct. |
| 7 | Expense categorisation | Directly impacts P&L accuracy and tax deductions. |
| 8 | Credit card reconciliation | Often neglected; leads to miscategorised business expenses. |
| 9 | Accounts payable review | Ensures bills are paid on time and no duplicate payments. |
| 10 | Annual audit support | Seasonal crunch; having clean records saves hours. |

### 3.3 From a Compliance / Risk Perspective

*Penalties, deadlines, and legal exposure.*

| Rank | Operation | Why |
|------|-----------|-----|
| 1 | Payroll processing & tax filing | Personal liability for directors; can include jail time for withheld taxes. |
| 2 | Sales tax (VAT/GST) filing | Short filing windows, frequent penalties for errors. |
| 3 | Annual income tax return | Large potential liability; audit trigger if done wrong. |
| 4 | Estimated quarterly income tax | Underpayment penalties add up. |
| 5 | 1099 / contractor filing | Missed filings = IRS penalties per form. |
| 6 | Business license renewal | Can legally prevent you from operating. |
| 7 | Audit trail maintenance | Regulators and auditors expect a clear, immutable record. |
| 8 | Record retention | Legal requirement to keep records for N years (varies by jurisdiction). |
| 9 | Annual audit (if required) | Mandatory for certain entities (LLCs above threshold, public companies). |
| 10 | Foreign bank account reporting (FBAR) | High penalties for nondisclosure. |

### 3.4 From an Operational Efficiency View

*Where should automation have the biggest time-savings impact?*

| Rank | Operation | Why |
|------|-----------|-----|
| 1 | Transaction categorisation | Currently manual in most SMBs; AI can do it in seconds. |
| 2 | Bank reconciliation | Hours of manual clicking every month. |
| 3 | Receipt / document capture | Paper receipts are a nightmare to organise. |
| 4 | Accounts receivable follow-up | Sending reminders is repetitive and easily automated. |
| 5 | Sales invoicing | Template-driven; should be one click or automatic. |
| 6 | Expense recording | Mileage, meals, travel — tedious data entry. |
| 7 | P&L / management report generation | Should be real-time, not a month-end scramble. |
| 8 | Cash flow forecasting | Manual spreadsheet work that's always out of date. |
| 9 | Sales tax calculation | Easy to get wrong manually; rule-based systems are perfect. |
| 10 | Payroll processing | The penalty for error is high, but the process itself is formulaic. |

---

## 4. Summary Heatmap

| Category | Owner Importance | Accountant Importance | Compliance Importance | Automation Potential |
|----------|:---------------:|:--------------------:|:--------------------:|:-------------------:|
| Transaction Processing | ★★★★★ | ★★★★ | ★★★ | ★★★★★ |
| Reconciliation | ★★★ | ★★★★★ | ★★★ | ★★★★★ |
| Payroll & Employee | ★★★★ | ★★★★ | ★★★★★ | ★★★★ |
| Tax & Compliance | ★★★★ | ★★★★★ | ★★★★★ | ★★★ |
| Reporting & Analysis | ★★★★★ | ★★★★ | ★★ | ★★★★ |
| Planning & Forecasting | ★★★★★ | ★★★ | ★ | ★★★ |
| Treasury & Cash Mgmt | ★★★★★ | ★★ | ★★ | ★★★ |
| Record Keeping & Audit | ★★ | ★★★★★ | ★★★★★ | ★★★★ |

---

## 5. Key Takeaways for AutoFi

1. **Start with Transaction Processing + Reconciliation.** These are high-frequency, high-automation-potential, and foundational to everything else. An SMB that can't trust its transaction data can't do anything else well.

2. **Cash flow visibility is the owner's #1 need.** Any product that gives the owner a reliable, real-time cash forecast adds immediate value.

3. **Compliance is high-stakes but low-volume.** Filing happens 4-12 times a year per obligation, but errors are expensive. Automate the calculation; keep human-in-the-loop for submission.

4. **Payroll is the hardest problem.** Complex rules, jurisdiction-specific, high liability. Consider partnering with a payroll API (Gusto, Rippling, ADP) rather than building from scratch.

5. **Reporting is the payoff.** All the upstream work (categorisation, reconciliation, forecasting) ultimately serves the reports that owners and accountants use to make decisions.

6. **Record keeping is the infrastructure.** Ignore it at your peril — a system that doesn't maintain a proper audit trail will not be trusted by accountants or regulators.
