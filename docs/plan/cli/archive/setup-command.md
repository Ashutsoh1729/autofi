# CLI Setup Command — Model & API Key Configuration

## Description

Add an `autofi setup` command that interactively configures the LLM model and API key, storing them securely in the database instead of `.env` files. The agent system then reads from the database at runtime, falling back to env vars.

## Problem

Currently, users must manually edit `.env` with `AUTOFI_LLM_MODEL=google-gla:gemini-2.0-flash` and `GOOGLE_API_KEY=...`. This is error-prone (the user just set `AUTOFI_LLM_MODEL` to the API key value by mistake), requires direnv/`.env` loading infrastructure, and leaks keys in plaintext files.

## Goals

- Interactive `autofi setup` CLI with model selection from supported providers
- API key stored encrypted in SQLite DB (not plaintext `.env`)
- DB-stored settings override env vars at runtime
- Existing env-var-based flow remains as a fallback (backward compatible)

## Implementation Steps

### Step 1: Add `AppConfig` model to database

- [x] Add `AppConfig` SQLModel table in `src/data/models.py` with columns:
  - `key: str` (primary key) — e.g. `"model"`, `"api_key_anthropic"`, `"api_key_openai"`, etc.
  - `value: str` — encrypted value
- [x] Add `data/config.py` with `get_setting(db_path, key)`, `set_setting(db_path, key, value)`, `delete_setting(db_path, key)`

**Note on encryption:** Symmetric encryption via `cryptography.fernet` with PBKDF2-derived key stored at `~/.config/autofi/fernet.key`.

### Step 2: Add `cryptography` dependency & encryption helpers

- [x] `uv add cryptography`
- [x] Create `src/util/crypto.py` with:
  - `encrypt_value(plaintext: str) -> str`
  - `decrypt_value(token: str) -> str`
- [x] Key derived using PBKDF2HMAC(SHA256) with random salt, stored in config dir

### Step 3: Create `src/data/config.py` — DB config helpers

- [x] `get_setting(db_path, key) -> str | None` — read from `AppConfig`
- [x] `set_setting(db_path, key, value)` — upsert into `AppConfig`
- [x] `delete_setting(db_path, key)` — remove from `AppConfig`

### Step 4: Create `src/cli/setup.py` — the setup command

- [x] Interactive wizard with click.prompt:
  1. Display available providers with numbered selection
  2. User selects provider → show relevant model list (with ✨ for free-tier models)
  3. User selects model
  4. Prompt for API key (hidden input, optional — can skip to use env var)
  5. Show summary and ask for confirmation
  6. Save encrypted to DB

Provider → model mapping (hardcoded):
| Provider | Models |
|----------|--------|
| `anthropic` | `claude-sonnet-4-20250514`, `claude-opus-4-20250514`, `claude-3-5-sonnet-latest` |
| `openai` | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` |
| `google-gla` | `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-pro`, `gemini-2.5-flash-preview-05-20` — ✨ Free tier: 1,500 req/day |
| `groq` | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `llama-4-scout-17b-16e-instruct` — ✨ Free tier: 14,400 req/day |
| `openrouter` | `meta-llama/llama-4-maverick:free`, `deepseek/deepseek-r1:free`, `qwen/qwen3-235b-a22b:free` — ✨ All free on OpenRouter |

Top 5 recommended free/good-tier models to highlight in setup:
1. `gemini-2.5-flash-preview-05-20` — Google AI Studio, 1,500 req/day free
2. `llama-4-scout-17b-16e-instruct` — Groq, 14,400 req/day free, ultra-fast LPU
3. `meta-llama/llama-4-maverick:free` — OpenRouter, free
4. `deepseek/deepseek-r1:free` — OpenRouter, free, strong reasoning
5. `qwen/qwen3-235b-a22b:free` — OpenRouter, free, massive MoE

Keys stored in DB:
- `model` → full model string (e.g. `"google-gla:gemini-2.0-flash"`)
- `api_key_anthropic` → encrypted key
- `api_key_openai` → encrypted key
- `api_key_google-gla` → encrypted key
- `api_key_groq` → encrypted key

### Step 5: Register setup command in main CLI

- [x] Import and add `setup` command to `src/cli/main.py`

### Step 6: Update `src/agents/settings.py` to read from DB first

- [x] `resolve_api_key(provider: str)` — reads encrypted key from `AppConfig`, decrypts, falls back to env var
- [x] `get_model_for_agent(agent_name: str)` — reads `model` from `AppConfig` first, then env var, then default
- [x] `create_agent_model(agent_name: str)` — builds Model instance with provider-specific factories and API key injection
- [x] Added `openrouter` to `PROVIDER_ENV_VARS`

### Step 7: Wire the API key into agents at runtime

- [x] `create_agent_model` constructs model using `infer_model` with custom `provider_factory` that injects DB-stored key
- [x] When no key is available anywhere, returns model string for `defer_model_check` lazy resolution
- [x] Updated `bookkeeper.py` and `orchestrator.py` to use `create_agent_model()`
- [x] Updated `chat.py` Agent type annotations for pyright compatibility

### Step 8: Verify

- [x] Encryption round-trip: encrypt → decrypt → matches original (manual test passed)
- [x] AppConfig model: set_setting → get_setting → delete_setting (manual test passed)
- [x] All 9 existing tests pass
- [x] ruff check — All checks passed
- [x] pyright — 0 errors, 0 warnings

## Files Created / Modified

| File | Action |
|------|--------|
| `src/data/models.py` | **Modified** — Added `AppConfig` table |
| `src/data/config.py` | **NEW** — `get_setting`, `set_setting`, `delete_setting` helpers |
| `src/util/crypto.py` | **NEW** — `encrypt_value`, `decrypt_value` with PBKDF2 + Fernet |
| `src/cli/setup.py` | **NEW** — interactive setup command with provider/model selection |
| `src/cli/main.py` | **Modified** — Registered `setup` command |
| `src/cli/chat.py` | **Modified** — Fixed Agent type annotations for pyright |
| `src/agents/settings.py` | **Modified** — DB-first resolution, `create_agent_model()`, `resolve_api_key()` |
| `src/agents/bookkeeper.py` | **Modified** — Use `create_agent_model()` |
| `src/agents/orchestrator.py` | **Modified** — Use `create_agent_model()` |
| `pyproject.toml` | **Modified** — Added `cryptography` dependency |

## Status: Completed ✓

## Considerations

- **Encryption key location:** `~/.config/autofi/fernet.key` — if lost, stored API keys can't be decrypted. The user would need to re-run `autofi setup`.
- **Encryption is not hashing:** API keys must be decryptable to use them (LLM providers need the raw key). Fernet symmetric encryption with a local key is the right approach for a CLI tool.
- **Backward compatibility:** If no DB config exists, the old env-var path works unchanged.
- **Multiple providers:** A user might configure keys for multiple providers and switch models later. The setup stores all provider keys.
- **`autofi setup` can be re-run** to update model/key — it overwrites existing settings.
- **Not a secrets manager:** This is local convenience, not production-grade secret storage.
