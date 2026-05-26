import csv
import io
from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from pathlib import Path

from dateutil import parser as dateparser


class CSVFormat(Enum):
    GENERIC_DATE_DESC_AMOUNT = auto()
    GENERIC_DATE_DESC_DEBIT_CREDIT = auto()
    HDFC = auto()
    CHASE = auto()


@dataclass
class RawTransaction:
    date: date
    description: str
    amount: float
    currency: str = "INR"
    type: str | None = None


ParseResult = list[RawTransaction]


class ParseError(ValueError):
    def __init__(self, row: int, message: str) -> None:
        self.row = row
        self.message = message
        super().__init__(f"Row {row}: {message}")


def _normalise_header(h: str) -> str:
    return h.strip().lower().lstrip("\ufeff")


def _clean_amount(raw: str) -> float:
    cleaned = raw.strip().replace(",", "").replace('"', "")
    for sym in ("$", "₹", "€", "£", "US$", "USD", "INR"):
        cleaned = cleaned.replace(sym, "")
    cleaned = cleaned.strip()
    if not cleaned:
        return 0.0
    return float(cleaned)


def _parse_date(raw: str, dayfirst: bool = False) -> date:
    cleaned = raw.strip()
    dt = dateparser.parse(cleaned, dayfirst=dayfirst)
    if dt is None:
        raise ValueError(f"Could not parse date: {raw}")
    return dt.date()


def detect_format(headers: list[str]) -> CSVFormat:
    norm = [_normalise_header(h) for h in headers]

    if "narration" in norm and (
        "withdrawal amount" in norm
        or "deposit amount" in norm
        or "withdrawal amt.(inr)" in norm
        or "deposit amt.(inr)" in norm
    ):
        return CSVFormat.HDFC

    if "transaction date" in norm and "amount" in norm:
        return CSVFormat.CHASE
    if "details" in norm and "amount" in norm and "type" in norm:
        return CSVFormat.CHASE
    if "posting date" in norm and "description" in norm:
        return CSVFormat.CHASE

    if "date" in norm and "description" in norm and "debit" in norm and "credit" in norm:
        return CSVFormat.GENERIC_DATE_DESC_DEBIT_CREDIT

    if "date" in norm and "description" in norm and "amount" in norm:
        return CSVFormat.GENERIC_DATE_DESC_AMOUNT

    raise ValueError(f"Unrecognised CSV format. Headers: {headers}")


_BUILTIN_COL_CANDIDATES: dict[str, tuple[str, ...]] = {
    "date": ("date", "transaction date", "posting date", "post date", "value dat", "txn date"),
    "description": ("description", "narration", "details", "memo", "particulars"),
    "amount": ("amount", "transaction amount", "txn amount"),
    "debit": ("debit", "withdrawal amount", "withdrawal amt.(inr)", "withdrawals", "debit amount", "withdrawn"),
    "credit": ("credit", "deposit amount", "deposit amt.(inr)", "deposits", "credit amount", "deposit"),
}


def _build_column_map(headers: list[str]) -> dict[str, str]:
    norm = {_normalise_header(h): h for h in headers}
    result: dict[str, str] = {}
    for canonical, possible in _BUILTIN_COL_CANDIDATES.items():
        for p in possible:
            if p in norm:
                result[canonical] = p
                break
    return result


def _iter_rows(reader: csv.DictReader):
    for i, row in enumerate(reader, start=2):
        cleaned = {k.strip().lower(): v.strip() for k, v in row.items() if k and v is not None}
        if not any(cleaned.values()):
            continue
        yield i, cleaned


def _parse_rows_generic_simple(
    reader: csv.DictReader,
    col_map: dict[str, str],
) -> ParseResult:
    results: ParseResult = []
    for i, row in _iter_rows(reader):
        try:
            dt = _parse_date(row[col_map["date"]])
            desc = row.get(col_map.get("description", ""), "")
            amt = _clean_amount(row[col_map["amount"]])
            results.append(RawTransaction(date=dt, description=desc, amount=amt))
        except KeyError as e:
            raise ParseError(i, f"Missing column: {e}") from e
        except ValueError as e:
            raise ParseError(i, str(e)) from e
    return results


def _parse_rows_generic_debit_credit(
    reader: csv.DictReader,
    col_map: dict[str, str],
) -> ParseResult:
    results: ParseResult = []
    for i, row in _iter_rows(reader):
        try:
            dt = _parse_date(row[col_map["date"]])
            desc = row.get(col_map.get("description", ""), "")
            debit = _clean_amount(row.get(col_map.get("debit", ""), "0"))
            credit = _clean_amount(row.get(col_map.get("credit", ""), "0"))
            amt = credit - debit
            tx_type = "credit" if credit > 0 else "debit"
            results.append(RawTransaction(date=dt, description=desc, amount=amt, type=tx_type))
        except KeyError as e:
            raise ParseError(i, f"Missing column: {e}") from e
        except ValueError as e:
            raise ParseError(i, str(e)) from e
    return results


def _parse_rows_hdfc(
    reader: csv.DictReader,
    col_map: dict[str, str],
) -> ParseResult:
    results: ParseResult = []
    for i, row in _iter_rows(reader):
        try:
            dt = _parse_date(row[col_map["date"]], dayfirst=True)
            desc = row.get(col_map.get("description", ""), "")
            withdrawal = _clean_amount(row.get(col_map.get("debit", ""), "0"))
            deposit = _clean_amount(row.get(col_map.get("credit", ""), "0"))
            amt = deposit - withdrawal
            results.append(RawTransaction(date=dt, description=desc, amount=amt))
        except KeyError as e:
            raise ParseError(i, f"Missing column: {e}") from e
        except ValueError as e:
            raise ParseError(i, str(e)) from e
    return results


def _parse_rows_chase(
    reader: csv.DictReader,
    col_map: dict[str, str],
) -> ParseResult:
    results: ParseResult = []
    for i, row in _iter_rows(reader):
        try:
            dt = _parse_date(row[col_map["date"]])
            desc = row.get(col_map.get("description", ""), "")
            amt = _clean_amount(row[col_map["amount"]])
            results.append(RawTransaction(date=dt, description=desc, amount=amt))
        except KeyError as e:
            raise ParseError(i, f"Missing column: {e}") from e
        except ValueError as e:
            raise ParseError(i, str(e)) from e
    return results


_FORMAT_PARSERS: dict[CSVFormat, callable] = {
    CSVFormat.GENERIC_DATE_DESC_AMOUNT: _parse_rows_generic_simple,
    CSVFormat.GENERIC_DATE_DESC_DEBIT_CREDIT: _parse_rows_generic_debit_credit,
    CSVFormat.HDFC: _parse_rows_hdfc,
    CSVFormat.CHASE: _parse_rows_chase,
}


def parse_csv(filepath: str | Path) -> ParseResult:
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    if filepath.stat().st_size == 0:
        raise ValueError("CSV file is empty")

    with filepath.open(encoding="utf-8-sig") as f:
        content = f.read()

    if not content.strip():
        raise ValueError("CSV file is empty")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV file has no headers")

    headers = reader.fieldnames
    fmt = detect_format(headers)
    col_map = _build_column_map(headers)
    parser = _FORMAT_PARSERS[fmt]

    results = parser(reader, col_map)
    return results
