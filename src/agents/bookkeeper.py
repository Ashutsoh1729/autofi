"""Bookkeeper agent — transaction management and chart of accounts."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from sqlmodel import Session, col, select

from agents.settings import create_agent_model
from data.db import get_session, init_db
from data.models import (
    Account,
    Bill,
    BillLineItem,
    CategoryRule,
    Customer,
    GLAccount,
    Invoice,
    InvoiceLineItem,
    Transaction,
    Vendor,
)
from util.config import get_db_path as _config_get_db_path

logger = logging.getLogger(__name__)


@dataclass
class BookkeeperDeps:
    """Dependencies for the bookkeeper agent."""

    db_path: Path


def _default_deps() -> BookkeeperDeps:
    return BookkeeperDeps(db_path=_config_get_db_path())


# ---------------------------------------------------------------------------
# Standalone tool functions (registered on bookkeeper_agent below)
# ---------------------------------------------------------------------------


def categorise_transaction(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
    category: str,
) -> str:
    """Categorise a transaction by its ID.

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The ID of the transaction to categorise.
        category: The category label (e.g. "Food", "Rent", "Salary").

    Returns:
        A confirmation message.

    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        t = session.get(Transaction, tx_id)
        if t is None:
            logger.warning("categorise_transaction: tx %s not found", tx_id)
            return f"Transaction {tx_id} not found."
        old = t.category
        t.category = category
        session.add(t)
        session.commit()
        logger.info("Categorised tx %s: '%s' → '%s'", tx_id, old, category)
        return f"Transaction {tx_id} categorised as '{category}'."

    logger.error("categorise_transaction: no DB session available")
    return "Error: could not connect to database."


def list_transactions(
    ctx: RunContext[BookkeeperDeps],
    query: str = "",
    limit: int = 20,
) -> str:
    """List transactions, optionally filtered by description search.

    Args:
        ctx: Bookkeeper agent context with DB path.
        query: Search term to filter by transaction description.
              Leave empty to list all transactions.
        limit: Maximum number of results (default 20).

    Returns:
        A formatted table of matching transactions.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Transaction).order_by(col(Transaction.date).desc()).limit(limit)
        if query:
            stmt = stmt.where(col(Transaction.description).ilike(f"%{query}%"))
        txs = list(session.exec(stmt).all())
        if not txs:
            return "No transactions found."

        header = (
            f"{'ID':>5}  {'Date':<12}  {'Description':<50}  "
            f"{'Amount':>10}  {'Category':<20}"
        )
        lines = [header, "-" * 100]
        for t in txs:
            cat = t.category or "—"
            lines.append(
                f"{t.id:>5}  {t.date!s:<12}  {t.description:<50}  "
                f"{t.amount:>10.2f}  {cat:<20}",
            )
        return "\n".join(lines)

    logger.error("list_transactions: no DB session available")
    return "Error: could not connect to database."


def get_transaction_stats(ctx: RunContext[BookkeeperDeps]) -> str:
    """Get summary statistics for all transactions.

    Args:
        ctx: Bookkeeper agent context with DB path.

    Returns:
        A formatted summary (total count, per-account counts, date range).
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        total = session.exec(select(Transaction)).all()
        total_count = len(total)

        accts = session.exec(select(Account)).all()
        per_account: dict[str, int] = {}
        for acct in accts:
            cnt = len(
                session.exec(
                    select(Transaction).where(Transaction.account_id == acct.id),
                ).all(),
            )
            per_account[acct.name] = cnt

        dates = [t.date for t in total]
        date_range: str | None = None
        if dates:
            date_range = f"{min(dates).isoformat()} to {max(dates).isoformat()}"

        lines = [f"Total transactions: {total_count}"]
        lines.append("Per account:")
        for name, count in per_account.items():
            lines.append(f"  {name}: {count}")
        if date_range:
            lines.append(f"Date range: {date_range}")
        return "\n".join(lines)

    return "No transactions found."


