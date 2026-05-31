import datetime
from pathlib import Path

from sqlmodel import Session, select

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
from data.seed import DEFAULT_GL_ACCOUNTS


def test_init_db_creates_tables(tmp_path: Path):
    db = tmp_path / "test.db"
    engine = init_db(db)
    assert engine is not None


def test_insert_and_query_account(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        acct = Account(name="Test Account", type="savings", currency="INR")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        assert acct.id is not None
        assert acct.name == "Test Account"
        assert acct.type == "savings"

        fetched = session.exec(select(Account).where(Account.name == "Test Account")).first()
        assert fetched is not None
        assert fetched.id == acct.id


def test_insert_and_query_transactions(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        acct = Account(name="Business Account")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        tx_hash = Transaction.compute_hash(datetime.date(2025, 1, 15), "Office Supplies", 120.50)
        tx = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 1, 15),
            description="Office Supplies",
            amount=120.50,
            currency="INR",
            hash=tx_hash,
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)

        assert tx.id is not None
        assert tx.description == "Office Supplies"
        assert tx.amount == 120.50

        txs = session.exec(
            select(Transaction).where(Transaction.account_id == acct.id)
        ).all()
        assert len(txs) == 1


def test_dedup_rejects_duplicate_hash(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        acct = Account(name="Business Account")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        tx_hash = Transaction.compute_hash(datetime.date(2025, 1, 15), "Office Supplies", 120.50)
        tx1 = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 1, 15),
            description="Office Supplies",
            amount=120.50,
            hash=tx_hash,
        )
        session.add(tx1)
        session.commit()

        tx2 = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 1, 15),
            description="Office Supplies",
            amount=120.50,
            hash=tx_hash,
        )
        session.add(tx2)
        import pytest
        with pytest.raises(Exception):
            session.commit()


def test_compute_hash_consistency():
    h1 = Transaction.compute_hash(datetime.date(2025, 6, 1), "Coffee", 4.50)
    h2 = Transaction.compute_hash(datetime.date(2025, 6, 1), "Coffee", 4.50)
    assert h1 == h2


def test_compute_hash_case_insensitive():
    h1 = Transaction.compute_hash(datetime.date(2025, 6, 1), "Coffee", 4.50)
    h2 = Transaction.compute_hash(datetime.date(2025, 6, 1), "coffee", 4.50)
    assert h1 == h2


