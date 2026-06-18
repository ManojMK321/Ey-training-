# 🧠 Memory Architecture in Financial RAG
## Long-Term Memory (LTM) vs Short-Term Memory (STM) within the Planner → Executor → Validator Pipeline for Annual Budgeting

---

## 1. Overview

In cognitive science, **Long-Term Memory (LTM)** stores persistent knowledge accumulated over time, while **Short-Term Memory (STM)** holds information that is actively in use within a single working session. When this distinction is mapped onto a financial RAG system used for **annual budgeting**, it produces a clean, defensible separation of concerns across all three pipeline stages.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ANNUAL BUDGETING RAG PIPELINE                       │
│                                                                         │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐   │
│   │   PLANNER    │────►│   EXECUTOR   │────►│     VALIDATOR        │   │
│   │              │     │              │     │                      │   │
│   │ Reads LTM    │     │ Uses STM     │     │ Writes to LTM        │   │
│   │ Writes STM   │     │ Enriches STM │     │ Clears STM           │   │
│   └──────────────┘     └──────────────┘     └──────────────────────┘   │
│          ▲                                           │                  │
│          │                LTM STORE (PKL)            │                  │
│          └───────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Memory Type Definitions in Budgeting Context

### 🗄️ Long-Term Memory (LTM)

LTM is everything that **persists across sessions, fiscal years, and user queries**. It is built up incrementally, stored to disk (PKL / FAISS), and consulted at the start of every new planning cycle. In budgeting terms, LTM is your institutional knowledge base.

| Attribute | Value |
|-----------|-------|
| **Persistence** | Survives process restarts, new fiscal years |
| **Update frequency** | Quarterly / annually |
| **Storage mechanism** | `faiss_index.pkl`, `sessions.pkl`, `config.pkl` |
| **Access in pipeline** | Read by Planner; updated by Validator |
| **Analogy** | CFO's institutional memory, prior-year actuals, board-approved policies |

### ⚡ Short-Term Memory (STM)

STM is everything that **exists only for the duration of a single query or planning session**. It is created by the Planner, enriched by the Executor, evaluated by the Validator, and then either promoted to LTM or discarded. In budgeting terms, STM is the analyst's working scratchpad.

| Attribute | Value |
|-----------|-------|
| **Persistence** | Single query / session lifetime |
| **Update frequency** | Every query invocation |
| **Storage mechanism** | `st.session_state`, in-memory Python objects |
| **Access in pipeline** | Written by Planner; consumed by Executor and Validator |
| **Analogy** | Analyst's notepad during a budget review meeting |

---

## 3. LTM vs STM Breakdown by Pipeline Stage

### Stage 1 — 🗺️ Planner

The Planner is the **memory-orchestration hub**. It reads LTM to understand historical context and writes STM to frame the current query.

```
Planner
├── READS from LTM
│   ├── Prior-year budget baselines (FAISS index of archived 10-K / budget docs)
│   ├── Historical intent classifications (which query patterns → which strategy)
│   ├── Approved retrieval configurations (chunk_size, k, MMR lambda)
│   └── Organisation-level fiscal calendar (Q1–Q4 boundaries, lock dates)
│
└── WRITES to STM
    ├── Plan object  { intent, retrieval_k, chunk_size, strategy }
    ├── Required source categories  [ "Budget_FY24", "Risk", "Liquidity" ]
    ├── Budget dimension tags  [ "OPEX", "CAPEX", "Headcount", "Revenue" ]
    └── Query timestamp + session_id
```

**Annual budgeting specifics:**

When a query arrives such as *"What is the projected CAPEX for FY2025 given FY2024 actuals?"*, the Planner:

1. **Reads LTM** — loads the FY2024 10-K embedding index and prior budget lock configs.
2. **Classifies intent** — `trend` (year-over-year projection), not `factual`.
3. **Writes STM** — sets `retrieval_k=6`, `chunk_size=512`, tags `["CAPEX", "FY2024", "FY2025"]`, records that sources `Budget_FY24_Liquidity` and `Budget_FY24_CapEx` are required.