def list_accounts(ctx: RunContext[BookkeeperDeps]) -> str:
    """List all accounts in the chart of accounts with transaction counts.

    Args:
        ctx: Bookkeeper agent context with DB path.

    Returns:
        A formatted table of accounts.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        accounts = session.exec(select(Account).order_by(Account.name)).all()
        if not accounts:
            return "No accounts found."

        header = (
            f"{'ID':>3}  {'Name':<30}  {'Type':<15}  "
            f"{'Currency':<10}  {'Transactions':>12}"
        )
        lines = [header, "-" * 75]
        for acct in accounts:
            count = len(
                session.exec(
                    select(Transaction).where(Transaction.account_id == acct.id),
                ).all(),
            )
            lines.append(
                f"{acct.id:>3}  {acct.name:<30}  {acct.type:<15}  "
                f"{acct.currency:<10}  {count:>12}",
            )
        return "\n".join(lines)

    logger.error("list_accounts: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# GL Account tools
# ---------------------------------------------------------------------------


def list_gl_accounts(
    ctx: RunContext[BookkeeperDeps],
    acct_type: str | None = None,
) -> str:
    """List chart of accounts (GL accounts), optionally filtered by type.

    Args:
        ctx: Bookkeeper agent context with DB path.
        acct_type: Optional filter — one of 'asset', 'liability', 'equity',
                   'income', 'expense'. Leave empty to list all.

    Returns:
        A formatted table of GL accounts.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(GLAccount).order_by(GLAccount.code)
        if acct_type:
            stmt = stmt.where(GLAccount.type == acct_type)
        accounts = list(session.exec(stmt).all())
        if not accounts:
            return "No GL accounts found."

        header = f"{'Code':<8}  {'Name':<40}  {'Type':<12}  {'Active':>6}"
        lines = [header, "-" * 70]
        for a in accounts:
            active = "Yes" if a.is_active else "No"
            lines.append(f"{a.code:<8}  {a.name:<40}  {a.type:<12}  {active:>6}")
        return "\n".join(lines)

    logger.error("list_gl_accounts: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Auto-categorisation via CategoryRule
# ---------------------------------------------------------------------------


def auto_categorise(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
) -> str:
    """Auto-categorise a transaction by matching its description against
    active CategoryRule patterns. The highest-priority match is applied.

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The ID of the transaction to categorise.

    Returns:
        A message describing what rule matched (or that none matched).
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        tx = session.get(Transaction, tx_id)
        if tx is None:
            logger.warning("auto_categorise: tx %s not found", tx_id)
            return f"Transaction {tx_id} not found."

        rules = session.exec(
            select(CategoryRule)
            .where(CategoryRule.is_active == True)  # noqa: E712
            .order_by(CategoryRule.priority)
        ).all()

        desc_lower = tx.description.lower()
        for rule in rules:
            if rule.pattern.lower() in desc_lower:
                tx.category = rule.category
                tx.gl_account_id = rule.gl_account_id
                session.add(tx)
                session.commit()
                logger.info(
                    "Auto-categorised tx %s: pattern='%s' → category='%s', gl_account_id=%s",
                    tx_id, rule.pattern, rule.category, rule.gl_account_id,
                )
                return (
                    f"Transaction {tx_id} auto-categorised as '{rule.category}' "
                    f"(matched pattern '{rule.pattern}')."
                )

        return f"No matching CategoryRule found for transaction {tx_id}."

    logger.error("auto_categorise: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Vendor tools
# ---------------------------------------------------------------------------


def list_vendors(
    ctx: RunContext[BookkeeperDeps],
    query: str = "",
) -> str:
    """Search vendors by name.

    Args:
        ctx: Bookkeeper agent context with DB path.
        query: Search term to filter by vendor name.
               Leave empty to list all vendors.

    Returns:
        A formatted table of matching vendors.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Vendor).order_by(Vendor.name)
        if query:
            stmt = stmt.where(Vendor.name.ilike(f"%{query}%"))
        vendors = list(session.exec(stmt).all())
        if not vendors:
            return "No vendors found."

        header = f"{'ID':>3}  {'Name':<40}  {'GSTIN':<20}  {'Email':<30}  {'Phone':<15}"
        lines = [header, "-" * 112]
        for v in vendors:
            gstin = v.gstin or "—"
            email = v.email or "—"
            phone = v.phone or "—"
            lines.append(
                f"{v.id:>3}  {v.name:<40}  {gstin:<20}  {email:<30}  {phone:<15}"
            )
        return "\n".join(lines)

    logger.error("list_vendors: no DB session available")
    return "Error: could not connect to database."


