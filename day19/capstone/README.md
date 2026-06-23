# Agentic System — Architecture Note

## System at a Glance

This capstone implements a **production-grade agentic loop** on top of Anthropic Claude.
Every concern (memory, tools, approval, observability, reliability) is isolated into a
single-responsibility class or decorator, making each layer independently testable and
swappable.

---

## Component Inventory

| # | Component | Class / Function | Role |
|---|-----------|-----------------|------|
| 1 | **Short-term memory** | `ShortTermMemory` | Redis `RPUSH`/`LTRIM` sliding window, TTL-keyed per session |
| 2 | **Long-term memory** | `LongTermMemory` | ChromaDB cosine-similarity store; every Q→A pair is upserted |
| 3 | **Tool: calculator** | `tool_calculator` | Safe `eval()` over a whitelist; fully sync |
| 4 | **Tool: web_search** | `tool_web_search` | Mock HTTP layer (swap body for Brave / Serper / Tavily) |
| 5 | **Tool: async_queue** | `tool_async_queue` | `async`; Redis `RPUSH`/`BLPOP` FIFO; gate-guarded |
| 6 | **Human approval gate** | `ApprovalGate` | Intercepts `GATED_TOOLS`; interactive `input()` or `auto_approve=True` for CI |
| 7 | **Intent router** | `classify_intent` + `ChainRouter.route()` | Keyword rules → sub-chain dispatch |
| 8 | **Agentic loop** | `ChainRouter._llm_chain()` | Up to 5 tool rounds per user turn |
| 9 | **Retry decorator** | `@with_retry` (Tenacity) | 3 attempts, exponential back-off 2 → 8 s on `APIStatusError` / `APIConnectionError` |
| 10 | **Prompt caching** | `cache_control: ephemeral` | Caches KV state of system block for 5 min; up to 90 % cost/latency reduction on warm calls |
| 11 | **Span tracer** | `span()` context-manager | Lightweight OTel-inspired spans; `show_trace()` renders a Rich table |

---

## Data Flow (single turn)

```
User message
     │
     ▼
classify_intent()          ← keyword rules → intent label
     │
     ├─ "memory_chain"  →  LongTermMemory.recall()  →  return (no LLM)
     │
     └─ all others      →  _llm_chain()
                               │
                               ├── LongTermMemory.recall(k=2)    inject into system prompt
                               ├── ShortTermMemory.as_messages()  prepend history
                               │
                               ▼
                        Anthropic API (claude-sonnet-4-6)
                        system: [{…, cache_control: ephemeral}]
                               │
                    stop_reason == "tool_use"?
                          │           │
                         YES          NO
                          │           └── return final text
                          ▼
                    for each tool_use block:
                      ApprovalGate.check()
                          │ approved?
                         YES           NO
                          │             └── inject "Denied" result
                          ▼
                    dispatch to tool_calculator /
                             tool_web_search /
                             tool_async_queue  (await)
                          │
                          ▼
                    append tool_result → messages
                    loop back to API call (max 5 rounds)
                               │
                    final answer
                          │
                    ShortTermMemory.push(user_msg + answer)
                    LongTermMemory.remember(Q+A)
                    Span tracer records all durations
```

---

## Memory Architecture

### Short-Term (Redis)

```
Key pattern : session:<session_id>:msgs
Data type   : Redis LIST
Write       : RPUSH → LTRIM to last window=20 entries
TTL         : EXPIRE session_ttl=3600 s (refreshed on every push)
Read        : LRANGE 0 -1 → deserialize JSON → Anthropic messages format
```

The window keeps only the most recent 20 messages (configurable).  When the TTL
expires the key is evicted automatically — no manual cleanup needed.

### Long-Term (ChromaDB)

```
Collection  : agent_longterm
Distance    : cosine
Embed fn    : _hash_embed (demo) — replace with text-embedding-3-small or similar
Write       : col.add(id, embedding, document, metadata)
Read        : col.query(query_embedding, n_results=k) → ranked results
```

Every completed Q→A pair is upserted so the agent accumulates domain knowledge
across sessions.  The system prompt for every LLM call injects the top-2 recalled
memories, grounding the model without exceeding context limits.

---

## Tool Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Sync tools stay sync** | `calculator`, `web_search` — no async overhead |
| **I/O-bound tools are async** | `async_task_queue` — awaitable, non-blocking |
| **All tools return dicts** | JSON-serialisable; injected as `tool_result` content |
| **Gating is per-tool, not per-request** | `GATED_TOOLS` set; easy to extend |
| **Schemas drive the LLM** | `TOOL_SCHEMAS` list passed verbatim to `tools=` |

---

## Retry Strategy

```
Library     : Tenacity
Attempts    : 3
Wait        : exponential  min=2 s  max=8 s  multiplier=2
Retry on    : anthropic.APIStatusError  (429, 529, 5xx)
              anthropic.APIConnectionError
Side effects: logs each retry attempt via Rich console
Reraise     : True — bubble up after all attempts exhausted
```

---

## Prompt Caching Strategy

The system block is the ideal caching target because:

1. It is **long** (injected memories + instructions).
2. It is **stable** — only the top-2 recalled memories change it, and those change
   infrequently relative to the 5-minute cache window.
3. It is **prepended** to every call — satisfying Anthropic's prefix-caching requirement.

Cache hit savings are visible in `resp.usage.cache_read_input_tokens`.

---

## Extension Points

| What to swap | How |
|---|---|
| Real embeddings | Replace `_hash_embed` with `openai.embeddings.create()` or a local model |
| Real web search | Replace `tool_web_search` body with `httpx.get(SERPER_URL, …)` |
| Persistent ChromaDB | Pass `chromadb.PersistentClient(path="./chroma_db")` to `LongTermMemory` |
| Live Redis | Set `REDIS_HOST` / `REDIS_PORT` env vars; `MockRedis` is auto-bypassed |
| Interactive gate | Set `ApprovalGate(auto_approve=False)` |
| Different model | Change `MODEL` constant in §2 |
| Real OTel export | Replace `_SPANS` list with `opentelemetry.trace` SDK spans |

---

## File Map

```
capstone_agentic_system.ipynb   Main notebook (18 sections, run top-to-bottom)
architecture_note.md            This document
```

*Generated — Capstone Agentic System*
