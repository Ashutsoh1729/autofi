import datetime
import hashlib

from sqlmodel import Field, SQLModel


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: str = "checking"
    currency: str = "INR"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class Transaction(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id")
    date: datetime.date
    description: str
    amount: float
    currency: str = "INR"
    category: str | None = None
    notes: str | None = None
    hash: str = Field(unique=True, index=True)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @staticmethod
    def compute_hash(tx_date: datetime.date, description: str, amount: float) -> str:
        raw = f"{tx_date.isoformat()}|{description.strip().lower()}|{amount}"
        return hashlib.sha256(raw.encode()).hexdigest()
