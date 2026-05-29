# Orchestrator + Bookkeeper Agents — Work File

## What each step accomplishes

---

### Step 1: Dependency + Agent Scaffold ✅ (Done)

**Functions enabled:**
- `src/agents/settings.py` reads `AUTOFI_LLM_MODEL` env var (default `anthropic:claude-sonnet-4-20250514`) and resolves API keys from provider-specific env vars
- `src/agents/bookkeeper.py` defines the Bookkeeper Pydantic AI agent with four tool stubs: `categorise_transaction`, `list_transactions`, `get_transaction_stats`, `list_accounts`
- `src/agents/orchestrator.py` defines the Orchestrator Pydantic AI agent with routing system prompt describing specialist agent roles

**Implemented in:**
- `src/agents/settings.py` (new, 39 lines)
- `src/agents/bookkeeper.py` (new, 75 lines)
- `src/agents/orchestrator.py` (new, 33 lines)

**Business capability:** None yet — agents exist but have no real database-backed tools or CLI integration. The Pydantic AI framework is wired in and ready for tool implementations in Step 2.

---

### Step 2: Bookkeeper Tools ✅ (Done)

**Functions implemented:**

- `categorise_transaction(tx_id, category)` — looks up `Transaction` by ID in DB via `session.get()`, sets `t.category`, commits. Logs the change (old → new category).

- `list_transactions(query, limit)` — searches transactions by description using SQL `ilike` (case-insensitive match), returns a formatted table (ID, Date, Description, Amount, Category). Uses `col(Transaction.description).ilike(f"%{query}%")`.

- `get_transaction_stats()` — delegates to `util.bank_feed_ingestion.get_transaction_stats()`, formats the result dict into readable lines.

- `list_accounts()` — queries all `Account` rows, counts transactions per account, returns a formatted table (ID, Name, Type, Currency, Transaction count).

**Dependencies:** All tools receive `ctx.deps.db_path` via Pydantic AI's `RunContext[BookkeeperDeps]` dependency injection. A `BookkeeperDeps` dataclass holds the `db_path`.

**Implemented in:** `src/agents/bookkeeper.py` (now ~150 lines — was 70 lines of stubs)

**Business capability:** The Bookkeeper agent can now read/write real data from the SQLite database. A user can ask "categorise transaction 5 as Food" or "show me transactions mentioning Starbucks" and the agent will actually execute those operations.

---

### Step 3: Orchestrator ✅ (Done)

**What changed:**
- `src/agents/orchestrator.py` — now registers all four bookkeeper tool functions (`categorise_transaction`, `list_transactions`, `get_transaction_stats`, `list_accounts`) on the orchestrator agent using `agent.tool(func)`.
- `src/agents/bookkeeper.py` — refactored: tool functions are now standalone (not bound to `bookkeeper_agent` at definition time). Both `bookkeeper_agent` and `orchestrator_agent` register the same functions, avoiding code duplication.
- `orchestrator_agent` has `deps_type=BookkeeperDeps` and `defer_model_check=True`, same as bookkeeper.

**System prompt** describes the Orchestrator role: receive user requests, decompose, route to specialist agents, synthesise results. For MVP it's a single-agent setup — the orchestrator IS the agent with all bookkeeper tools.

**Business capability:** The orchestrator agent is the primary entry point for the chat CLI. It can handle any bookkeeping question.

---

### Step 4: Conversation History Model ✅ (Done)

**New table:** `ConversationMessage(SQLModel, table=True)` in `src/data/models.py`:
- `id` (PK), `conversation_id` (indexed UUID), `role` ("user" / "agent"), `content` (text), `created_at` (timestamp)
- `new_conversation_id()` — generates a fresh UUID for each chat session

**Storage:** The chat CLI stores every user message and agent response via `_store_message(conv_id, role, content)` before/after each `run_sync` call. Tables are auto-created by `init_db()` since `SQLModel.metadata.create_all` picks up all subclasses.

---

### Step 5: Chat CLI Command ✅ (Done)

**New file:** `src/cli/chat.py`

- `autofi chat "<question>"` — single-turn: stores user message, calls `orchestrator_agent.run_sync()`, stores agent response, prints it
- `autofi chat --interactive` (or `-i`) — multi-turn REPL loop. Maintains `message_history` across turns for conversation context. Type `/exit`, `/quit`, `/q`, or Ctrl+D to exit. Each turn is stored in `ConversationMessage` table.
- Registered in `src/cli/main.py` via `autofi.add_command(chat)`

**Architecture:** Uses `_run_agent()` helper which calls `orchestrator_agent.run_sync()` with `deps=_default_deps()` and optional `message_history`. The orchestrator agent has all bookkeeper tools.

---

### Step 6: Logging ✅ (Done)

- `src/agents/__init__.py` — sets up `logging.basicConfig` with INFO level, timestamp, level, module, and message format
- Every tool function logs invocations, warnings (e.g. tx not found), errors (e.g. DB failures)
- Chat CLI logs each user input and any exceptions during `run_sync`
- LLM calls are handled by pydantic-ai's own logging when `logfire` is configured; basic agent logging covers tool invocations and errors

---

### Step 7: Tests ✅ (Done)

**`tests/test_bookkeeper_tools.py`** (6 tests):
- `test_categorise_transaction_ok` — updates category, verifies DB was written
- `test_categorise_transaction_not_found` — returns "not found" for missing tx
- `test_list_transactions_matches` — `ilike` search returns matching rows
- `test_list_transactions_no_match` — returns "No transactions found"
- `test_list_accounts` — lists seeded account
- `test_bookkeeper_agent_with_testmodel` — end-to-end agent call with `TestModel`

**`tests/test_orchestrator.py`** (2 tests):
- `test_orchestrator_routes_to_bookkeeper_tool` — verifies the orchestrator agent can invoke bookkeeper tools via `TestModel`
- `test_orchestrator_multiturn_conversation` — verifies `message_history` threading across two turns

All tests use temporary in-memory or file-based SQLite databases — no real LLM calls.
