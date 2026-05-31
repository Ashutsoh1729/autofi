import datetime
import hashlib
import uuid

from sqlmodel import Field, SQLModel


class ConversationMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: str = Field(index=True)
    role: str
    content: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


def new_conversation_id() -> str:
    return str(uuid.uuid4())


class AppConfig(SQLModel, table=True):
    """Key-value store for app settings (model choice, encrypted API keys)."""

    key: str = Field(primary_key=True, max_length=64)
    value: str


class Account(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    type: str = "checking"
    currency: str = "INR"
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class GLAccount(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=16)
    name: str
    type: str
    parent_id: int | None = Field(default=None, foreign_key="glaccount.id")
    is_active: bool = Field(default=True)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class Vendor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    gstin: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class Customer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    gstin: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class Invoice(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    invoice_no: str = Field(unique=True, index=True, max_length=64)
    customer_id: int = Field(foreign_key="customer.id")
    issue_date: datetime.date
    due_date: datetime.date
    status: str = "draft"
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    paid_amount: float = 0.0
    notes: str | None = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class InvoiceLineItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id", ondelete="CASCADE")
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float
    gl_account_id: int | None = Field(default=None, foreign_key="glaccount.id")


class Bill(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bill_no: str = Field(unique=True, index=True, max_length=64)
    vendor_id: int = Field(foreign_key="vendor.id")
    issue_date: datetime.date
    due_date: datetime.date
    status: str = "pending"
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    paid_amount: float = 0.0
    notes: str | None = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))


class BillLineItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bill_id: int = Field(foreign_key="bill.id", ondelete="CASCADE")
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float
    gl_account_id: int | None = Field(default=None, foreign_key="glaccount.id")


class CategoryRule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    pattern: str
    gl_account_id: int = Field(foreign_key="glaccount.id")
    category: str
    priority: int = 0
    is_active: bool = Field(default=True)
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
    gl_account_id: int | None = Field(default=None, foreign_key="glaccount.id")
    invoice_id: int | None = Field(default=None, foreign_key="invoice.id")
    bill_id: int | None = Field(default=None, foreign_key="bill.id")
    hash: str = Field(unique=True, index=True)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    @staticmethod
    def compute_hash(tx_date: datetime.date, description: str, amount: float) -> str:
        raw = f"{tx_date.isoformat()}|{description.strip().lower()}|{amount}"
        return hashlib.sha256(raw.encode()).hexdigest()