---

### Stage 2 — ⚡ Executor

The Executor is **purely STM-driven**. It does not read from or write to disk. Everything it needs is in the Plan object (STM), and everything it produces enriches the current execution context (also STM).

```
Executor
├── READS from STM
│   ├── Plan.retrieval_k, Plan.chunk_size, Plan.strategy
│   ├── Plan.required_sources (directs MMR retriever)
│   └── Plan.intent (shapes prompt template selection)
│
├── USES LTM implicitly
│   └── FAISS vectorstore (already loaded into memory from PKL — treat as read-only LTM)
│
└── WRITES to STM
    ├── ExecutionResult.retrieved_chunks  [ { source, content } × k ]
    ├── ExecutionResult.answer            (LLM response)
    ├── ExecutionResult.latency_s
    └── ExecutionResult.token_count
```

**Annual budgeting specifics:**

For a CAPEX projection query, the Executor:

1. **Reads STM Plan** — MMR retrieves 6 chunks from FAISS (LTM) filtered toward `Budget_FY24_Liquidity`.
2. **Calls LLM** — injects retrieved chunks as context; prompt template includes `"Be conservative with forward projections."` (a budgeting-mode instruction set in the Plan).
3. **Writes STM result** — stores the answer, latency (target < 3s), and all retrieved chunk metadata for the Validator.

---

### Stage 3 — ✅ Validator

The Validator is the **LTM gatekeeper**. It reads both STM (the just-produced result) and LTM (historical benchmarks), evaluates quality, and decides what gets promoted into long-term knowledge.

```
Validator
├── READS from STM
│   ├── ExecutionResult.answer
│   ├── ExecutionResult.retrieved_chunks
│   └── Plan.required_sources, Plan.intent
│
├── READS from LTM
│   ├── Historical faithfulness benchmarks (target ≥ 0.85)
│   ├── Prior validation reports for same query type
│   └── Budget accuracy thresholds (org-level SLAs)
│
└── WRITES to LTM  (on PASS)
    ├── Validated answer → sessions.pkl (durable session record)
    ├── ValidationReport → query_history.pkl (audit trail)
    ├── Promoted Q&A pair → golden_set.pkl (evaluation dataset)
    └── Updated intent→strategy mapping (improves future Planner routing)
│
└── DISCARDS STM  (always)
    └── Clears Plan, ExecutionResult from session_state after persistence
```

**Annual budgeting specifics:**

The Validator applies stricter thresholds during the budget lock period (a rule stored in LTM):

- `faithfulness_score ≥ 0.90` (higher than the default 0.85 — budget answers must be grounded).
- `source_coverage = 1.0` — all required budget sources must be cited.
- If a number is cited (e.g., `$10.959B CAPEX`), a numeric extraction check confirms it appears verbatim in a retrieved chunk.
- **PASS** → writes the validated pair to `golden_set.pkl` for future RAGAS evaluation.
- **FAIL** → raises a warning in the UI and does **not** promote to LTM.

---

## 4. Annual Budgeting Data Taxonomy

The table below maps real budgeting artefacts to their memory tier and pipeline stage.

| Budget Artefact | Memory Type | Where Stored | Pipeline Stage |
|-----------------|-------------|--------------|----------------|
| FY2023, FY2024 10-K PDFs | **LTM** | `faiss_index.pkl` | Executor reads |
| Board-approved fiscal calendar | **LTM** | `config.pkl` | Planner reads |
| Historical query→intent mappings | **LTM** | `sessions.pkl` | Planner reads |
| RAGAS golden set (validated Q&A pairs) | **LTM** | `golden_set.pkl` | Validator writes |
| Faithfulness SLA thresholds | **LTM** | `config.pkl` | Validator reads |
| Current query text | **STM** | `st.session_state["query"]` | Planner consumes |
| Classified intent + tags | **STM** | `Plan` object | Executor reads |
| Retrieved FAISS chunks (this query) | **STM** | `ExecutionResult.retrieved_chunks` | Validator reads |
| Draft LLM answer | **STM** | `ExecutionResult.answer` | Validator reads |
| Validation scores (pre-commit) | **STM** | `ValidationReport` (in-memory) | Validator holds |
| Latency measurement | **STM** | `ExecutionResult.latency_s` | Validator checks |

