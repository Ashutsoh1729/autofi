from sqlmodel import Session, select

from data.models import GLAccount

DEFAULT_GL_ACCOUNTS: list[dict] = [
    {"code": "1100", "name": "Cash", "type": "asset"},
    {"code": "1200", "name": "Accounts Receivable", "type": "asset"},
    {"code": "2100", "name": "Accounts Payable", "type": "liability"},
    {"code": "3100", "name": "Owner's Equity", "type": "equity"},
    {"code": "3200", "name": "Retained Earnings", "type": "equity"},
    {"code": "4100", "name": "Revenue", "type": "income"},
    {"code": "4200", "name": "Service Income", "type": "income"},
    {"code": "5010", "name": "Cost of Goods Sold", "type": "expense"},
    {"code": "5020", "name": "Rent", "type": "expense"},
    {"code": "5030", "name": "Utilities", "type": "expense"},
    {"code": "5040", "name": "Office Supplies", "type": "expense"},
    {"code": "5050", "name": "Software & Subscriptions", "type": "expense"},
    {"code": "5060", "name": "Travel", "type": "expense"},
    {"code": "5070", "name": "Meals & Entertainment", "type": "expense"},
    {"code": "5080", "name": "Professional Fees", "type": "expense"},
    {"code": "5090", "name": "Insurance", "type": "expense"},
    {"code": "5100", "name": "Taxes & Licenses", "type": "expense"},
    {"code": "5110", "name": "Bank Fees", "type": "expense"},
    {"code": "5120", "name": "Depreciation", "type": "expense"},
]


def seed_gl_accounts(engine) -> None:
    with Session(engine) as session:
        existing = session.exec(select(GLAccount).limit(1)).first()
        if existing is not None:
            return

        accounts = [GLAccount(**data) for data in DEFAULT_GL_ACCOUNTS]
        session.add_all(accounts)
        session.commit()