def add_vendor(
    ctx: RunContext[BookkeeperDeps],
    name: str,
    gstin: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> str:
    """Add a new vendor (a counterparty you pay money to).

    Args:
        ctx: Bookkeeper agent context with DB path.
        name: Vendor name.
        gstin: Optional GSTIN (India).
        email: Optional email address.
        phone: Optional phone number.

    Returns:
        Confirmation with the new vendor's ID.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        vendor = Vendor(name=name, gstin=gstin, email=email, phone=phone)
        session.add(vendor)
        session.commit()
        session.refresh(vendor)
        logger.info("Created vendor: id=%s name='%s'", vendor.id, vendor.name)
        return f"Created vendor: {vendor.id} — {vendor.name}."

    logger.error("add_vendor: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Customer tools
# ---------------------------------------------------------------------------


def list_customers(
    ctx: RunContext[BookkeeperDeps],
    query: str = "",
) -> str:
    """Search customers by name.

    Args:
        ctx: Bookkeeper agent context with DB path.
        query: Search term to filter by customer name.
               Leave empty to list all customers.

    Returns:
        A formatted table of matching customers.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Customer).order_by(Customer.name)
        if query:
            stmt = stmt.where(Customer.name.ilike(f"%{query}%"))
        customers = list(session.exec(stmt).all())
        if not customers:
            return "No customers found."

        header = f"{'ID':>3}  {'Name':<40}  {'GSTIN':<20}  {'Email':<30}  {'Phone':<15}"
        lines = [header, "-" * 112]
        for c in customers:
            gstin = c.gstin or "—"
            email = c.email or "—"
            phone = c.phone or "—"
            lines.append(
                f"{c.id:>3}  {c.name:<40}  {gstin:<20}  {email:<30}  {phone:<15}"
            )
        return "\n".join(lines)

    logger.error("list_customers: no DB session available")
    return "Error: could not connect to database."


def add_customer(
    ctx: RunContext[BookkeeperDeps],
    name: str,
    gstin: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> str:
    """Add a new customer (a counterparty who pays you).

    Args:
        ctx: Bookkeeper agent context with DB path.
        name: Customer name.
        gstin: Optional GSTIN (India).
        email: Optional email address.
        phone: Optional phone number.

    Returns:
        Confirmation with the new customer's ID.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        customer = Customer(name=name, gstin=gstin, email=email, phone=phone)
        session.add(customer)
        session.commit()
        session.refresh(customer)
        logger.info("Created customer: id=%s name='%s'", customer.id, customer.name)
        return f"Created customer: {customer.id} — {customer.name}."

    logger.error("add_customer: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Invoice tools
# ---------------------------------------------------------------------------


def list_invoices(
    ctx: RunContext[BookkeeperDeps],
    status: str | None = None,
) -> str:
    """List sales invoices, optionally filtered by status.

    Args:
        ctx: Bookkeeper agent context with DB path.
        status: Optional filter — 'draft', 'sent', 'paid', 'overdue', 'cancelled'.
                Leave empty to list all.

    Returns:
        A formatted table of invoices.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Invoice).order_by(Invoice.issue_date.desc())
        if status:
            stmt = stmt.where(Invoice.status == status)
        invoices = list(session.exec(stmt).all())
        if not invoices:
            return "No invoices found."

        header = (
            f"{'ID':>3}  {'Invoice No':<20}  {'Customer':<30}  "
            f"{'Date':<12}  {'Total':>10}  {'Paid':>10}  {'Status':<12}"
        )
        lines = [header, "-" * 102]
        for inv in invoices:
            customer = session.get(Customer, inv.customer_id)
            customer_name = customer.name if customer else f"id={inv.customer_id}"
            lines.append(
                f"{inv.id:>3}  {inv.invoice_no:<20}  {customer_name:<30}  "
                f"{inv.issue_date!s:<12}  {inv.total:>10.2f}  "
                f"{inv.paid_amount:>10.2f}  {inv.status:<12}"
            )
        return "\n".join(lines)

    logger.error("list_invoices: no DB session available")
    return "Error: could not connect to database."


