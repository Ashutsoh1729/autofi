from pathlib import Path

import pytest

from util.bank_feed_ingestion import (
    get_transaction_stats,
    import_csv,
    list_transactions,
)


SAMPLE_CSV = """Date,Description,Amount
2025-01-15,Office Supplies,-120.50
2025-01-16,Client Payment,5000.00
2025-01-17,Internet Bill,-89.99
2025-01-18,Freelance Income,1500.00
2025-01-19,Office Rent,-2000.00"""


@pytest.fixture(autouse=True)
def mock_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_autofi.db"
    import util.bank_feed_ingestion as bfi
    monkeypatch.setattr(bfi, "get_db_path", lambda: db_file)
    return db_file


class TestImportCSV:
    def test_import_new_csv(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        result = import_csv(str(csv_path))
        assert result.imported == 5
        assert result.skipped == 0
        assert result.account_name == "Default Account"

    def test_dedup_on_reimport(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        r1 = import_csv(str(csv_path))
        assert r1.imported == 5
        assert r1.skipped == 0

        r2 = import_csv(str(csv_path))
        assert r2.imported == 0
        assert r2.skipped == 5

    def test_dry_run_does_not_write(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        result = import_csv(str(csv_path), dry_run=True)
        assert result.imported == 5
        assert result.skipped == 0
        assert result.account_name == "Default Account"

        txs = list_transactions()
        assert len(txs) == 0

    def test_import_with_existing_account(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text("Date,Description,Amount\n2025-01-15,T1,100.00")

        # First import creates default account
        r1 = import_csv(str(csv_path))
        assert r1.account_name == "Default Account"

        # Second import into same account
        r2 = import_csv(str(csv_path), account_id=str(r1.account_id))
        assert r2.account_name == "Default Account"

    def test_import_unknown_account_raises(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text("Date,Description,Amount\n2025-01-15,T1,100.00")
        with pytest.raises(ValueError, match="not found"):
            import_csv(str(csv_path), account_id="9999")

    def test_partial_import_with_errors(self, mock_db: Path, tmp_path: Path):
        csv_data = "Date,Description,Amount\n2025-01-15,Valid,100.00\nnot-a-date,Bad,-50.00\n2025-01-15,Also Valid,75.00\n"
        csv_path = tmp_path / "partial.csv"
        csv_path.write_text(csv_data)
        with pytest.raises(Exception):
            import_csv(str(csv_path))

    def test_csv_parse_error_preserves_valid_rows(self, mock_db: Path, tmp_path: Path):
        csv_data = "Date,Description,Amount\n2025-01-15,Valid,100.00\ninvalid,Bad,-50.00\n"
        csv_path = tmp_path / "partial2.csv"
        csv_path.write_text(csv_data)
        with pytest.raises(Exception):
            import_csv(str(csv_path))


class TestListTransactions:
    def test_list_all(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        import_csv(str(csv_path))
        txs = list_transactions()
        assert len(txs) == 5

    def test_list_with_limit(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        import_csv(str(csv_path))
        txs = list_transactions(limit=2)
        assert len(txs) == 2

    def test_list_with_days_filter(self, mock_db: Path, tmp_path: Path):
        """All sample data is from Jan 2025 — should be outside a 7-day window."""
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        import_csv(str(csv_path))
        txs = list_transactions(days=7)
        assert len(txs) == 0

    def test_list_with_account_id(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text("Date,Description,Amount\n2025-01-15,T1,100.00")
        r = import_csv(str(csv_path))
        txs = list_transactions(account_id=r.account_id)
        assert len(txs) == 1


class TestGetTransactionStats:
    def test_stats_empty(self, mock_db: Path):
        stats = get_transaction_stats()
        assert stats["total_transactions"] == 0
        assert stats["per_account"] == {}
        assert stats["date_range"] is None

    def test_stats_after_import(self, mock_db: Path, tmp_path: Path):
        csv_path = tmp_path / "txns.csv"
        csv_path.write_text(SAMPLE_CSV)
        import_csv(str(csv_path))
        stats = get_transaction_stats()
        assert stats["total_transactions"] == 5
        assert "Default Account" in stats["per_account"]
        assert stats["date_range"] is not None
        assert "2025-01-15" in stats["date_range"]
        assert "2025-01-19" in stats["date_range"]
