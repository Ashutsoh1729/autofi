import datetime
from pathlib import Path

import pytest

from util.csv_parser import (
    CSVFormat,
    _clean_amount,
    _parse_date,
    _build_column_map,
    detect_format,
    parse_csv,
)


class TestDetectFormat:
    def test_hdfc(self):
        headers = ["Date", "Narration", "Chq/Ref Number", "Value Dat", "Withdrawal Amount", "Deposit Amount", "Closing Balance"]
        assert detect_format(headers) == CSVFormat.HDFC

    def test_chase_by_transaction_date(self):
        headers = ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"]
        assert detect_format(headers) == CSVFormat.CHASE

    def test_chase_by_details(self):
        headers = ["Details", "Posting Date", "Description", "Amount", "Type", "Balance"]
        assert detect_format(headers) == CSVFormat.CHASE

    def test_generic_date_desc_amount(self):
        headers = ["Date", "Description", "Amount"]
        assert detect_format(headers) == CSVFormat.GENERIC_DATE_DESC_AMOUNT

    def test_generic_debit_credit(self):
        headers = ["Date", "Description", "Debit", "Credit"]
        assert detect_format(headers) == CSVFormat.GENERIC_DATE_DESC_DEBIT_CREDIT

    def test_unrecognised_raises(self):
        headers = ["Foo", "Bar", "Baz"]
        with pytest.raises(ValueError):
            detect_format(headers)


