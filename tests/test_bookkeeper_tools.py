"""Unit tests for bookkeeper agent tools using TestModel + in-memory SQLite."""

import datetime
import tempfile
from pathlib import Path

import pytest
from pydantic_ai import RunContext
from sqlmodel import Session, SQLModel, create_engine, select

from agents.bookkeeper import (
    BookkeeperDeps,
    add_customer,
    add_vendor,
    auto_categorise,
    categorise_transaction,
    confirm_match,
    find_unreconciled_transactions,
    link_to_bill,
    link_to_invoice,
    list_accounts,
    list_bills,
    list_customers,
    list_gl_accounts,
    list_invoices,
    list_transactions,
    list_vendors,
    show_bill,
    show_invoice,
    suggest_matches,
)
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


@pytest.fixture
def db_path() -> Path:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Account(name="Test Account", type="checking", currency="INR"))
        session.commit()
        for i in range(3):
            session.add(
                Transaction(
                    account_id=1,
                    date=datetime.date(2025, 1, i + 1),
                    description=f"Transaction {i}",
                    amount=100.0 + i,
                    hash=f"hash_{i}",
                )
            )
        session.commit()
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def ctx(db_path: Path) -> RunContext[BookkeeperDeps]:
    return RunContext[BookkeeperDeps](
        deps=BookkeeperDeps(db_path=db_path),
        model=None,
        usage=None,
        prompt="test",
        retry=0,
    )


def _add_test_tx(session: Session, description: str, amount: float) -> Transaction:
    tx = Transaction(
        account_id=1,
        date=datetime.date(2025, 2, 1),
        description=description,
        amount=amount,
        currency="INR",
        hash=f"hash_{description}_{amount}",
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# categorise_transaction
# ---------------------------------------------------------------------------


def test_categorise_transaction_ok(ctx: RunContext[BookkeeperDeps]) -> None:
    result = categorise_transaction(ctx, tx_id=1, category="Food")
    assert "categorised as 'Food'" in result

    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 1)
        assert t is not None
        assert t.category == "Food"


def test_categorise_transaction_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = categorise_transaction(ctx, tx_id=999, category="Rent")
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# list_transactions
# ---------------------------------------------------------------------------


