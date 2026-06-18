"""
rag_engine.py — Financial RAG Engine
Planner → Executor → Validator architecture with PKL-based persistence
"""

import os
import pickle
import time
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from pathlib import Path

# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Plan:
    query: str
    intent: str              # classify: factual | comparative | trend | risk
    required_sources: list   # expected source categories
    retrieval_k: int
    chunk_size: int
    strategy: str            # dense | hybrid
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ExecutionResult:
    query: str
    plan: Plan
    retrieved_chunks: list   # list of {source, content, score}
    answer: str
    latency_s: float
    token_count: int
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ValidationReport:
    query: str
    answer: str
    faithfulness_score: float
    relevance_score: float
    source_coverage: float
    passed: bool
    warnings: list
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class RAGSession:
    session_id: str
    created_at: str
    queries: list = field(default_factory=list)           # list of Plan
    executions: list = field(default_factory=list)        # list of ExecutionResult
    validations: list = field(default_factory=list)       # list of ValidationReport
    index_metadata: dict = field(default_factory=dict)


# ─── PKL Store ────────────────────────────────────────────────────────────────

class PKLStore:
    """Persistent store for sessions, index, and query history."""

    def __init__(self, store_dir: str = "./rag_store"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(exist_ok=True)
        self.session_file  = self.store_dir / "sessions.pkl"
        self.index_file    = self.store_dir / "faiss_index.pkl"
        self.history_file  = self.store_dir / "query_history.pkl"
        self.config_file   = self.store_dir / "config.pkl"

    # ── sessions ──
    def save_session(self, session: RAGSession):
        sessions = self.load_all_sessions()
        sessions[session.session_id] = session
        self._write(self.session_file, sessions)

    def load_all_sessions(self) -> dict:
        return self._read(self.session_file, {})

    def load_session(self, session_id: str) -> Optional[RAGSession]:
        return self.load_all_sessions().get(session_id)

    # ── FAISS index + chunks ──
    def save_index(self, vectorstore, chunks: list, metadata: dict):
        self._write(self.index_file, {
            "vectorstore": vectorstore,
            "chunks": chunks,
            "metadata": metadata,
            "saved_at": datetime.now().isoformat()
        })

    def load_index(self):
        data = self._read(self.index_file, None)
        if data:
            return data["vectorstore"], data["chunks"], data["metadata"]
        return None, None, None

    def index_exists(self) -> bool:
        return self.index_file.exists()

    # ── query history ──
    def append_history(self, record: dict):
        history = self._read(self.history_file, [])
        history.append(record)
        self._write(self.history_file, history)

    def load_history(self) -> list:
        return self._read(self.history_file, [])

    def clear_history(self):
        self._write(self.history_file, [])

    # ── config ──
    def save_config(self, config: dict):
        self._write(self.config_file, config)

    def load_config(self) -> dict:
        return self._read(self.config_file, {})

    # ── helpers ──
    def _write(self, path: Path, obj):
        with open(path, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)

    def _read(self, path: Path, default):
        if not path.exists():
            return default
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return default

    def store_stats(self) -> dict:
        stats = {}
        for name, path in [
            ("sessions", self.session_file),
            ("index",    self.index_file),
            ("history",  self.history_file),
        ]:
            if path.exists():
                size_kb = path.stat().st_size / 1024
                stats[name] = f"{size_kb:.1f} KB"
            else:
                stats[name] = "not found"
        return stats


# ─── Planner ──────────────────────────────────────────────────────────────────

class Planner:
    """
    Analyses the incoming query and produces a structured Plan.
    Determines: intent, retrieval strategy, k, chunk_size.
    """

    INTENT_RULES = {
        "comparative": ["compare", "vs", "versus", "difference", "better", "worse"],
        "trend":       ["trend", "growth", "increase", "decrease", "over time", "year over year", "yoy"],
        "risk":        ["risk", "challenge", "threat", "uncertainty", "concern"],
        "liquidity":   ["cash", "liquidity", "capital", "debt", "balance sheet"],
        "revenue":     ["revenue", "sales", "income", "profit", "margin", "earnings"],
    }

    def plan(self, query: str, config: dict) -> Plan:
        q_lower = query.lower()

        # Classify intent
        intent = "factual"
        for label, keywords in self.INTENT_RULES.items():
            if any(kw in q_lower for kw in keywords):
                intent = label
                break

        # Tune retrieval params per intent
        if intent == "comparative":
            k, chunk_size = 6, 256
        elif intent in ("trend", "revenue"):
            k, chunk_size = 5, 512
        elif intent == "risk":
            k, chunk_size = 4, 512
        else:
            k, chunk_size = config.get("retrieval_k", 4), config.get("chunk_size", 512)

        # Determine strategy
        strategy = config.get("retrieval_strategy", "dense")

        # Expected source categories
        required_sources = self._infer_sources(intent)

        return Plan(
            query=query,
            intent=intent,
            required_sources=required_sources,
            retrieval_k=k,
            chunk_size=chunk_size,
            strategy=strategy,
        )

    def _infer_sources(self, intent: str) -> list:
        mapping = {
            "revenue":     ["Risk", "Products"],
            "liquidity":   ["Liquidity"],
            "risk":        ["Risk"],
            "comparative": ["Risk", "Products", "Liquidity"],
            "trend":       ["Risk", "Products"],
            "factual":     [],
        }
        return mapping.get(intent, [])


# ─── Executor ─────────────────────────────────────────────────────────────────

class Executor:
    """
    Executes the plan: retrieves context and calls the LLM.
    Supports dense and hybrid retrieval modes.
    """

    RAG_PROMPT_TEMPLATE = """You are FinSight, an AI research analyst for a Tier-1 investment bank.
Answer the analyst's question ONLY using the provided context.
If the context does not contain the answer, say: "Insufficient information in the retrieved context."
Always cite the specific source document at the end of your answer.
Be concise and precise — this is for financial professionals.

CONTEXT:
{context}

ANALYST QUESTION: {question}

ANSWER (cite source):"""

    def __init__(self, vectorstore, embedding_model, llm):
        self.vectorstore     = vectorstore
        self.embedding_model = embedding_model
        self.llm             = llm

    def execute(self, plan: Plan) -> ExecutionResult:
        t0 = time.time()

        # Build retriever per plan spec
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k":           plan.retrieval_k,
                "fetch_k":     plan.retrieval_k * 3,
                "lambda_mult": 0.7,
            },
        )

        # Retrieve
        docs = retriever.invoke(plan.query)
        retrieved_chunks = [
            {"source": d.metadata.get("source", "unknown"), "content": d.page_content}
            for d in docs
        ]

        # Format context
        context = "\n\n".join(
            f"[Source: {c['source']}]\n{c['content']}" for c in retrieved_chunks
        )

        # Generate answer
        prompt = self.RAG_PROMPT_TEMPLATE.format(
            context=context, question=plan.query
        )
        response = self.llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)

        latency = time.time() - t0

        # Rough token estimate
        token_count = len(prompt.split()) + len(answer.split())

        return ExecutionResult(
            query=plan.query,
            plan=plan,
            retrieved_chunks=retrieved_chunks,
            answer=answer,
            latency_s=round(latency, 3),
            token_count=token_count,
        )