def show_invoice(
    ctx: RunContext[BookkeeperDeps],
    id: int,
) -> str:
    """Show full details of an invoice, including its line items.

    Args:
        ctx: Bookkeeper agent context with DB path.
        id: The invoice ID.

    Returns:
        A detailed view of the invoice.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        inv = session.get(Invoice, id)
        if inv is None:
            return f"Invoice {id} not found."

        customer = session.get(Customer, inv.customer_id)
        customer_name = customer.name if customer else f"id={inv.customer_id}"

        lines = [
            f"Invoice: {inv.invoice_no}",
            f"Customer: {customer_name}",
            f"Status:   {inv.status}",
            f"Issued:   {inv.issue_date}",
            f"Due:      {inv.due_date}",
            f"Subtotal: {inv.subtotal:.2f}",
            f"Tax:      {inv.tax_amount:.2f}",
            f"Total:    {inv.total:.2f}",
            f"Paid:     {inv.paid_amount:.2f}",
            "",
            "Line Items:",
        ]
        header = f"{'ID':>3}  {'Description':<50}  {'Qty':>6}  {'Price':>10}  {'Amount':>10}"
        lines.append(header)
        lines.append("-" * 84)
        items = session.exec(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == id)
        ).all()
        for item in items:
            lines.append(
                f"{item.id:>3}  {item.description:<50}  {item.quantity:>6.2f}  "
                f"{item.unit_price:>10.2f}  {item.amount:>10.2f}"
            )
        if inv.notes:
            lines.append("")
            lines.append(f"Notes: {inv.notes}")
        return "\n".join(lines)

    logger.error("show_invoice: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Bill tools
# ---------------------------------------------------------------------------


def list_bills(
    ctx: RunContext[BookkeeperDeps],
    status: str | None = None,
) -> str:
    """List vendor bills, optionally filtered by status.

    Args:
        ctx: Bookkeeper agent context with DB path.
        status: Optional filter — 'pending', 'approved', 'paid', 'cancelled'.
                Leave empty to list all.

    Returns:
        A formatted table of bills.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Bill).order_by(Bill.issue_date.desc())
        if status:
            stmt = stmt.where(Bill.status == status)
        bills = list(session.exec(stmt).all())
        if not bills:
            return "No bills found."

        header = (
            f"{'ID':>3}  {'Bill No':<20}  {'Vendor':<30}  "
            f"{'Date':<12}  {'Total':>10}  {'Paid':>10}  {'Status':<12}"
        )
        lines = [header, "-" * 102]
        for b in bills:
            vendor = session.get(Vendor, b.vendor_id)
            vendor_name = vendor.name if vendor else f"id={b.vendor_id}"
            lines.append(
                f"{b.id:>3}  {b.bill_no:<20}  {vendor_name:<30}  "
                f"{b.issue_date!s:<12}  {b.total:>10.2f}  "
                f"{b.paid_amount:>10.2f}  {b.status:<12}"
            )
        return "\n".join(lines)

    logger.error("list_bills: no DB session available")
    return "Error: could not connect to database."