def test_list_transactions_matches(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        _add_test_tx(session, "Starbucks Coffee", 5.50)
        _add_test_tx(session, "Starbucks Latte", 6.00)
        _add_test_tx(session, "Amazon Books", 15.00)

    result = list_transactions(ctx, query="Starbucks", limit=5)
    assert "Starbucks Coffee" in result
    assert "Starbucks Latte" in result
    assert "Amazon Books" not in result
    assert "5.50" in result
    assert "6.00" in result


def test_list_transactions_no_match(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_transactions(ctx, query="ZZZZNOTFOUND", limit=5)
    assert "No transactions found" in result


# ---------------------------------------------------------------------------
# list_accounts
# ---------------------------------------------------------------------------


def test_list_accounts(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_accounts(ctx)
    assert "Test Account" in result or "No accounts found" in result


# ---------------------------------------------------------------------------
# list_gl_accounts
# ---------------------------------------------------------------------------


def test_list_gl_accounts_all(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(GLAccount(code="1000", name="Test Asset", type="asset"))
        session.add(GLAccount(code="2000", name="Test Expense", type="expense"))
        session.commit()

    result = list_gl_accounts(ctx)
    assert "Test Asset" in result
    assert "Test Expense" in result
    assert "1000" in result
    assert "2000" in result


def test_list_gl_accounts_filtered(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(GLAccount(code="1000", name="Test Asset", type="asset"))
        session.add(GLAccount(code="2000", name="Test Expense", type="expense"))
        session.commit()

    result = list_gl_accounts(ctx, acct_type="asset")
    assert "Test Asset" in result
    assert "Test Expense" not in result


def test_list_gl_accounts_empty(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_gl_accounts(ctx)
    assert "No GL accounts found" in result or "1000" not in result


# ---------------------------------------------------------------------------
# auto_categorise
# ---------------------------------------------------------------------------


def test_auto_categorise_matches(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    gl = GLAccount(code="6000", name="Food & Dining", type="expense")
    for session in get_session(ctx.deps.db_path):
        session.add(gl)
        session.commit()
        session.refresh(gl)
        session.add(
            CategoryRule(
                pattern="starbucks",
                gl_account_id=gl.id,
                category="Food & Dining",
                priority=1,
            )
        )
        session.add(
            CategoryRule(
                pattern="amazon",
                gl_account_id=gl.id,
                category="Shopping",
                priority=2,
            )
        )
        session.commit()
        _add_test_tx(session, "Starbucks Coffee", 5.50)

    result = auto_categorise(ctx, tx_id=4)
    assert "auto-categorised" in result.lower()
    assert "Food & Dining" in result or "starbucks" in result.lower()

    # Verify DB was updated
    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 4)
        assert t is not None
        assert t.category == "Food & Dining"
        assert t.gl_account_id is not None


def test_auto_categorise_no_match(ctx: RunContext[BookkeeperDeps]) -> None:
    result = auto_categorise(ctx, tx_id=1)
    assert "No matching CategoryRule" in result


def test_auto_categorise_tx_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = auto_categorise(ctx, tx_id=999)
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# list_vendors
# ---------------------------------------------------------------------------


def test_list_vendors(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(Vendor(name="Acme Corp", email="acme@example.com"))
        session.add(Vendor(name="Beta Ltd", email="beta@example.com"))
        session.commit()

    result = list_vendors(ctx)
    assert "Acme Corp" in result
    assert "Beta Ltd" in result


def test_list_vendors_query(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(Vendor(name="Acme Corp", email="acme@example.com"))
        session.add(Vendor(name="Beta Ltd", email="beta@example.com"))
        session.commit()

    result = list_vendors(ctx, query="acme")
    assert "Acme Corp" in result
    assert "Beta Ltd" not in result


def test_list_vendors_empty(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_vendors(ctx)
    assert "No vendors found" in result


# ---------------------------------------------------------------------------
# add_vendor
# ---------------------------------------------------------------------------


def test_add_vendor(ctx: RunContext[BookkeeperDeps]) -> None:
    result = add_vendor(ctx, name="New Vendor", email="v@example.com", phone="123")
    assert "Created vendor" in result
    assert "New Vendor" in result


# ---------------------------------------------------------------------------
# list_customers
# ---------------------------------------------------------------------------


def test_list_customers(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(Customer(name="Alpha Client"))
        session.add(Customer(name="Omega Client"))
        session.commit()

    result = list_customers(ctx)
    assert "Alpha Client" in result
    assert "Omega Client" in result


def test_list_customers_query(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(Customer(name="Alpha Client"))
        session.add(Customer(name="Omega Client"))
        session.commit()

    result = list_customers(ctx, query="omega")
    assert "Omega Client" in result
    assert "Alpha Client" not in result


def test_list_customers_empty(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_customers(ctx)
    assert "No customers found" in result


# ---------------------------------------------------------------------------
# add_customer
# ---------------------------------------------------------------------------


def test_add_customer(ctx: RunContext[BookkeeperDeps]) -> None:
    result = add_customer(ctx, name="New Customer", email="c@example.com")
    assert "Created customer" in result
    assert "New Customer" in result


# ---------------------------------------------------------------------------
# list_invoices
# ---------------------------------------------------------------------------


def test_list_invoices(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Test Customer")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV-001",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            status="sent",
            total=1000.0,
        )
        session.add(inv)
        session.commit()

    result = list_invoices(ctx)
    assert "INV-001" in result
    assert "Test Customer" in result
    assert "1000.00" in result


def test_list_invoices_filtered(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Test Customer")
        session.add(c)
        session.commit()
        session.refresh(c)
        session.add(
            Invoice(
                invoice_no="INV-001",
                customer_id=c.id,
                issue_date=datetime.date(2025, 1, 15),
                due_date=datetime.date(2025, 2, 15),
                status="sent",
                total=1000.0,
            )
        )
        session.add(
            Invoice(
                invoice_no="INV-002",
                customer_id=c.id,
                issue_date=datetime.date(2025, 1, 20),
                due_date=datetime.date(2025, 2, 20),
                status="paid",
                total=500.0,
            )
        )
        session.commit()

    result = list_invoices(ctx, status="paid")
    assert "INV-002" in result
    assert "INV-001" not in result


def test_list_invoices_empty(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_invoices(ctx)
    assert "No invoices found" in result


# ---------------------------------------------------------------------------
# show_invoice
# ---------------------------------------------------------------------------


def test_show_invoice(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Show Customer")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV-SHOW",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            status="sent",
            subtotal=800.0,
            tax_amount=80.0,
            total=880.0,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)
        session.add(
            InvoiceLineItem(
                invoice_id=inv.id,
                description="Consulting",
                quantity=10,
                unit_price=80.0,
                amount=800.0,
            )
        )
        session.commit()

    result = show_invoice(ctx, id=1)
    assert "INV-SHOW" in result
    assert "Show Customer" in result
    assert "Consulting" in result
    assert "880.00" in result


def test_show_invoice_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = show_invoice(ctx, id=999)
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# list_bills
# ---------------------------------------------------------------------------


def test_list_bills(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        v = Vendor(name="Bill Vendor")
        session.add(v)
        session.commit()
        session.refresh(v)
        session.add(
            Bill(
                bill_no="BILL-001",
                vendor_id=v.id,
                issue_date=datetime.date(2025, 1, 15),
                due_date=datetime.date(2025, 2, 15),
                status="pending",
                total=500.0,
            )
        )
        session.commit()

    result = list_bills(ctx)
    assert "BILL-001" in result
    assert "Bill Vendor" in result
    assert "500.00" in result


def test_list_bills_filtered(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        v = Vendor(name="Bill Vendor")
        session.add(v)
        session.commit()
        session.refresh(v)
        session.add(
            Bill(
                bill_no="BILL-001",
                vendor_id=v.id,
                issue_date=datetime.date(2025, 1, 15),
                due_date=datetime.date(2025, 2, 15),
                status="pending",
                total=500.0,
            )
        )
        session.add(
            Bill(
                bill_no="BILL-002",
                vendor_id=v.id,
                issue_date=datetime.date(2025, 1, 20),
                due_date=datetime.date(2025, 2, 20),
                status="paid",
                total=300.0,
            )
        )
        session.commit()

    result = list_bills(ctx, status="pending")
    assert "BILL-001" in result
    assert "BILL-002" not in result


def test_list_bills_empty(ctx: RunContext[BookkeeperDeps]) -> None:
    result = list_bills(ctx)
    assert "No bills found" in result


# ---------------------------------------------------------------------------
# show_bill
# ---------------------------------------------------------------------------


def test_show_bill(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        v = Vendor(name="Show Vendor")
        session.add(v)
        session.commit()
        session.refresh(v)
        b = Bill(
            bill_no="BILL-SHOW",
            vendor_id=v.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            status="pending",
            subtotal=400.0,
            tax_amount=40.0,
            total=440.0,
        )
        session.add(b)
        session.commit()
        session.refresh(b)
        session.add(
            BillLineItem(
                bill_id=b.id,
                description="Office Supplies",
                quantity=5,
                unit_price=80.0,
                amount=400.0,
            )
        )
        session.commit()

    result = show_bill(ctx, id=1)
    assert "BILL-SHOW" in result
    assert "Show Vendor" in result
    assert "Office Supplies" in result
    assert "440.00" in result


def test_show_bill_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = show_bill(ctx, id=999)
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# Reconciliation: link_to_invoice
# ---------------------------------------------------------------------------


def test_link_to_invoice_ok(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Recon Customer")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV-RECON",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            status="sent",
            total=1000.0,
        )
        session.add(inv)
        session.commit()

    result = link_to_invoice(ctx, tx_id=1, invoice_id=1)
    assert "linked" in result.lower()
    assert "invoice 1" in result.lower()

    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 1)
        assert t is not None
        assert t.invoice_id == 1


def test_link_to_invoice_tx_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Recon Customer")
        session.add(c)
        session.commit()
        session.refresh(c)
        session.add(
            Invoice(
                invoice_no="INV-RECON",
                customer_id=c.id,
                issue_date=datetime.date(2025, 1, 15),
                due_date=datetime.date(2025, 2, 15),
                status="sent",
                total=1000.0,
            )
        )
        session.commit()

    result = link_to_invoice(ctx, tx_id=999, invoice_id=1)
    assert "not found" in result.lower()


def test_link_to_invoice_inv_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = link_to_invoice(ctx, tx_id=1, invoice_id=999)
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# Reconciliation: link_to_bill
# ---------------------------------------------------------------------------


def test_link_to_bill_ok(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        v = Vendor(name="Recon Vendor")
        session.add(v)
        session.commit()
        session.refresh(v)
        b = Bill(
            bill_no="BILL-RECON",
            vendor_id=v.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            status="pending",
            total=500.0,
        )
        session.add(b)
        session.commit()

    result = link_to_bill(ctx, tx_id=1, bill_id=1)
    assert "linked" in result.lower()
    assert "bill 1" in result.lower()

    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 1)
        assert t is not None
        assert t.bill_id == 1


def test_link_to_bill_tx_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        v = Vendor(name="Recon Vendor")
        session.add(v)
        session.commit()
        session.refresh(v)
        session.add(
            Bill(
                bill_no="BILL-RECON",
                vendor_id=v.id,
                issue_date=datetime.date(2025, 1, 15),
                due_date=datetime.date(2025, 2, 15),
                status="pending",
                total=500.0,
            )
        )
        session.commit()

    result = link_to_bill(ctx, tx_id=999, bill_id=1)
    assert "not found" in result.lower()


def test_link_to_bill_bill_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = link_to_bill(ctx, tx_id=1, bill_id=999)
    assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# find_unreconciled_transactions
# ---------------------------------------------------------------------------


def test_find_unreconciled_all_reconciled(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="C")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 1),
            due_date=datetime.date(2025, 2, 1),
            total=100.0,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)
        for tx in session.exec(select(Transaction)).all():
            tx.invoice_id = inv.id
            session.add(tx)
        session.commit()

    result = find_unreconciled_transactions(ctx)
    assert "No unreconciled transactions" in result


def test_find_unreconciled_shows_unmatched(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        session.add(
            Transaction(
                account_id=1,
                date=datetime.date(2025, 6, 1),
                description="Unmatched tx",
                amount=100.0,
                hash="unmatched_hash",
            )
        )
        session.commit()

    result = find_unreconciled_transactions(ctx)
    assert "Unmatched tx" in result
    assert "100.00" in result


def test_find_unreconciled_skips_reconciled(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="C")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 1),
            due_date=datetime.date(2025, 2, 1),
            total=100.0,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)
        session.add(
            Transaction(
                account_id=1,
                date=datetime.date(2025, 1, 15),
                description="Linked tx",
                amount=100.0,
                invoice_id=inv.id,
                hash="linked_hash",
            )
        )
        session.commit()

    result = find_unreconciled_transactions(ctx)
    assert "Linked tx" not in result


# ---------------------------------------------------------------------------
# suggest_matches
# ---------------------------------------------------------------------------


def test_suggest_matches_finds_invoice(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Client A")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV-100",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            total=5000.0,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)
        # tx #4 has the same amount and date as the invoice
        session.add(
            Transaction(
                account_id=1,
                date=datetime.date(2025, 1, 15),
                description="Client Payment INV-100",
                amount=5000.0,
                hash="match_tx_hash",
            )
        )
        session.commit()

        result = suggest_matches(ctx, tx_id=4)
        assert "INV-100" in result
        assert "Client A" in result
        assert "5000.00" in result  # amount shown for candidate


def test_suggest_matches_tx_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = suggest_matches(ctx, tx_id=999)
    assert "not found" in result.lower()


def test_suggest_matches_already_reconciled(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="C")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 1),
            due_date=datetime.date(2025, 2, 1),
            total=100.0,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)
        tx = session.get(Transaction, 1)
        assert tx is not None
        tx.invoice_id = inv.id
        session.add(tx)
        session.commit()

    result = suggest_matches(ctx, tx_id=1)
    assert "already reconciled" in result.lower()


def test_suggest_matches_no_candidates(ctx: RunContext[BookkeeperDeps]) -> None:
    # tx #1 exists but no invoices/bills
    result = suggest_matches(ctx, tx_id=1)
    assert "No matching" in result


# ---------------------------------------------------------------------------
# confirm_match
# ---------------------------------------------------------------------------


def test_confirm_match_to_invoice(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="Client B")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV-CONF",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            total=1000.0,
        )
        session.add(inv)
        session.commit()

    result = confirm_match(ctx, tx_id=1, doc_id=1, doc_type="invoice")
    assert "matched" in result.lower()
    assert "invoice 1" in result.lower()

    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 1)
        assert t is not None
        assert t.invoice_id == 1
        inv = session.get(Invoice, 1)
        assert inv is not None
        assert inv.paid_amount == 100.0  # tx #1 amount


def test_confirm_match_to_bill(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        v = Vendor(name="Vendor A")
        session.add(v)
        session.commit()
        session.refresh(v)
        b = Bill(
            bill_no="BILL-CONF",
            vendor_id=v.id,
            issue_date=datetime.date(2025, 1, 15),
            due_date=datetime.date(2025, 2, 15),
            total=500.0,
        )
        session.add(b)
        session.commit()

    result = confirm_match(ctx, tx_id=1, doc_id=1, doc_type="bill")
    assert "matched" in result.lower()
    assert "bill 1" in result.lower()

    for session in get_session(ctx.deps.db_path):
        t = session.get(Transaction, 1)
        assert t is not None
        assert t.bill_id == 1
        bill = session.get(Bill, 1)
        assert bill is not None
        assert bill.paid_amount == 100.0


def test_confirm_match_invalid_doc_type(ctx: RunContext[BookkeeperDeps]) -> None:
    result = confirm_match(ctx, tx_id=1, doc_id=1, doc_type="widget")
    assert "invalid" in result.lower()


def test_confirm_match_tx_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = confirm_match(ctx, tx_id=999, doc_id=1, doc_type="invoice")
    assert "not found" in result.lower()


def test_confirm_match_doc_not_found(ctx: RunContext[BookkeeperDeps]) -> None:
    result = confirm_match(ctx, tx_id=1, doc_id=999, doc_type="invoice")
    assert "not found" in result.lower()


def test_confirm_match_already_reconciled(ctx: RunContext[BookkeeperDeps]) -> None:
    from data.db import get_session, init_db

    init_db(ctx.deps.db_path)
    for session in get_session(ctx.deps.db_path):
        c = Customer(name="C")
        session.add(c)
        session.commit()
        session.refresh(c)
        inv = Invoice(
            invoice_no="INV",
            customer_id=c.id,
            issue_date=datetime.date(2025, 1, 1),
            due_date=datetime.date(2025, 2, 1),
            total=100.0,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)
        tx = session.get(Transaction, 1)
        assert tx is not None
        tx.invoice_id = inv.id
        session.add(tx)
        session.commit()

    result = confirm_match(ctx, tx_id=1, doc_id=1, doc_type="invoice")
    assert "already reconciled" in result.lower()
