# Orchestrator → Sub-Agent Delegation (Phase 2)

## Description

Refactor the orchestrator from flat tool registration to runtime agent delegation. Instead of registering individual bookkeeper tool functions on the orchestrator, register a single `bookkeeper(task: str) -> str` tool that delegates to `bookkeeper_agent.run_sync()` at runtime. This enables per-agent LLM model selection, isolated agent contexts, and an extensible registry pattern for future specialist agents.

---

## Current State (as-is)

```
User → Orchestrator agent
         ├── tool: categorise_transaction(tx_id, category)    ← direct function call
         ├── tool: list_transactions(query, limit)             ← direct function call
         ├── tool: get_transaction_stats()                     ← direct function call
         └── tool: list_accounts()                             ← direct function call

Problems:
• All tools share the orchestrator's single LLM context/state
• Adding a new specialist agent means registering N individual tool functions
• Each tool has a narrow, function-call interface — no natural-language task boundary
• Single AUTOFI_LLM_MODEL for all agents — no multi-vendor support
```

## Desired State (to-be)

```
User → Orchestrator agent  (model: claude-sonnet-4)
         └── tool: bookkeeper(task: str) → str
                  └── runs → BookkeeperAgent.run_sync(task)
                              ├── categorise_transaction
                              ├── list_transactions
                              ├── get_transaction_stats
                              └── list_accounts

Future:
         └── tool: reconciler(task: str) → str
         └── tool: payments(task: str) → str
         └── tool: forecaster(task: str) → str

Benefits:
• Sub-agent runs in its own LLM context — independent system prompt + model
• Each sub-agent can use a different LLM vendor (OPENAI / ANTHROPIC / GEMINI)
• Natural-language task boundary — the orchestrator LLM describes what to do, not which function to call
• Extensible: new specialist = add to registry, delegation tool auto-generated
• Error isolation: a sub-agent failure doesn't corrupt the orchestrator's turn
```

---

## Implementation Steps

### Step 1: Per-Agent Model Settings
- [x] Add `AGENT_MODELS` dict in `src/agents/settings.py` with env var overrides per agent name
- [x] Add `get_model_for_agent(agent_name: str) -> str` that reads `AUTOFI_{AGENT}_MODEL` or falls back to a default
- [x] Update `PROVIDER_ENV_VARS` to support per-agent model resolution *(no change needed — provider resolution is already generic)*
- [x] Update `bookkeeper.py` to use `get_model_for_agent("bookkeeper")` instead of `get_model_string()`
- [x] Update `orchestrator.py` to use `get_model_for_agent("orchestrator")`

### Step 2: Add Agent Registry + Delegation Tool
- [x] Create `src/agents/registry.py` — holds `OrchestratorDeps`, `AgentEntry`, `AGENT_REGISTRY: dict[str, AgentEntry]`, `_make_delegation_tool()`, `wire_orchestrator_tools()`
- [x] `_make_delegation_tool(name, entry)` returns a sync `delegator(ctx, task)` function that calls `entry.agent.run_sync(task, deps=entry.deps_factory(ctx.deps))`
- [x] Register bookkeeper in the registry via `register_agent("bookkeeper", AgentEntry(...))`
- [x] Auto-generate delegation tools via `wire_orchestrator_tools(orchestrator_agent)`

### Step 3: OrchestratorDeps
- [x] Create `OrchestratorDeps` in `registry.py` with `db_path: Path` and optional `model: Any` (for test model propagation)
- [x] The delegation tool resolves sub-agent deps via `entry.deps_factory(ctx.deps)` — e.g. `BookkeeperDeps(db_path=od.db_path)`
- [x] If `ctx.deps.model` is set (test mode), it's forwarded to the sub-agent's `run_sync()` so TestModel cascades

### Step 4: Remove Flat Tool Registration
- [x] Remove individual tool function imports from `orchestrator.py` (`categorise_transaction`, `list_transactions`, etc.)
- [x] Remove `orchestrator_agent.tool(...)` lines for individual functions — replaced by `wire_orchestrator_tools()`
- [x] Update system prompt to describe delegation pattern: "You must ALWAYS delegate to specialist agents — never answer financial questions yourself"

### Step 5: Update chat.py
- [x] `chat.py` imports `_default_deps` from `orchestrator` instead of `bookkeeper` — returns `OrchestratorDeps` now

### Step 6: Tests
- [x] `test_orchestrator_has_delegation_tool` — verifies `bookkeeper` tool is registered on orchestrator
- [x] `test_delegation_invokes_sub_agent` — passes `TestModel` via `OrchestratorDeps.model`, proves full delegation chain works (orchestrator → bookkeeper sub-agent → tool execution)
- [x] `test_orchestrator_multiturn_conversation` — updated to use `OrchestratorDeps`

---

## Files to Modify

| File | Change |
|------|--------|
| `src/agents/settings.py` | Add `AGENT_MODELS` dict, `get_model_for_agent(name)` |
| `src/agents/orchestrator.py` | Replace flat tool imports with registry-based delegation; use `OrchestratorDeps` |
| `src/agents/bookkeeper.py` | Use `get_model_for_agent("bookkeeper")` |
| `src/agents/registry.py` | **NEW** — agent registry + delegation tool factory |
| `src/cli/chat.py` | Minor: pass orchestrator deps (or no change if backward-compatible) |
| `tests/test_orchestrator.py` | Update tests for delegation pattern |

## Considerations

- The delegation tool is `async def` — `run_sync` wraps it synchronously, but the sub-agent call `agent.run_sync()` inside can be sync (Pydantic AI supports both)
- Each sub-agent gets a **fresh conversation** per delegation (no message_history passed) — the orchestrator's prompt IS the task description
- API keys remain env-var-based — each provider reads its own key automatically via pydantic-ai
- For error handling: if the sub-agent errors, the delegation tool catches and returns an error string; the orchestrator LLM decides what to tell the user
- Existing `tests/test_bookkeeper_tools.py` should continue passing unchanged — the bookkeeper agent itself doesn't change
