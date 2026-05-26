# Test Results: Steps 1 & 2 — DB Layer

**Plan:** `docs/plan/ingestion/bank-feed-ingestion.md`
**Work:** `docs/work/bank-feed-ingestion.md`

---

## Tests Run

```bash
uv run pytest src/test/test_db.py -v
```

```
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/ashutoshhota/Coding/play_ground/personal_projects/ai_apps/autofi
configfile: pyproject.toml
collecting ... collected 8 items

src/test/test_db.py::test_init_db_creates_tables PASSED                  [ 12%]
src/test/test_db.py::test_insert_and_query_account PASSED                [ 25%]
src/test/test_db.py::test_insert_and_query_transactions PASSED           [ 37%]
src/test/test_db.py::test_dedup_rejects_duplicate_hash PASSED            [ 50%]
src/test/test_db.py::test_compute_hash_consistency PASSED                [ 62%]
src/test/test_db.py::test_compute_hash_case_insensitive PASSED           [ 75%]
src/test/test_db.py::test_list_transactions_with_filter PASSED           [ 87%]
src/test/test_db.py::test_get_db_path_returns_path PASSED                [100%]

============================== 8 passed in 0.34s ===============================
```

## Lint Check

```bash
uv run ruff check src/test/test_db.py
```
```
All checks passed!
```

## Results Summary

| Test | Status | What It Validates |
|------|--------|-------------------|
| `test_init_db_creates_tables` | ✅ | DB file + tables created without error |
| `test_insert_and_query_account` | ✅ | Account insert + read-back works |
| `test_insert_and_query_transactions` | ✅ | Transaction insert linked to account + query by account_id |
| `test_dedup_rejects_duplicate_hash` | ✅ | Duplicate hash triggers unique constraint violation |
| `test_compute_hash_consistency` | ✅ | Same inputs → identical hash |
| `test_compute_hash_case_insensitive` | ✅ | Case difference normalised → same hash |
| `test_list_transactions_with_filter` | ✅ | `.limit()` filter on queries |
| `test_get_db_path_returns_path` | ✅ | Config returns valid path ending in `autofi.db` |

## Notes

- All tests use `tmp_path` (pytest fixture) — no side effects on real DB
- 8/8 passed, 0 warnings, lint clean
- Covers: DB init, CRUD, dedup logic, config path, query filtering