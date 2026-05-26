import datetime
from pathlib import Path

from sqlmodel import Session, select

from data.db import get_session, init_db
from data.models import Account, Transaction


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