def show_bill(
    ctx: RunContext[BookkeeperDeps],
    id: int,
) -> str:
    """Show full details of a bill, including its line items.

    Args:
        ctx: Bookkeeper agent context with DB path.
        id: The bill ID.

    Returns:
        A detailed view of the bill.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        bill = session.get(Bill, id)
        if bill is None:
            return f"Bill {id} not found."

        vendor = session.get(Vendor, bill.vendor_id)
        vendor_name = vendor.name if vendor else f"id={bill.vendor_id}"

        lines = [
            f"Bill:     {bill.bill_no}",
            f"Vendor:   {vendor_name}",
            f"Status:   {bill.status}",
            f"Issued:   {bill.issue_date}",
            f"Due:      {bill.due_date}",
            f"Subtotal: {bill.subtotal:.2f}",
            f"Tax:      {bill.tax_amount:.2f}",
            f"Total:    {bill.total:.2f}",
            f"Paid:     {bill.paid_amount:.2f}",
            "",
            "Line Items:",
        ]
        header = f"{'ID':>3}  {'Description':<50}  {'Qty':>6}  {'Price':>10}  {'Amount':>10}"
        lines.append(header)
        lines.append("-" * 84)
        items = session.exec(
            select(BillLineItem).where(BillLineItem.bill_id == id)
        ).all()
        for item in items:
            lines.append(
                f"{item.id:>3}  {item.description:<50}  {item.quantity:>6.2f}  "
                f"{item.unit_price:>10.2f}  {item.amount:>10.2f}"
            )
        if bill.notes:
            lines.append("")
            lines.append(f"Notes: {bill.notes}")
        return "\n".join(lines)

    logger.error("show_bill: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Reconciliation tools
# ---------------------------------------------------------------------------


def link_to_invoice(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
    invoice_id: int,
) -> str:
    """Link a transaction to an invoice (payment reconciliation).

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The transaction ID.
        invoice_id: The invoice ID to link to.

    Returns:
        A confirmation message.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        tx = session.get(Transaction, tx_id)
        if tx is None:
            return f"Transaction {tx_id} not found."
        inv = session.get(Invoice, invoice_id)
        if inv is None:
            return f"Invoice {invoice_id} not found."

        tx.invoice_id = invoice_id
        session.add(tx)
        session.commit()
        logger.info(
            "Linked tx %s to invoice %s", tx_id, invoice_id
        )
        return f"Transaction {tx_id} linked to invoice {invoice_id}."

    logger.error("link_to_invoice: no DB session available")
    return "Error: could not connect to database."


