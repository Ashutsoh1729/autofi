"""CLI command tests using Click runner with in-memory DB."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.main import autofi

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
    import cli.bank as cli_bank
    monkeypatch.setattr(cli_bank, "get_db_path", lambda: db_file)
    import cli.transactions as cli_tx
    monkeypatch.setattr(cli_tx, "get_db_path", lambda: db_file)
    return db_file


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "txns.csv"
    path.write_text(SAMPLE_CSV)
    return path


# ---------------------------------------------------------------------------
# autofi bank import
# ---------------------------------------------------------------------------


class TestBankImport:
    def test_import_new_csv(self, runner: CliRunner, csv_file: Path):
        result = runner.invoke(autofi, ["bank", "import", str(csv_file)])
        assert result.exit_code == 0
        assert "Imported: 5" in result.output
        assert "Skipped (duplicates): 0" in result.output
        assert "Default Account" in result.output

    def test_import_dry_run(self, runner: CliRunner, csv_file: Path):
        result = runner.invoke(autofi, ["bank", "import", str(csv_file), "--dry-run"])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "Imported: 5" in result.output

    def test_import_with_account_id(self, runner: CliRunner, csv_file: Path):
        # First import creates default account
        r1 = runner.invoke(autofi, ["bank", "import", str(csv_file)])
        assert r1.exit_code == 0

        # Parse account ID from output
        account_id = None
        for line in r1.output.splitlines():
            if "id=" in line:
                account_id = line.split("id=")[-1].strip().rstrip(")")
                break
        assert account_id is not None

        # Re-import with explicit account-id
        import_csv = csv_file.parent / "txns2.csv"
        import_csv.write_text("Date,Description,Amount\n2025-02-01,New Tx,100.00")
        r2 = runner.invoke(
            autofi, ["bank", "import", str(import_csv), "--account-id", account_id]
        )
        assert r2.exit_code == 0
        assert "Imported: 1" in r2.output

    def test_import_file_not_found(self, runner: CliRunner):
        result = runner.invoke(autofi, ["bank", "import", "/nonexistent/file.csv"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# autofi bank add-account
# ---------------------------------------------------------------------------


class TestBankAddAccount:
    def test_add_account_defaults(self, runner: CliRunner):
        result = runner.invoke(autofi, ["bank", "add-account", "My Account"])
        assert result.exit_code == 0
        assert "Created account" in result.output
        assert "My Account" in result.output

    def test_add_account_with_options(self, runner: CliRunner):
        result = runner.invoke(
            autofi,
            ["bank", "add-account", "Savings Plus", "--type", "savings", "--currency", "USD"],
        )
        assert result.exit_code == 0
        assert "Savings Plus" in result.output
        assert "savings" in result.output
        assert "USD" in result.output


# ---------------------------------------------------------------------------
# autofi bank list
# ---------------------------------------------------------------------------


class TestBankList:
    def test_list_empty(self, runner: CliRunner):
        result = runner.invoke(autofi, ["bank", "list"])
        assert result.exit_code == 0
        assert "No accounts found" in result.output or "transactions" in result.output.lower()

    def test_list_after_import(self, runner: CliRunner, csv_file: Path):
        runner.invoke(autofi, ["bank", "import", str(csv_file)])
        result = runner.invoke(autofi, ["bank", "list"])
        assert result.exit_code == 0
        assert "Default Account" in result.output
        assert "5 transactions" in result.output


# ---------------------------------------------------------------------------
# autofi tx list
# ---------------------------------------------------------------------------


class TestTxList:
    def test_list_empty(self, runner: CliRunner):
        result = runner.invoke(autofi, ["tx", "list"])
        assert result.exit_code == 0
        assert "No transactions found" in result.output

    def test_list_after_import(self, runner: CliRunner, csv_file: Path):
        runner.invoke(autofi, ["bank", "import", str(csv_file)])
        result = runner.invoke(autofi, ["tx", "list"])
        assert result.exit_code == 0
        assert "Office Supplies" in result.output
        assert "Client Payment" in result.output
        assert "5000.00" in result.output

    def test_list_with_limit(self, runner: CliRunner, csv_file: Path):
        runner.invoke(autofi, ["bank", "import", str(csv_file)])
        result = runner.invoke(autofi, ["tx", "list", "--limit", "2"])
        assert result.exit_code == 0
        lines = [line for line in result.output.splitlines() if line.strip() and not line.startswith("---")]
        # header + max 2 data lines
        assert len(lines) <= 3


# ---------------------------------------------------------------------------
# autofi tx show
# ---------------------------------------------------------------------------


class TestTxShow:
    def test_show_existing(self, runner: CliRunner, csv_file: Path):
        runner.invoke(autofi, ["bank", "import", str(csv_file)])
        result = runner.invoke(autofi, ["tx", "show", "1"])
        assert result.exit_code == 0
        assert "Office Supplies" in result.output

    def test_show_not_found(self, runner: CliRunner):
        result = runner.invoke(autofi, ["tx", "show", "999"])
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# autofi tx stats
# ---------------------------------------------------------------------------


class TestTxStats:
    def test_stats_empty(self, runner: CliRunner):
        result = runner.invoke(autofi, ["tx", "stats"])
        assert result.exit_code == 0
        assert "0" in result.output

    def test_stats_after_import(self, runner: CliRunner, csv_file: Path):
        runner.invoke(autofi, ["bank", "import", str(csv_file)])
        result = runner.invoke(autofi, ["tx", "stats"])
        assert result.exit_code == 0
        assert "Total transactions: 5" in result.output
        assert "Default Account" in result.output
