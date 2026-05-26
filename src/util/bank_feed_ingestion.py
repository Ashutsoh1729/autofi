import datetime
from dataclasses import dataclass, field
from pathlib import Path

from sqlmodel import Session, col, select

from data.db import get_session, init_db

from data.models import Account, Transaction

from util.config import get_db_path

from util.csv_parser import RawTransaction, parse_csv


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)
    account_id: int | None = None
    account_name: str = ""


def _resolve_account(
    session: Session,
    csv_rows: list[RawTransaction],
    account_id: str | None,
) -> tuple[Account, bool]:
    if account_id is not None:
        acct = session.get(Account, int(account_id))
        if acct is None:
            raise ValueError(f"Account with id={account_id} not found")
        return acct, False

    accounts = session.exec(select(Account)).all()
    if not accounts:
        acct = Account(name="Default Account", currency="INR")
        session.add(acct)
        session.commit()
        session.refresh(acct)
        return acct, True

    if len(accounts) == 1:
        return accounts[0], False

    raise ValueError(
        "Multiple accounts exist. Use --account-id to specify which account to import into."
    )


def _existing_hashes(session: Session) -> set[str]:
    stmt = select(Transaction.hash)
    return set(session.exec(stmt).all())


def import_csv(
    filepath: str | Path,
    account_id: str | None = None,
    dry_run: bool = False,
) -> ImportResult:
    raw_txs = parse_csv(filepath)

    db_path = get_db_path()
    init_db(db_path)

    result = ImportResult()

    session: Session
    for session in get_session(db_path):
        try:
            acct, created = _resolve_account(session, raw_txs, account_id)
            result.account_id = acct.id
            result.account_name = acct.name

            existing = _existing_hashes(session)
            new_txs: list[Transaction] = []

            for i, raw in enumerate(raw_txs, start=2):
                tx_hash = Transaction.compute_hash(raw.date, raw.description, raw.amount)
                if tx_hash in existing:
                    result.skipped += 1
                    continue

                tx = Transaction(
                    account_id=acct.id,
                    date=raw.date,
                    description=raw.description,
                    amount=raw.amount,
                    currency=raw.currency or acct.currency,
                    hash=tx_hash,
                )
                new_txs.append(tx)
                existing.add(tx_hash)

            if not dry_run and new_txs:
                for tx in new_txs:
                    session.add(tx)
                session.commit()

            result.imported = len(new_txs)
        except Exception:
            session.rollback()
            raise

    return result


def list_transactions(
    account_id: int | None = None,
    days: int | None = None,
    limit: int = 100,
) -> list[Transaction]:
    db_path = get_db_path()
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        stmt = select(Transaction).order_by(col(Transaction.date).desc())
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if days is not None:
            cutoff = datetime.date.today() - datetime.timedelta(days=days)
            stmt = stmt.where(Transaction.date >= cutoff)
        stmt = stmt.limit(limit)
        return list(session.exec(stmt).all())
    return []


def get_transaction_stats() -> dict:
    db_path = get_db_path()
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
                    select(Transaction).where(Transaction.account_id == acct.id)
                ).all()
            )
            per_account[acct.name] = cnt

        dates = [t.date for t in total]
        date_range: str | None = None
        if dates:
            date_range = f"{min(dates).isoformat()} to {max(dates).isoformat()}"

        return {
            "total_transactions": total_count,
            "per_account": per_account,
            "date_range": date_range,
        }
    return {}
