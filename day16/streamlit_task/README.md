# 📈 FinSight AI — Financial RAG System

**Planner → Executor → Validator** architecture with a Streamlit UI and PKL-based persistence.

---

## Architecture

```
Query ──► Planner ──► Executor ──► Validator ──► Result
              │           │             │
         Classifies   Retrieves    Checks
         intent +     chunks +    faithfulness,
         tunes k,     calls LLM   relevance,
         strategy              source coverage
                   └──────────────────────────────► PKL Store
                                (sessions, index, history)
```

### Components

| Layer | File | Role |
|-------|------|------|
| **Planner** | `rag_engine.py` | Classifies query intent (revenue / risk / liquidity / trend / comparative / factual), selects retrieval_k, chunk_size, and strategy |
| **Executor** | `rag_engine.py` | Runs MMR retrieval on FAISS, formats context, calls Azure OpenAI / OpenAI |
| **Validator** | `rag_engine.py` | Scores faithfulness (context overlap), relevance (keyword match), source coverage; flags warnings |
| **PKL Store** | `rag_engine.py` | Persists sessions, FAISS index, query history as `.pkl` files |
| **Streamlit UI** | `app.py` | Full UI with pipeline status, metrics, answer display, history, session browser |

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set credentials (optional — can enter in sidebar)
```bash
cp .env.example .env
# Edit .env with your Azure/OpenAI keys
```

### 3. Run
```bash
streamlit run app.py
```

---

## PKL Storage Layout

```
rag_store/
├── faiss_index.pkl    # FAISS vectorstore + chunks + metadata
├── sessions.pkl       # All RAG sessions (Plan + Execution + Validation per query)
├── query_history.pkl  # Flat history list for the History tab
└── config.pkl         # Last-used configuration
```

---

## Usage

1. Open the sidebar and enter your Azure OpenAI or OpenAI credentials.
2. Click **Build Index** (first run only — subsequent runs load from PKL).
3. Type a financial question or click a sample query chip.
4. Click **▶ Run** — watch the **Planner → Executor → Validator** pipeline animate.
5. See the answer, validation scores, retrieved chunks, and planner JSON.
6. Browse the **History** and **Session** tabs to review past queries.

---

## Supported Query Intents (Planner)

| Intent | Example |
|--------|---------|
| `revenue` | "What was Apple's gross margin?" |
| `liquidity` | "How much cash did Apple have?" |
| `risk` | "What risks does Apple face?" |
| `comparative` | "Compare iPhone vs Mac revenue" |
| `trend` | "How did Services revenue grow YoY?" |
| `factual` | "How many active devices does Apple have?" |