def test_list_transactions_with_filter(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        acct = Account(name="Checking")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        for i in range(5):
            tx = Transaction(
                account_id=acct.id,
                date=datetime.date(2025, 1, 1 + i),
                description=f"Tx {i}",
                amount=float(i * 10),
                hash=Transaction.compute_hash(datetime.date(2025, 1, 1 + i), f"Tx {i}", float(i * 10)),
            )
            session.add(tx)
        session.commit()

        txs = session.exec(
            select(Transaction).where(Transaction.account_id == acct.id).limit(3)
        ).all()
        assert len(txs) == 3


def test_get_db_path_returns_path():
    from util.config import get_db_path
    path = get_db_path()
    assert str(path).endswith("autofi.db")
    assert path.parent.name == "autofi"


def test_glaccount_crud(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        gl = GLAccount(code="6000", name="Custom Account", type="expense")
        session.add(gl)
        session.commit()
        session.refresh(gl)

        assert gl.id is not None
        assert gl.code == "6000"
        assert gl.name == "Custom Account"
        assert gl.type == "expense"

        fetched = session.exec(select(GLAccount).where(GLAccount.code == "6000")).first()
        assert fetched is not None
        assert fetched.id == gl.id


def test_glaccount_transaction_fk(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        gl = GLAccount(code="6001", name="Test GL", type="expense")
        session.add(gl)
        session.commit()
        session.refresh(gl)

        acct = Account(name="Checking")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        tx = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 6, 1),
            description="Monthly Rent",
            amount=20000,
            gl_account_id=gl.id,
            hash=Transaction.compute_hash(datetime.date(2025, 6, 1), "Monthly Rent", 20000),
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)

        assert tx.gl_account_id == gl.id


def test_vendor_crud(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        v = Vendor(name="AWS India", gstin="29ABCDE1234F1Z5")
        session.add(v)
        session.commit()
        session.refresh(v)

        assert v.id is not None
        assert v.name == "AWS India"
        assert v.gstin == "29ABCDE1234F1Z5"

        fetched = session.exec(select(Vendor).where(Vendor.name == "AWS India")).first()
        assert fetched is not None


def test_customer_crud(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        c = Customer(name="Acme Corp", email="billing@acme.com")
        session.add(c)
        session.commit()
        session.refresh(c)

        assert c.id is not None
        assert c.name == "Acme Corp"
        assert c.email == "billing@acme.com"


def test_invoice_with_line_items_cascade(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        gl = GLAccount(code="6002", name="Revenue", type="income")
        session.add(gl)
        session.commit()
        session.refresh(gl)

        c = Customer(name="Client A")
        session.add(c)
        session.commit()
        session.refresh(c)

        inv = Invoice(
            invoice_no="INV-001",
            customer_id=c.id,
            issue_date=datetime.date(2025, 6, 1),
            due_date=datetime.date(2025, 7, 1),
            subtotal=10000,
            tax_amount=1800,
            total=11800,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)

        line = InvoiceLineItem(
            invoice_id=inv.id,
            description="Consulting",
            quantity=1,
            unit_price=10000,
            amount=10000,
            gl_account_id=gl.id,
        )
        session.add(line)
        session.commit()
        session.refresh(line)

        assert line.id is not None
        assert line.invoice_id == inv.id

        lines = session.exec(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == inv.id)
        ).all()
        assert len(lines) == 1

        session.delete(inv)
        session.commit()
        remaining = session.exec(
            select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == inv.id)
        ).all()
        assert len(remaining) == 0


def test_bill_with_line_items_cascade(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        gl = GLAccount(code="6003", name="Software & Subscriptions", type="expense")
        session.add(gl)
        session.commit()
        session.refresh(gl)

        v = Vendor(name="AWS India")
        session.add(v)
        session.commit()
        session.refresh(v)

        bill = Bill(
            bill_no="AWS-MAY",
            vendor_id=v.id,
            issue_date=datetime.date(2025, 5, 1),
            due_date=datetime.date(2025, 6, 1),
            subtotal=5000,
            tax_amount=900,
            total=5900,
        )
        session.add(bill)
        session.commit()
        session.refresh(bill)

        line = BillLineItem(
            bill_id=bill.id,
            description="EC2 Compute",
            quantity=1,
            unit_price=5000,
            amount=5000,
            gl_account_id=gl.id,
        )
        session.add(line)
        session.commit()
        session.refresh(line)

        assert line.id is not None
        assert line.bill_id == bill.id

        lines = session.exec(
            select(BillLineItem).where(BillLineItem.bill_id == bill.id)
        ).all()
        assert len(lines) == 1

        session.delete(bill)
        session.commit()
        remaining = session.exec(
            select(BillLineItem).where(BillLineItem.bill_id == bill.id)
        ).all()
        assert len(remaining) == 0


def test_transaction_reconciliation_fks(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        acct = Account(name="HDFC Current")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        gl = GLAccount(code="6004", name="Revenue", type="income")
        session.add(gl)
        session.commit()
        session.refresh(gl)

        c = Customer(name="Client A")
        session.add(c)
        session.commit()
        session.refresh(c)

        v = Vendor(name="AWS India")
        session.add(v)
        session.commit()
        session.refresh(v)

        inv = Invoice(
            invoice_no="INV-002",
            customer_id=c.id,
            issue_date=datetime.date(2025, 6, 1),
            due_date=datetime.date(2025, 7, 1),
            subtotal=10000,
            tax_amount=1800,
            total=11800,
        )
        session.add(inv)
        session.commit()
        session.refresh(inv)

        bill = Bill(
            bill_no="AWS-JUN",
            vendor_id=v.id,
            issue_date=datetime.date(2025, 6, 1),
            due_date=datetime.date(2025, 7, 1),
            subtotal=5000,
            tax_amount=900,
            total=5900,
        )
        session.add(bill)
        session.commit()
        session.refresh(bill)

        tx_in = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 6, 5),
            description="Payment from Client A - INV-002",
            amount=11800,
            gl_account_id=gl.id,
            invoice_id=inv.id,
            hash=Transaction.compute_hash(datetime.date(2025, 6, 5), "Payment from Client A - INV-002", 11800),
        )
        session.add(tx_in)
        session.commit()
        session.refresh(tx_in)

        tx_out = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 6, 6),
            description="AWS India - AWS-JUN",
            amount=-5900,
            gl_account_id=gl.id,
            bill_id=bill.id,
            hash=Transaction.compute_hash(datetime.date(2025, 6, 6), "AWS India - AWS-JUN", -5900),
        )
        session.add(tx_out)
        session.commit()
        session.refresh(tx_out)

        assert tx_in.invoice_id == inv.id
        assert tx_in.bill_id is None
        assert tx_out.bill_id == bill.id
        assert tx_out.invoice_id is None


def test_transaction_reconciliation_fks_nullable(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        acct = Account(name="Checking")
        session.add(acct)
        session.commit()
        session.refresh(acct)

        tx = Transaction(
            account_id=acct.id,
            date=datetime.date(2025, 1, 1),
            description="Unlinked tx",
            amount=100,
            hash=Transaction.compute_hash(datetime.date(2025, 1, 1), "Unlinked tx", 100),
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)

        assert tx.gl_account_id is None
        assert tx.invoice_id is None
        assert tx.bill_id is None


def test_categoryrule_matching(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        gl = GLAccount(code="6005", name="Software & Subscriptions", type="expense")
        session.add(gl)
        session.commit()
        session.refresh(gl)

        rule = CategoryRule(
            pattern="UBER%",
            gl_account_id=gl.id,
            category="Software & Subscriptions",
            priority=10,
        )
        session.add(rule)
        session.commit()
        session.refresh(rule)

        assert rule.id is not None
        assert rule.pattern == "UBER%"
        assert rule.gl_account_id == gl.id
        assert rule.is_active is True

        rules = session.exec(
            select(CategoryRule).where(CategoryRule.is_active)
        ).all()
        assert len(rules) == 1


def test_seed_gl_accounts_idempotent(tmp_path: Path):
    db = tmp_path / "test.db"
    init_db(db)

    session: Session
    for session in get_session(db):
        accounts = session.exec(select(GLAccount)).all()
        assert len(accounts) == len(DEFAULT_GL_ACCOUNTS)
        codes = [a.code for a in accounts]
        assert "1100" in codes
        assert "4100" in codes
        assert "5110" in codes

    init_db(db)
    for session in get_session(db):
        accounts = session.exec(select(GLAccount)).all()
        assert len(accounts) == len(DEFAULT_GL_ACCOUNTS)