---

## 5. Memory Lifecycle: Full Annual Budget Cycle

```
JANUARY — Budget Planning Opens
│
│  Planner reads LTM:
│    ← FY2023 actuals index (FAISS)
│    ← Last year's Planner configs
│    ← Board-approved FY2024 targets
│
├──► QUERY: "What was OPEX growth FY22→FY23?"
│      STM: Plan{ intent=trend, k=5 }
│      STM: Result{ answer, chunks, latency }
│      STM: Report{ faith=0.91, PASS }
│      LTM ← sessions.pkl updated
│      LTM ← golden_set.pkl gains one Q&A pair
│
MARCH — Budget Lock
│
│  Validator tightens LTM thresholds:
│    config.pkl → { "faithfulness_floor": 0.90, "lock_period": true }
│
├──► QUERY: "Project FY2025 CAPEX from FY2024 actuals"
│      STM: Plan{ intent=trend, required_sources=["Liquidity","CapEx"] }
│      STM: Result{ answer includes $10.959B }
│      Validator checks: number present in chunks? ✅
│      Validator checks: source_coverage == 1.0? ✅
│      LTM ← validated answer archived
│
JUNE — Mid-Year Review
│
│  LTM enriched with H1 actuals PDF → rebuild FAISS index
│  All prior STM discarded; new sessions begin
│
DECEMBER — Year-End Close
│
│  Validator promotes full golden set to LTM
│  RAGAS run against golden_set.pkl → faithfulness report saved to LTM
│  Config updated for FY2026 planning cycle
```

---

## 6. PKL File Roles: LTM vs STM Persistence

```
rag_store/
│
├── faiss_index.pkl      ← LTM  │ Vectorstore + chunks + build metadata
│                                │ Updated: when documents are re-ingested
│                                │ Read by: Executor (via loaded vectorstore)
│
├── sessions.pkl         ← LTM  │ All past RAG sessions (Plan+Execution+Validation)
│                                │ Updated: after every PASS validation
│                                │ Read by: Planner (historical routing patterns)
│
├── query_history.pkl    ← LTM  │ Flat audit trail — every query + scores
│                                │ Updated: every query (pass or fail)
│                                │ Read by: History tab, RAGAS evaluation
│
├── golden_set.pkl       ← LTM  │ Validated Q&A pairs for offline evaluation
│                                │ Updated: Validator on PASS with score ≥ 0.90
│                                │ Read by: RAGAS step 8
│
└── config.pkl           ← LTM  │ Retrieval settings, SLA thresholds, lock flags
                                 │ Updated: manually or at budget cycle boundaries
                                 │ Read by: Planner + Validator
```

> **STM** lives in `st.session_state` and in-memory Python dataclass instances. Nothing in `rag_store/` is STM. If a process restarts, STM is gone; LTM survives.

---

## 7. Code Reference: Where LTM and STM Live in `rag_engine.py`

### LTM structures

```python
# PKLStore — all LTM persistence
class PKLStore:
    def save_index(self, vectorstore, chunks, metadata): ...   # LTM write
    def load_index(self):                                 ...   # LTM read
    def save_session(self, session: RAGSession):          ...   # LTM write
    def append_history(self, record: dict):               ...   # LTM write
    def save_config(self, config: dict):                  ...   # LTM write
    def load_config(self) -> dict:                        ...   # LTM read

# RAGSession — durable record of a full session (promoted to LTM on save)
@dataclass
class RAGSession:
    session_id: str
    created_at: str
    queries:     list   # Plans (after session ends → LTM)
    executions:  list   # Results
    validations: list   # Reports
    index_metadata: dict
```

