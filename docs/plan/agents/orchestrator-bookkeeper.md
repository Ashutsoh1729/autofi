# Orchestrator + Bookkeeper Agents (Phase 1)

## Description
Build the first two agents from SPEC.md — Orchestrator (LLM-driven router) and Bookkeeper (categorisation + chart of accounts) — exposed via a `autofi chat` CLI command.

Uses [Pydantic AI](https://ai.pydantic.dev/) as the agent framework — model-agnostic (OpenAI, Anthropic, Gemini, etc.), type-safe tool calling, structured outputs.

## Goals
- User can ask natural-language questions about their finances
- Orchestrator routes requests to specialist agent tools via LLM reasoning
- Bookkeeper can categorise transactions and show the chart of accounts
- All agent actions log to a conversation history table
- Multi-provider LLM support via `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` env vars

## Implementation Steps

### Step 1: Dependency + Agent Scaffold
- [x] Add `pydantic-ai` to `pyproject.toml`
- [x] Create `src/agents/settings.py` — reads `AUTOFI_LLM_MODEL` env var (default `anthropic:claude-sonnet-4-20250514`), API key from provider-specific env var
- [x] Create `src/agents/orchestrator.py` — Pydantic AI `Agent` with system prompt defining agent roles and routing logic
- [x] Create `src/agents/bookkeeper.py` — Pydantic AI `Agent` with bookkeeping tools registered via `@agent.tool`

### Step 2: Bookkeeper Tools
- [x] `categorise_transaction(tx_id: int, category: str)` — updates `Transaction.category` in DB
- [x] `list_transactions(query: str, limit: int = 10)` — searches by description text (ilike), wraps existing session pattern
- [x] `get_transaction_stats()` — wraps existing `get_transaction_stats()` from ingestion service
- [x] `list_accounts()` — shows chart of accounts with transaction counts

### Step 3: Orchestrator
- [x] Orchestrator agent receives user message, decides which specialist agent (or tool) to invoke
- [x] For MVP: single-agent setup where the Bookkeeper agent has all tools + conversational system prompt
- [x] Orchestrator returns structured response (text + optional tool results)

### Step 4: Conversation History Model
- [x] Add `ConversationMessage` SQLModel table (messages, agent turns, timestamp)
- [x] Store every user message + agent response in DB

### Step 5: Chat CLI Command
- [x] Add `autofi chat "<question>"` command in `src/cli/chat.py`
- [x] Accept `--interactive` flag for multi-turn REPL
- [x] Wire to orchestrator → returns response

### Step 6: Logging
- [x] Add `logging` throughout agents (per AGENTS.md requirement)
- [x] Log LLM calls, tool invocations, errors

### Step 7: Tests
- [x] Unit tests for bookkeeper tools (mock DB)
- [x] Unit tests for orchestrator routing
- [x] CLI integration test for `autofi chat`

## Files to Modify/Create
- `src/agents/settings.py` (new) — LLM model config, API key resolution
- `src/agents/orchestrator.py` (new) — Pydantic AI Agent, routing logic
- `src/agents/bookkeeper.py` (new) — Bookkeeper agent with tools
- `src/data/models.py` (add Conversation model)
- `src/cli/chat.py` (new)
- `src/cli/main.py` (register chat command)
- `pyproject.toml` (add `pydantic-ai`)
- `tests/` (new test files)

## Considerations
- LLM API keys are read from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.) — never logged or committed
- If LLM is unavailable, fall back to a rule-based response
- Pydantic AI's `Agent` uses function type hints + docstrings for tool schemas — no manual JSON schema
- Use `agent.run_sync()` for synchronous CLI calls
- Model selection via `AUTOFI_LLM_MODEL` env var (e.g. `openai:gpt-4o`, `anthropic:claude-sonnet-4-20250514`, `google-gla:gemini-2.0-flash`)