# ─── Validator ────────────────────────────────────────────────────────────────

class Validator:
    """
    Heuristic + LLM-based validation of the answer.
    Checks: faithfulness (answer grounded in context?), relevance, source coverage.
    """

    def __init__(self, llm=None):
        self.llm = llm

    def validate(self, result: ExecutionResult) -> ValidationReport:
        warnings = []

        # 1) Source coverage
        required  = set(result.plan.required_sources)
        retrieved = {c["source"].split("_")[2] if "_" in c["source"] else c["source"]
                     for c in result.retrieved_chunks}
        if required:
            matched = sum(1 for r in required if any(r in ret for ret in retrieved))
            source_coverage = matched / len(required)
            if source_coverage < 0.5:
                warnings.append(f"Low source coverage: expected {required}, got {retrieved}")
        else:
            source_coverage = 1.0

        # 2) Faithfulness — heuristic: answer terms overlap with context
        context_text = " ".join(c["content"].lower() for c in result.retrieved_chunks)
        answer_words = set(result.answer.lower().split())
        context_words = set(context_text.split())
        overlap = len(answer_words & context_words) / max(len(answer_words), 1)
        faithfulness_score = min(1.0, overlap * 3)   # scale heuristic

        # flag "Insufficient information" answers
        if "insufficient information" in result.answer.lower():
            faithfulness_score = 0.5
            warnings.append("Model returned 'Insufficient information' — consider expanding retrieval k")

        # 3) Relevance — does the answer contain query keywords?
        q_words = set(result.plan.query.lower().split()) - {"what", "how", "was", "did", "is", "the", "a", "an"}
        relevance_score = len(q_words & answer_words) / max(len(q_words), 1)
        relevance_score = min(1.0, relevance_score * 2)

        if relevance_score < 0.3:
            warnings.append("Answer may not address the question directly")

        # 4) Latency check
        if result.latency_s > 5:
            warnings.append(f"High latency: {result.latency_s:.1f}s (target < 3s)")

        # Overall pass
        passed = faithfulness_score >= 0.4 and relevance_score >= 0.3 and not any(
            "Low source coverage" in w for w in warnings
        )

        return ValidationReport(
            query=result.query,
            answer=result.answer,
            faithfulness_score=round(faithfulness_score, 3),
            relevance_score=round(relevance_score, 3),
            source_coverage=round(source_coverage, 3),
            passed=passed,
            warnings=warnings,
        )


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class RAGOrchestrator:
    """
    Wires Planner → Executor → Validator.
    Manages session state and PKL persistence.
    """

    def __init__(self, store: PKLStore):
        self.store    = store
        self.planner  = Planner()
        self.executor  = None
        self.validator = None
        self._session: Optional[RAGSession] = None

    def load_or_init_session(self, session_id: str) -> RAGSession:
        session = self.store.load_session(session_id)
        if not session:
            session = RAGSession(
                session_id=session_id,
                created_at=datetime.now().isoformat(),
            )
        self._session = session
        return session

    def setup_executor(self, vectorstore, embedding_model, llm):
        self.executor  = Executor(vectorstore, embedding_model, llm)
        self.validator = Validator(llm)

    def run(self, query: str, config: dict) -> tuple[Plan, ExecutionResult, ValidationReport]:
        if not self.executor:
            raise RuntimeError("Call setup_executor() first.")

        # Step 1 — Plan
        plan = self.planner.plan(query, config)

        # Step 2 — Execute
        result = self.executor.execute(plan)

        # Step 3 — Validate
        report = self.validator.validate(result)

        # Persist
        if self._session:
            self._session.queries.append(asdict(plan))
            self._session.executions.append({
                "query":   result.query,
                "answer":  result.answer,
                "latency": result.latency_s,
                "chunks":  result.retrieved_chunks,
                "tokens":  result.token_count,
                "timestamp": result.timestamp,
            })
            self._session.validations.append(asdict(report))
            self.store.save_session(self._session)

        self.store.append_history({
            "query":       query,
            "intent":      plan.intent,
            "answer":      result.answer,
            "latency_s":   result.latency_s,
            "faithfulness": report.faithfulness_score,
            "relevance":   report.relevance_score,
            "passed":      report.passed,
            "timestamp":   result.timestamp,
        })

        return plan, result, report