class TestHelpers:
    def test_clean_amount_strips_commas_and_symbols(self):
        assert _clean_amount("$1,234.56") == 1234.56
        assert _clean_amount("₹5,000") == 5000.0
        assert _clean_amount("\"1,234.56\"") == 1234.56

    def test_clean_amount_empty(self):
        assert _clean_amount("") == 0.0

    def test_parse_date(self):
        assert _parse_date("2025-01-15") == datetime.date(2025, 1, 15)
        assert _parse_date("01/15/2025") == datetime.date(2025, 1, 15)
        assert _parse_date("15 Jan 2025") == datetime.date(2025, 1, 15)

    def test_parse_date_invalid(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")


class TestBuildColumnMap:
    def test_maps_standard_headers(self):
        headers = ["Date", "Description", "Amount"]
        m = _build_column_map(headers)
        assert m["date"] == "date"
        assert m["description"] == "description"
        assert m["amount"] == "amount"

    def test_maps_hdfc_headers(self):
        headers = ["Date", "Narration", "Chq/Ref Number", "Value Dat", "Withdrawal Amount", "Deposit Amount", "Closing Balance"]
        m = _build_column_map(headers)
        assert m["date"] == "date"
        assert m["description"] == "narration"
        assert m["debit"] == "withdrawal amount"
        assert m["credit"] == "deposit amount"

    def test_maps_variant_names(self):
        headers = ["Txn Date", "Memo", "Amount"]
        m = _build_column_map(headers)
        assert m["date"] == "txn date"
        assert m["description"] == "memo"
        assert m["amount"] == "amount"


HDFC_CSV = """Date,Narration,Chq/Ref Number,Value Dat,Withdrawal Amount,Deposit Amount,Closing Balance
01/04/2025,UPI Payment to Merchant,UPI001,01/04/2025,,500.00,10500.00
02/04/2025,ATM Withdrawal,ATM002,02/04/2025,2000.00,,8500.00
03/04/2025,Salary Credit,SLRY003,03/04/2025,,75000.00,83500.00"""

CHASE_CSV = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
04/01/2025,04/01/2025,Starbucks Coffee,Food & Drink,Sale,-5.50,
04/02/2025,04/02/2025,Direct Deposit,Payroll,Deposit,2500.00,
04/03/2025,04/03/2025,Amazon.com,Shopping,Sale,-34.99,"Order #12345"
"""

GENERIC_SIMPLE_CSV = """Date,Description,Amount
2025-01-15,Office Supplies,-120.50
2025-01-16,Client Payment,5000.00
2025-01-17,Internet Bill,-89.99"""

GENERIC_DEBIT_CREDIT_CSV = """Date,Description,Debit,Credit
2025-01-15,Office Supplies,120.50,
2025-01-16,Client Payment,,5000.00
2025-01-17,Electric Bill,250.00,"""


@pytest.fixture
def tmp_csv(tmp_path: Path, request):
    """Write a CSV file to tmp_path for testing."""
    marker = request.node.get_closest_marker("csv_content")
    data = marker.args[0] if marker else ""
    path = tmp_path / "test.csv"
    path.write_text(data, encoding="utf-8")
    return path


class TestParseCSV:
    def test_hdfc_format(self, tmp_path: Path):
        path = tmp_path / "hdfc.csv"
        path.write_text(HDFC_CSV)
        txs = parse_csv(path)
        assert len(txs) == 3
        assert txs[0].description == "UPI Payment to Merchant"
        assert txs[0].amount == 500.0  # deposit
        assert txs[0].date == datetime.date(2025, 4, 1)
        assert txs[1].description == "ATM Withdrawal"
        assert txs[1].amount == -2000.0  # withdrawal
        assert txs[1].date == datetime.date(2025, 4, 2)
        assert txs[2].amount == 75000.0  # salary deposit
        assert txs[2].date == datetime.date(2025, 4, 3)

    def test_chase_format(self, tmp_path: Path):
        path = tmp_path / "chase.csv"
        path.write_text(CHASE_CSV)
        txs = parse_csv(path)
        assert len(txs) == 3
        assert txs[0].description == "Starbucks Coffee"
        assert txs[0].amount == -5.50
        assert txs[0].date == datetime.date(2025, 4, 1)
        assert txs[1].description == "Direct Deposit"
        assert txs[1].amount == 2500.0
        assert txs[1].date == datetime.date(2025, 4, 2)
        assert txs[2].description == "Amazon.com"
        assert txs[2].amount == -34.99

    def test_generic_simple(self, tmp_path: Path):
        path = tmp_path / "generic.csv"
        path.write_text(GENERIC_SIMPLE_CSV)
        txs = parse_csv(path)
        assert len(txs) == 3
        assert txs[0].description == "Office Supplies"
        assert txs[0].amount == -120.50
        assert txs[0].date == datetime.date(2025, 1, 15)
        assert txs[1].description == "Client Payment"
        assert txs[1].amount == 5000.0
        assert txs[1].date == datetime.date(2025, 1, 16)
        assert txs[2].description == "Internet Bill"
        assert txs[2].amount == -89.99
        assert txs[2].date == datetime.date(2025, 1, 17)

    def test_generic_debit_credit(self, tmp_path: Path):
        path = tmp_path / "generic_dc.csv"
        path.write_text(GENERIC_DEBIT_CREDIT_CSV)
        txs = parse_csv(path)
        assert len(txs) == 3
        assert txs[0].description == "Office Supplies"
        assert txs[0].amount == -120.50
        assert txs[0].type == "debit"
        assert txs[0].date == datetime.date(2025, 1, 15)
        assert txs[1].description == "Client Payment"
        assert txs[1].amount == 5000.0
        assert txs[1].type == "credit"
        assert txs[1].date == datetime.date(2025, 1, 16)
        assert txs[2].description == "Electric Bill"
        assert txs[2].amount == -250.0
        assert txs[2].type == "debit"
        assert txs[2].date == datetime.date(2025, 1, 17)

    def test_bom_handling(self, tmp_path: Path):
        content = "\ufeff" + GENERIC_SIMPLE_CSV
        path = tmp_path / "bom.csv"
        path.write_bytes(content.encode("utf-8"))
        txs = parse_csv(path)
        assert len(txs) == 3

    def test_empty_file_raises(self, tmp_path: Path):
        path = tmp_path / "empty.csv"
        path.write_text("")
        with pytest.raises(ValueError, match="empty"):
            parse_csv(path)

    def test_no_headers_raises(self, tmp_path: Path):
        path = tmp_path / "no_headers.csv"
        path.write_text("\n")
        with pytest.raises(ValueError):
            parse_csv(path)

    def test_skip_empty_rows(self, tmp_path: Path):
        csv_data = "Date,Description,Amount\n2025-01-15,Test,100.0\n\n\n2025-01-16,Another,50.0\n"
        path = tmp_path / "empty_rows.csv"
        path.write_text(csv_data)
        txs = parse_csv(path)
        assert len(txs) == 2

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_csv("/nonexistent/file.csv")

    def test_currency_variants(self, tmp_path: Path):
        csv_data = "Date,Description,Amount\n2025-01-15,Sale,\"$1,234.56\"\n2025-01-16,Purchase,₹500.00\n"
        path = tmp_path / "currency.csv"
        path.write_text(csv_data)
        txs = parse_csv(path)
        assert len(txs) == 2
        assert txs[0].amount == 1234.56
        assert txs[1].amount == 500.0