def link_to_bill(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
    bill_id: int,
) -> str:
    """Link a transaction to a bill (payment reconciliation).

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The transaction ID.
        bill_id: The bill ID to link to.

    Returns:
        A confirmation message.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        tx = session.get(Transaction, tx_id)
        if tx is None:
            return f"Transaction {tx_id} not found."
        bill = session.get(Bill, bill_id)
        if bill is None:
            return f"Bill {bill_id} not found."

        tx.bill_id = bill_id
        session.add(tx)
        session.commit()
        logger.info(
            "Linked tx %s to bill %s", tx_id, bill_id
        )
        return f"Transaction {tx_id} linked to bill {bill_id}."

    logger.error("link_to_bill: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# find_unreconciled_transactions
# ---------------------------------------------------------------------------


def find_unreconciled_transactions(
    ctx: RunContext[BookkeeperDeps],
    limit: int = 20,
) -> str:
    """List transactions that have not yet been reconciled to an invoice or bill.

    Args:
        ctx: Bookkeeper agent context with DB path.
        limit: Maximum number of results (default 20).

    Returns:
        A formatted list of unreconciled transactions.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = (
            select(Transaction)
            .where(Transaction.invoice_id.is_(None), Transaction.bill_id.is_(None))
            .order_by(col(Transaction.date).desc())
            .limit(limit)
        )
        txs = list(session.exec(stmt).all())
        if not txs:
            return "No unreconciled transactions found."

        header = f"{'ID':>5}  {'Date':<12}  {'Description':<50}  {'Amount':>10}"
        lines = [header, "-" * 82]
        for t in txs:
            lines.append(
                f"{t.id:>5}  {t.date!s:<12}  {t.description:<50}  {t.amount:>10.2f}"
            )
        return "\n".join(lines)

    logger.error("find_unreconciled_transactions: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# suggest_matches — find candidate invoices/bills for a transaction
# ---------------------------------------------------------------------------


def _score_description(tx_desc: str, doc_desc: str) -> float:
    """Simple token overlap score between transaction and document descriptions."""
    stop_words = {"payment", "transfer", "ref", "inv", "bill", "txn"}
    tx_tokens = {t.lower() for t in re.findall(r'\w+', tx_desc) if t.lower() not in stop_words}
    doc_tokens = {t.lower() for t in re.findall(r'\w+', doc_desc) if t.lower() not in stop_words}
    if not tx_tokens or not doc_tokens:
        return 0.0
    overlap = len(tx_tokens & doc_tokens)
    return overlap / max(len(tx_tokens), len(doc_tokens))


def suggest_matches(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
) -> str:
    """Suggest which invoice or bill a transaction likely matches.
    Candidates are scored by amount proximity, date proximity,
    and description token overlap.

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The ID of the transaction to match.

    Returns:
        A formatted list of candidate matches with scores.
    """
    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        tx = session.get(Transaction, tx_id)
        if tx is None:
            return f"Transaction {tx_id} not found."

        if tx.invoice_id is not None or tx.bill_id is not None:
            return f"Transaction {tx_id} is already reconciled."

        candidates: list[tuple[str, int, str, float, float]] = []
        tolerance = 0.01

        # Score unmatched invoices
        invoices = session.exec(
            select(Invoice).where(Invoice.status != "paid")
        ).all()
        for inv in invoices:
            amount_diff = abs(tx.amount - inv.total)
            if amount_diff > 500:
                continue
            score = 0.0
            if amount_diff <= tolerance:
                score += 2.0
            if tx.date == inv.issue_date:
                score += 1.0
            elif abs((tx.date - inv.issue_date).days) <= 1:
                score += 0.75
            elif abs((tx.date - inv.issue_date).days) <= 3:
                score += 0.5
            desc_score = _score_description(tx.description, inv.invoice_no)
            score += desc_score
            customer = session.get(Customer, inv.customer_id)
            label = customer.name if customer else f"customer#{inv.customer_id}"
            candidates.append(("invoice", inv.id, f"{inv.invoice_no} ({label})", score, inv.total))

        # Score unmatched bills
        bills = session.exec(
            select(Bill).where(Bill.status != "paid")
        ).all()
        for bill in bills:
            amount_diff = abs(tx.amount - bill.total)
            if amount_diff > 500:
                continue
            score = 0.0
            if amount_diff <= tolerance:
                score += 2.0
            if tx.date == bill.issue_date:
                score += 1.0
            elif abs((tx.date - bill.issue_date).days) <= 1:
                score += 0.75
            elif abs((tx.date - bill.issue_date).days) <= 3:
                score += 0.5
            desc_score = _score_description(tx.description, bill.bill_no)
            score += desc_score
            vendor = session.get(Vendor, bill.vendor_id)
            label = vendor.name if vendor else f"vendor#{bill.vendor_id}"
            candidates.append(("bill", bill.id, f"{bill.bill_no} ({label})", score, bill.total))

        if not candidates:
            return f"No matching invoices or bills found for transaction {tx_id}."

        candidates.sort(key=lambda c: c[3], reverse=True)

        lines = [
            f"Candidates for transaction {tx_id}: "
            f"'{tx.description}' ({tx.amount:.2f} on {tx.date})",
            "",
        ]
        header = f"{'Type':<10}  {'ID':>3}  {'Document':<50}  {'Amount':>10}  {'Score':>6}"
        lines.append(header)
        lines.append("-" * 84)
        for typ, doc_id, label, score, amount in candidates:
            lines.append(
                f"{typ:<10}  {doc_id:>3}  {label:<50}  {amount:>10.2f}  {score:>6.2f}"
            )
        return "\n".join(lines)

    logger.error("suggest_matches: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# confirm_match — link a transaction to an invoice or bill
# ---------------------------------------------------------------------------


def confirm_match(
    ctx: RunContext[BookkeeperDeps],
    tx_id: int,
    doc_id: int,
    doc_type: str,
) -> str:
    """Confirm a match between a transaction and an invoice or bill.
    Links the transaction and updates the paid amount on the document.

    Args:
        ctx: Bookkeeper agent context with DB path.
        tx_id: The transaction ID.
        doc_id: The invoice or bill ID.
        doc_type: 'invoice' or 'bill'.

    Returns:
        A confirmation message.
    """
    if doc_type not in ("invoice", "bill"):
        return f"Invalid doc_type '{doc_type}'. Must be 'invoice' or 'bill'."

    db_path = ctx.deps.db_path
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        tx = session.get(Transaction, tx_id)
        if tx is None:
            return f"Transaction {tx_id} not found."

        if tx.invoice_id is not None or tx.bill_id is not None:
            return f"Transaction {tx_id} is already reconciled."

        if doc_type == "invoice":
            doc = session.get(Invoice, doc_id)
            if doc is None:
                return f"Invoice {doc_id} not found."
            tx.invoice_id = doc_id
            doc.paid_amount = (doc.paid_amount or 0) + abs(tx.amount)
            session.add(doc)
            logger.info(
                "Reconciled tx %s to invoice %s (paid_amount: %.2f → %.2f)",
                tx_id, doc_id, doc.paid_amount - abs(tx.amount), doc.paid_amount,
            )
        else:
            doc = session.get(Bill, doc_id)
            if doc is None:
                return f"Bill {doc_id} not found."
            tx.bill_id = doc_id
            doc.paid_amount = (doc.paid_amount or 0) + abs(tx.amount)
            session.add(doc)
            logger.info(
                "Reconciled tx %s to bill %s (paid_amount: %.2f → %.2f)",
                tx_id, doc_id, doc.paid_amount - abs(tx.amount), doc.paid_amount,
            )

        session.add(tx)
        session.commit()
        return f"Transaction {tx_id} matched to {doc_type} {doc_id}."

    logger.error("confirm_match: no DB session available")
    return "Error: could not connect to database."


# ---------------------------------------------------------------------------
# Agent instance
# ---------------------------------------------------------------------------

bookkeeper_agent = Agent(
    create_agent_model("bookkeeper"),
    system_prompt=(
        "You are a bookkeeper agent specialised in financial management.\n"
        "You can categorise transactions, list transactions, get transaction stats, "
        "list accounts, manage vendors and customers, manage invoices and bills, "
        "auto-categorise transactions using rules, reconcile payments, "
        "find unreconciled transactions, suggest matches to invoices/bills, "
        "and confirm reconciliation matches.\n"
        "When asked to list, show, or view data — output the raw tool result directly. "
        "Do NOT say 'a table has been printed' or rephrase the data. "
        "Always confirm before making changes."
    ),
    deps_type=BookkeeperDeps,
    defer_model_check=True,
)

bookkeeper_agent.tool(categorise_transaction)
bookkeeper_agent.tool(list_transactions)
bookkeeper_agent.tool(get_transaction_stats)
bookkeeper_agent.tool(list_accounts)
bookkeeper_agent.tool(list_gl_accounts)
bookkeeper_agent.tool(auto_categorise)
bookkeeper_agent.tool(list_vendors)
bookkeeper_agent.tool(add_vendor)
bookkeeper_agent.tool(list_customers)
bookkeeper_agent.tool(add_customer)
bookkeeper_agent.tool(list_invoices)
bookkeeper_agent.tool(show_invoice)
bookkeeper_agent.tool(list_bills)
bookkeeper_agent.tool(show_bill)
bookkeeper_agent.tool(link_to_invoice)
bookkeeper_agent.tool(link_to_bill)
bookkeeper_agent.tool(find_unreconciled_transactions)
bookkeeper_agent.tool(suggest_matches)
bookkeeper_agent.tool(confirm_match)