### STM structures

```python
# Plan — created fresh per query, lives in st.session_state["current_plan"]
@dataclass
class Plan:
    query: str
    intent: str             # STM: classified this session
    required_sources: list  # STM: expected for this query only
    retrieval_k: int        # STM: tuned for this query
    chunk_size: int
    strategy: str
    timestamp: str

# ExecutionResult — in-flight result, st.session_state["current_result"]
@dataclass
class ExecutionResult:
    query: str
    plan: Plan
    retrieved_chunks: list  # STM: only relevant to this query
    answer: str             # STM: draft answer
    latency_s: float
    token_count: int

# ValidationReport — in-memory evaluation, st.session_state["current_report"]
@dataclass
class ValidationReport:
    faithfulness_score: float   # STM until Validator commits to LTM
    relevance_score: float
    source_coverage: float
    passed: bool
    warnings: list
```

### Promotion logic (STM → LTM)

```python
# RAGOrchestrator.run() — the promotion gate
def run(self, query, config):
    plan   = self.planner.plan(query, config)      # creates STM Plan
    result = self.executor.execute(plan)            # creates STM ExecutionResult
    report = self.validator.validate(result)        # creates STM ValidationReport

    # ── Promotion: STM → LTM ──────────────────────────────
    if self._session:
        self._session.queries.append(asdict(plan))         # Plan → LTM session
        self._session.executions.append({ ... })           # Result → LTM session
        self._session.validations.append(asdict(report))   # Report → LTM session
        self.store.save_session(self._session)             # flush to PKL

    self.store.append_history({ ... })                     # audit trail → LTM

    return plan, result, report
    # STM objects returned to UI; cleared from session_state on "New Query"
```

---

## 8. Design Principles

### Why separate LTM and STM?

**Auditability.** Budget answers that survive into LTM are validated before promotion. A raw draft LLM answer (STM) is never directly committed; only Validator-passed results enter the institutional record.

**Reproducibility.** The FAISS index (LTM) is a deterministic snapshot of the documents ingested at a point in time. Re-running the same query against the same index produces the same retrieval context — essential for audit trails in regulated finance environments.

**Cost efficiency.** Embedding and indexing 10-K filings is expensive. LTM prevents re-doing it on every session. STM is lightweight and disposable.

**Progressive refinement.** Each budget cycle, the golden Q&A set (LTM) grows. The next RAGAS evaluation benchmarks against richer ground truth, and the Planner's intent classifier improves as historical sessions accumulate in `sessions.pkl`.

---

## 9. Quick-Reference Cheat Sheet

```
┌─────────────────────────────────┬──────────────────────────────────────┐
│         LONG-TERM MEMORY         │         SHORT-TERM MEMORY            │
├─────────────────────────────────┼──────────────────────────────────────┤
│ FAISS vectorstore               │ Plan object (intent, k, tags)        │
│ Historical sessions (PKL)       │ Retrieved chunks (this query)        │
│ Query audit history             │ Draft LLM answer                     │
│ Golden Q&A evaluation set       │ Validation scores (pre-commit)       │
│ Retrieval config & SLA thresholds│ Latency measurement                 │
│ Fiscal calendar / lock flags    │ Token count estimate                 │
│ Prior-year budget documents     │ Session-state UI flags               │
├─────────────────────────────────┼──────────────────────────────────────┤
│ Survives restarts ✅             │ Lost on restart ❌                   │
│ Built over fiscal year          │ Built per query                      │
│ Written by Validator (on PASS)  │ Written by Planner                   │
│ Read by Planner                 │ Read by Executor & Validator         │
│ Stored in: rag_store/*.pkl      │ Stored in: st.session_state / RAM    │
└─────────────────────────────────┴──────────────────────────────────────┘
```

---

*FinSight AI · Enterprise AI Engineering Series · Day 15*
