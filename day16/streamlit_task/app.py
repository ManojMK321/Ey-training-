"""
FinSight AI — Financial RAG System
Streamlit UI · Planner → Executor → Validator
"""

import os
import time
import uuid
import streamlit as st
from datetime import datetime
from pathlib import Path

from rag_engine import (
    PKLStore, RAGOrchestrator, RAGSession,
    Plan, ExecutionResult, ValidationReport
)

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FinSight AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Global */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1117 0%, #1a1d2e 100%);
    border-right: 1px solid #2d3148;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stTextInput label { color: #94a3b8 !important; font-size: 0.78rem; }

/* Header */
.finsight-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
    border: 1px solid #1e40af44;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.finsight-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4);
}
.finsight-header h1 { color: #f8fafc; font-size: 2rem; font-weight: 700; margin: 0; }
.finsight-header p  { color: #94a3b8; margin: 6px 0 0; font-size: 0.95rem; }

/* Architecture pipeline */
.pipeline-card {
    display: flex; align-items: center; gap: 0;
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 14px 20px; margin-bottom: 20px;
}
.pipe-step {
    flex: 1; text-align: center; padding: 10px 8px;
    background: #1e293b; border-radius: 8px; margin: 0 4px;
}
.pipe-step.active { background: #1d4ed8; border: 1px solid #3b82f6; }
.pipe-step.done   { background: #064e3b; border: 1px solid #10b981; }
.pipe-step.error  { background: #7f1d1d; border: 1px solid #ef4444; }
.pipe-step h4 { color: #f8fafc; margin: 0; font-size: 0.85rem; font-weight: 600; }
.pipe-step p  { color: #94a3b8; margin: 2px 0 0; font-size: 0.72rem; }
.pipe-arrow   { color: #475569; font-size: 1.2rem; padding: 0 4px; flex-shrink: 0; }

/* Cards */
.metric-card {
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 12px; padding: 18px 20px; text-align: center;
}
.metric-card h3 { color: #94a3b8; font-size: 0.78rem; font-weight: 500;
                  text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 8px; }
.metric-card .value { color: #f8fafc; font-size: 1.8rem; font-weight: 700; }
.metric-card .unit  { color: #64748b; font-size: 0.75rem; }

/* Intent badge */
.intent-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
}
.intent-revenue    { background: #1d4ed822; color: #60a5fa; border: 1px solid #1d4ed8; }
.intent-risk       { background: #7f1d1d22; color: #f87171; border: 1px solid #7f1d1d; }
.intent-liquidity  { background: #065f4622; color: #34d399; border: 1px solid #065f46; }
.intent-comparative{ background: #4c1d9522; color: #c084fc; border: 1px solid #4c1d95; }
.intent-trend      { background: #78350f22; color: #fbbf24; border: 1px solid #78350f; }
.intent-factual    { background: #1e293b;   color: #94a3b8; border: 1px solid #334155; }

/* Answer box */
.answer-box {
    background: #0f172a; border: 1px solid #1e3a5f;
    border-left: 4px solid #3b82f6;
    border-radius: 0 12px 12px 0; padding: 20px 24px;
    color: #e2e8f0; line-height: 1.7; font-size: 0.95rem;
    margin: 12px 0;
}

/* Validation bar */
.val-bar-wrap { background: #1e293b; border-radius: 20px; height: 8px; overflow: hidden; }
.val-bar      { height: 8px; border-radius: 20px;
                background: linear-gradient(90deg, #3b82f6, #10b981); }

/* Source chip */
.source-chip {
    display: inline-block; padding: 4px 10px; margin: 3px;
    background: #1e293b; border: 1px solid #334155;
    border-radius: 6px; font-size: 0.73rem; color: #94a3b8;
}

/* History table */
.history-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; background: #0f172a;
    border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 6px;
}
.history-row:hover { border-color: #334155; }

/* Scrollable chunk list */
.chunk-scroll { max-height: 260px; overflow-y: auto;
                border: 1px solid #1e293b; border-radius: 8px; padding: 8px; }
.chunk-item { background: #1e293b; border-radius: 6px; padding: 10px 12px;
              margin-bottom: 6px; font-size: 0.8rem; color: #cbd5e1; }
.chunk-item .chunk-src { color: #3b82f6; font-weight: 600; font-size: 0.72rem; }

/* Status pills */
.pill-pass { background: #064e3b; color: #34d399; padding: 2px 10px;
             border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.pill-fail { background: #7f1d1d; color: #f87171; padding: 2px 10px;
             border-radius: 20px; font-size: 0.75rem; font-weight: 600; }

/* Warning box */
.warning-item {
    background: #78350f22; border: 1px solid #78350f;
    border-radius: 6px; padding: 8px 12px; margin: 4px 0;
    color: #fbbf24; font-size: 0.82rem;
}

/* Streamlit overrides */
.stButton>button {
    background: linear-gradient(135deg, #1d4ed8, #7c3aed);
    color: white; border: none; border-radius: 8px;
    font-weight: 600; padding: 10px 24px;
    transition: opacity .2s;
}
.stButton>button:hover { opacity: .88; color: white; }
div[data-testid="stTextInput"] input {
    background: #0f172a; color: #f8fafc;
    border: 1px solid #334155; border-radius: 8px;
}
div[data-testid="stTextInput"] input:focus { border-color: #3b82f6; box-shadow: none; }
.stTabs [data-baseweb="tab"] { color: #64748b; }
.stTabs [aria-selected="true"] { color: #3b82f6 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

SAMPLE_DOCS = [
    {
        "source": "Apple_10K_2023_Risk",
        "text": """RISK FACTORS
Apple's operations and financial results are subject to various risks and uncertainties.
Global and regional economic conditions, including conditions resulting from financial and credit market fluctuations,
can adversely affect demand for Apple's products and services.
Apple faces intense competition in all of its business areas from well-established companies with significant
resources, as well as from new market entrants.
The Company's fiscal year 2023 revenue was $383.3 billion, compared to $394.3 billion in fiscal 2022,
a decrease of approximately 2.8 percent.
The Company's net income for fiscal 2023 was $97.0 billion, or $6.13 diluted earnings per share,
compared to $99.8 billion, or $6.11 diluted earnings per share, in fiscal 2022.
Apple's gross margin percentage was 44.1% in fiscal 2023, compared to 43.3% in fiscal 2022.
Services revenue reached an all-time high of $85.2 billion in fiscal 2023, up 9 percent year over year."""
    },
    {
        "source": "Apple_10K_2023_Products",
        "text": """PRODUCTS AND SERVICES
Apple designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories.
iPhone is Apple's line of smartphones based on its iOS operating system.
iPhone net sales were $200.6 billion in fiscal 2023, representing approximately 52% of total revenue.
Mac net sales were $29.4 billion in fiscal 2023, down from $40.2 billion in fiscal 2022.
iPad net sales were $28.3 billion in fiscal 2023.
Wearables, Home and Accessories net sales were $39.8 billion in fiscal 2023.
Apple's Services segment includes advertising, AppleCare, cloud, digital content, payment and other services.
The App Store, Apple Music, Apple TV+, Apple Arcade, iCloud and Apple Pay are key Services offerings.
The Company had approximately 2.2 billion active devices at the end of fiscal year 2023."""
    },
    {
        "source": "Apple_10K_2023_Liquidity",
        "text": """LIQUIDITY AND CAPITAL RESOURCES
The Company believes its existing balances of cash, cash equivalents and unrestricted marketable securities,
together with cash generated by operations, will be sufficient to satisfy its expected cash needs.
Cash and cash equivalents as of September 30, 2023 were $29.965 billion.
Total marketable securities were $100.544 billion, consisting of current marketable securities of $31.590 billion
and non-current marketable securities of $100.544 billion.
During fiscal 2023, the Company returned over $77 billion to shareholders,
including $15.1 billion in dividends and dividend equivalents and $62.2 billion through repurchases of 471 million shares.
Capital expenditures were $10.959 billion in fiscal 2023.
The Company's long-term debt as of September 30, 2023 was $95.281 billion."""
    },
]

SAMPLE_QUERIES = [
    "What was Apple's total revenue in fiscal year 2023?",
    "How much cash did Apple have at the end of fiscal 2023?",
    "What percentage of Apple's revenue came from iPhone in 2023?",
    "How much did Apple return to shareholders in fiscal 2023?",
    "What is Apple's gross margin for fiscal 2023?",
    "What risks does Apple face in its business?",
    "Compare iPhone vs Mac revenue for fiscal 2023",
]


@st.cache_resource
def get_store():
    return PKLStore("./rag_store")


def get_or_create_session_id():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    return st.session_state.session_id


def score_color(score: float) -> str:
    if score >= 0.7:
        return "#10b981"
    elif score >= 0.4:
        return "#f59e0b"
    return "#ef4444"


def render_pipeline_status(stage: str):
    """stage: idle | planning | executing | validating | done | error"""
    stages = [
        ("🗺️", "Planner",  "Intent & strategy"),
        ("⚡", "Executor", "Retrieve & generate"),
        ("✅", "Validator","Quality check"),
    ]
    s_map = {"idle": -1, "planning": 0, "executing": 1, "validating": 2, "done": 3, "error": -2}
    active = s_map.get(stage, -1)

    html = '<div class="pipeline-card">'
    for i, (icon, name, desc) in enumerate(stages):
        css = "done" if i < active else ("active" if i == active else "")
        if stage == "error" and i == active:
            css = "error"
        html += f'<div class="pipe-step {css}"><h4>{icon} {name}</h4><p>{desc}</p></div>'
        if i < 2:
            html += '<span class="pipe-arrow">→</span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_intent_badge(intent: str):
    return f'<span class="intent-badge intent-{intent}">{intent}</span>'


def render_score_bar(label: str, score: float):
    color = score_color(score)
    pct = int(score * 100)
    st.markdown(f"""
    <div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="color:#94a3b8;font-size:0.8rem">{label}</span>
        <span style="color:{color};font-weight:600;font-size:0.8rem">{pct}%</span>
      </div>
      <div class="val-bar-wrap">
        <div class="val-bar" style="width:{pct}%;background:{color}"></div>
      </div>
    </div>""", unsafe_allow_html=True)


# ─── Index Builder ────────────────────────────────────────────────────────────

def build_index(store: PKLStore, config: dict):
    """Build FAISS index from sample docs and persist to PKL."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS

    chunk_size    = config.get("chunk_size", 512)
    chunk_overlap = config.get("chunk_overlap", 64)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    lc_docs = [Document(page_content=d["text"], metadata={"source": d["source"]})
               for d in SAMPLE_DOCS]
    chunks = splitter.split_documents(lc_docs)

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = FAISS.from_documents(chunks, embedding_model)

    metadata = {
        "chunk_size":    chunk_size,
        "chunk_overlap": chunk_overlap,
        "n_chunks":      len(chunks),
        "n_vectors":     vectorstore.index.ntotal,
        "dimension":     vectorstore.index.d,
        "sources":       [d["source"] for d in SAMPLE_DOCS],
        "built_at":      datetime.now().isoformat(),
    }
    store.save_index(vectorstore, chunks, metadata)
    store.save_config(config)
    return vectorstore, chunks, embedding_model, metadata


@st.cache_resource
def load_embedding_model():
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_llm(config: dict):
    provider = config.get("llm_provider", "azure")
    if provider == "azure":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=config["azure_endpoint"],
            azure_deployment=config["azure_deployment"],
            openai_api_version=config.get("azure_api_version", "2024-06-01"),
            openai_api_key=config["azure_api_key"],
            temperature=0,
            max_tokens=512,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.get("openai_model", "gpt-4o"),
            api_key=config["openai_api_key"],
            temperature=0,
            max_tokens=512,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar(store: PKLStore) -> dict:
    with st.sidebar:
        st.markdown("## 📈 FinSight AI")
        st.markdown("<hr style='border-color:#2d3148'>", unsafe_allow_html=True)

        # LLM config
        st.markdown("### 🔑 LLM Configuration")
        provider = st.selectbox("Provider", ["Azure OpenAI", "OpenAI"], key="provider")

        config = {}
        if provider == "Azure OpenAI":
            config["llm_provider"]      = "azure"
            config["azure_endpoint"]    = st.text_input("Azure Endpoint", type="password",
                                                         placeholder="https://…openai.azure.com/")
            config["azure_api_key"]     = st.text_input("Azure API Key", type="password")
            config["azure_deployment"]  = st.text_input("Deployment Name", value="gpt-4o")
            config["azure_api_version"] = "2024-06-01"
        else:
            config["llm_provider"]   = "openai"
            config["openai_api_key"] = st.text_input("OpenAI API Key", type="password")
            config["openai_model"]   = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])

        st.markdown("<hr style='border-color:#2d3148'>", unsafe_allow_html=True)
        st.markdown("### ⚙️ Retrieval Settings")

        config["chunk_size"]          = st.select_slider("Chunk Size", [256, 512, 1024], value=512)
        config["chunk_overlap"]       = st.slider("Chunk Overlap", 32, 128, 64, 16)
        config["retrieval_k"]         = st.slider("Top-K Chunks", 2, 8, 4)
        config["retrieval_strategy"]  = st.radio("Strategy", ["dense", "hybrid"], horizontal=True)

        st.markdown("<hr style='border-color:#2d3148'>", unsafe_allow_html=True)

        # Build / load index
        index_exists = store.index_exists()
        idx_label = "🔄 Rebuild Index" if index_exists else "🏗️ Build Index"

        if st.button(idx_label, use_container_width=True):
            with st.spinner("Building FAISS index…"):
                try:
                    vs, chunks, em, meta = build_index(store, config)
                    st.session_state["vectorstore"]     = vs
                    st.session_state["chunks"]          = chunks
                    st.session_state["embedding_model"] = em
                    st.session_state["index_meta"]      = meta
                    st.success(f"✅ Index built — {meta['n_vectors']} vectors")
                except Exception as e:
                    st.error(f"Build failed: {e}")

        # Stats
        if index_exists:
            _, _, meta = store.load_index()
            if meta:
                st.markdown(f"""
                <div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:10px 12px;margin-top:8px">
                  <div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.05em">Index Info</div>
                  <div style="color:#e2e8f0;font-size:0.8rem;margin-top:4px">
                    {meta.get('n_vectors','?')} vectors · {meta.get('dimension','?')}D<br>
                    Chunks: {meta.get('n_chunks','?')} · Size: {meta.get('chunk_size','?')}<br>
                    Built: {meta.get('built_at','?')[:10]}
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#2d3148'>", unsafe_allow_html=True)

        # PKL store stats
        st.markdown("### 💾 PKL Store")
        stats = store.store_stats()
        for k, v in stats.items():
            st.markdown(f"<div style='color:#94a3b8;font-size:0.78rem'>{k}: <b style='color:#e2e8f0'>{v}</b></div>",
                        unsafe_allow_html=True)

        if st.button("🗑️ Clear History", use_container_width=True):
            store.clear_history()
            st.success("History cleared")

    return config


# ─── Main UI ──────────────────────────────────────────────────────────────────

def main():
    store      = get_store()
    config     = render_sidebar(store)
    session_id = get_or_create_session_id()

    # Header
    st.markdown("""
    <div class="finsight-header">
      <h1>📈 FinSight AI — Financial RAG System</h1>
      <p>Planner → Executor → Validator · Powered by FAISS · Persistent via PKL</p>
    </div>""", unsafe_allow_html=True)

    # Tabs
    tab_query, tab_history, tab_session, tab_docs = st.tabs([
        "🔍 Query",  "📋 History",  "🗂️ Session",  "📄 Documents"
    ])

    # ── TAB: QUERY ────────────────────────────────────────────────────────────
    with tab_query:
        # Pipeline status
        pipeline_stage = st.session_state.get("pipeline_stage", "idle")
        render_pipeline_status(pipeline_stage)

        # Query input
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            query = st.text_input(
                "Analyst Question",
                placeholder="e.g. What was Apple's gross margin in fiscal 2023?",
                label_visibility="collapsed",
                key="query_input",
            )
        with col_btn:
            run_btn = st.button("▶ Run", use_container_width=True)

        # Sample query chips
        st.markdown("<div style='margin-bottom:16px'>", unsafe_allow_html=True)
        sample_cols = st.columns(len(SAMPLE_QUERIES))
        for i, sq in enumerate(SAMPLE_QUERIES):
            with sample_cols[i]:
                if st.button(sq[:30] + "…" if len(sq) > 30 else sq,
                             key=f"sq_{i}", use_container_width=True,
                             help=sq):
                    st.session_state["query_input"] = sq
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Run pipeline
        if run_btn and query:
            # Validate prerequisites
            api_ready = (
                (config.get("azure_api_key") and config.get("azure_endpoint")) or
                config.get("openai_api_key")
            )
            if not api_ready:
                st.error("🔑 Please enter your API credentials in the sidebar.")
                st.stop()

            # Load / build index
            if "vectorstore" not in st.session_state:
                if store.index_exists():
                    with st.spinner("Loading index from PKL…"):
                        vs, chunks, meta = store.load_index()
                        em = load_embedding_model()
                        st.session_state.update({
                            "vectorstore": vs,
                            "chunks": chunks,
                            "embedding_model": em,
                            "index_meta": meta,
                        })
                else:
                    with st.spinner("Building index (first run)…"):
                        vs, chunks, em, meta = build_index(store, config)
                        st.session_state.update({
                            "vectorstore": vs,
                            "chunks": chunks,
                            "embedding_model": em,
                            "index_meta": meta,
                        })

            try:
                llm = get_llm(config)
            except Exception as e:
                st.error(f"LLM init failed: {e}")
                st.stop()

            orchestrator = RAGOrchestrator(store)
            orchestrator.load_or_init_session(session_id)
            orchestrator.setup_executor(
                st.session_state["vectorstore"],
                st.session_state["embedding_model"],
                llm
            )

            # ── Step 1: Plan ──
            st.session_state["pipeline_stage"] = "planning"
            st.rerun()

        # Show pipeline running feedback (handled below after rerun triggers)
        stage = st.session_state.get("pipeline_stage", "idle")

        if stage == "planning" and query:
            from rag_engine import Planner
            planner = Planner()
            plan = planner.plan(query, config)
            st.session_state["current_plan"] = plan
            st.session_state["pipeline_stage"] = "executing"
            render_pipeline_status("planning")
            st.rerun()

        elif stage == "executing" and "current_plan" in st.session_state:
            render_pipeline_status("executing")
            plan = st.session_state["current_plan"]

            # Quick check — index loaded?
            if "vectorstore" not in st.session_state:
                st.session_state["pipeline_stage"] = "idle"
                st.rerun()

            try:
                api_ready = (
                    (config.get("azure_api_key") and config.get("azure_endpoint")) or
                    config.get("openai_api_key")
                )
                if not api_ready:
                    st.error("Missing API credentials")
                    st.session_state["pipeline_stage"] = "idle"
                    st.stop()

                llm = get_llm(config)
                from rag_engine import Executor, Validator
                executor  = Executor(st.session_state["vectorstore"],
                                     st.session_state["embedding_model"], llm)
                validator = Validator(llm)

                with st.spinner("⚡ Executing…"):
                    result = executor.execute(plan)
                st.session_state["current_result"] = result
                st.session_state["pipeline_stage"] = "validating"
                st.rerun()

            except Exception as e:
                st.error(f"Execution error: {e}")
                st.session_state["pipeline_stage"] = "idle"

        elif stage == "validating" and "current_result" in st.session_state:
            render_pipeline_status("validating")
            result = st.session_state["current_result"]
            plan   = st.session_state["current_plan"]

            try:
                api_ready = (
                    (config.get("azure_api_key") and config.get("azure_endpoint")) or
                    config.get("openai_api_key")
                )
                llm = get_llm(config) if api_ready else None
                from rag_engine import Validator
                validator = Validator(llm)
                report = validator.validate(result)

                # Persist
                orchestrator = RAGOrchestrator(store)
                orchestrator.load_or_init_session(session_id)
                orchestrator._session.queries.append(vars(plan))
                orchestrator._session.executions.append({
                    "query": result.query, "answer": result.answer,
                    "latency": result.latency_s, "chunks": result.retrieved_chunks,
                    "tokens": result.token_count, "timestamp": result.timestamp,
                })
                from dataclasses import asdict
                orchestrator._session.validations.append(asdict(report))
                store.save_session(orchestrator._session)
                store.append_history({
                    "query": query, "intent": plan.intent,
                    "answer": result.answer, "latency_s": result.latency_s,
                    "faithfulness": report.faithfulness_score,
                    "relevance": report.relevance_score,
                    "passed": report.passed, "timestamp": result.timestamp,
                })

                st.session_state["current_report"] = report
                st.session_state["pipeline_stage"]  = "done"
                st.rerun()

            except Exception as e:
                st.error(f"Validation error: {e}")
                st.session_state["pipeline_stage"] = "idle"

        elif stage == "done":
            render_pipeline_status("done")
            plan   = st.session_state.get("current_plan")
            result = st.session_state.get("current_result")
            report = st.session_state.get("current_report")

            if plan and result and report:
                _render_results(plan, result, report)

                if st.button("🔄 New Query"):
                    for k in ["pipeline_stage", "current_plan", "current_result", "current_report"]:
                        st.session_state.pop(k, None)
                    st.rerun()

    # ── TAB: HISTORY ──────────────────────────────────────────────────────────
    with tab_history:
        history = store.load_history()
        st.markdown(f"### Query History &nbsp; <span style='color:#64748b;font-size:0.85rem'>({len(history)} queries)</span>",
                    unsafe_allow_html=True)

        if not history:
            st.info("No queries yet. Run a query to see history.")
        else:
            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            avg_latency = sum(h["latency_s"] for h in history) / len(history)
            avg_faith   = sum(h.get("faithfulness", 0) for h in history) / len(history)
            pass_rate   = sum(1 for h in history if h.get("passed")) / len(history)

            for col, label, val, unit in [
                (c1, "Total Queries", len(history), ""),
                (c2, "Avg Latency",   f"{avg_latency:.2f}", "s"),
                (c3, "Avg Faithfulness", f"{avg_faith:.0%}", ""),
                (c4, "Pass Rate",     f"{pass_rate:.0%}", ""),
            ]:
                with col:
                    st.markdown(f"""<div class="metric-card">
                      <h3>{label}</h3>
                      <div class="value">{val}<span class="unit">{unit}</span></div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            for h in reversed(history[-20:]):
                intent_html = render_intent_badge(h.get("intent", "factual"))
                pass_html   = f'<span class="pill-pass">PASS</span>' if h.get("passed") else f'<span class="pill-fail">FAIL</span>'
                st.markdown(f"""
                <div class="history-row">
                  <div style="flex:1">
                    <div style="color:#e2e8f0;font-size:0.85rem;font-weight:500">{h['query'][:80]}</div>
                    <div style="color:#64748b;font-size:0.72rem;margin-top:3px">{h.get('timestamp','')[:19]}</div>
                  </div>
                  <div>{intent_html}</div>
                  <div style="color:#94a3b8;font-size:0.8rem;min-width:60px;text-align:right">{h.get('latency_s',0):.2f}s</div>
                  <div style="min-width:50px;text-align:right">{pass_html}</div>
                </div>""", unsafe_allow_html=True)

    # ── TAB: SESSION ──────────────────────────────────────────────────────────
    with tab_session:
        st.markdown(f"### Session: `{session_id}`")
        sessions = store.load_all_sessions()
        if not sessions:
            st.info("No sessions saved yet.")
        else:
            for sid, sess in sessions.items():
                with st.expander(f"📁 {sid} — {len(sess.get('queries', sess.queries if hasattr(sess,'queries') else []))} queries · {sess.created_at[:10]}"):
                    execs = sess.executions if hasattr(sess, "executions") else sess.get("executions", [])
                    vals  = sess.validations if hasattr(sess, "validations") else sess.get("validations", [])
                    st.markdown(f"**Executions:** {len(execs)} &nbsp; **Validations:** {len(vals)}")
                    if execs:
                        for ex in execs[-3:]:
                            st.markdown(f"- `{ex.get('query','')[:60]}` · {ex.get('latency',0):.2f}s")

    # ── TAB: DOCUMENTS ────────────────────────────────────────────────────────
    with tab_docs:
        st.markdown("### 📄 Loaded Documents")
        for doc in SAMPLE_DOCS:
            with st.expander(f"📑 {doc['source']}"):
                st.code(doc["text"], language="text")

        if "index_meta" in st.session_state:
            meta = st.session_state["index_meta"]
            st.markdown("### 📊 Index Statistics")
            col1, col2, col3 = st.columns(3)
            for col, label, val in [
                (col1, "Total Vectors",  meta.get("n_vectors", "?")),
                (col2, "Dimensions",     meta.get("dimension", "?")),
                (col3, "Total Chunks",   meta.get("n_chunks", "?")),
            ]:
                with col:
                    st.markdown(f"""<div class="metric-card">
                      <h3>{label}</h3>
                      <div class="value">{val}</div>
                    </div>""", unsafe_allow_html=True)


# ─── Results Renderer ─────────────────────────────────────────────────────────

def _render_results(plan: Plan, result: ExecutionResult, report: ValidationReport):
    # Top metrics row
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val, unit in [
        (c1, "Latency",      f"{result.latency_s:.2f}", "s"),
        (c2, "Chunks Used",  len(result.retrieved_chunks), ""),
        (c3, "Faithfulness", f"{report.faithfulness_score:.0%}", ""),
        (c4, "Relevance",    f"{report.relevance_score:.0%}", ""),
        (c5, "Tokens (est)", result.token_count, ""),
    ]:
        with col:
            st.markdown(f"""<div class="metric-card">
              <h3>{label}</h3>
              <div class="value">{val}<span class="unit"> {unit}</span></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Plan summary
        intent_html = render_intent_badge(plan.intent)
        st.markdown(f"""
        <div style="margin-bottom:12px">
          <span style="color:#64748b;font-size:0.78rem">INTENT</span>&nbsp;&nbsp;{intent_html}&nbsp;&nbsp;
          <span style="color:#64748b;font-size:0.78rem">K={plan.retrieval_k}</span>&nbsp;&nbsp;
          <span style="color:#64748b;font-size:0.78rem">CHUNK={plan.chunk_size}</span>&nbsp;&nbsp;
          <span style="color:#64748b;font-size:0.78rem">STRATEGY={plan.strategy}</span>
        </div>""", unsafe_allow_html=True)

        # Answer
        st.markdown("#### 💬 Answer")
        st.markdown(f'<div class="answer-box">{result.answer}</div>', unsafe_allow_html=True)

        # Retrieved sources
        st.markdown("#### 📎 Retrieved Sources")
        chips = "".join(f'<span class="source-chip">{c["source"]}</span>'
                        for c in result.retrieved_chunks)
        st.markdown(chips, unsafe_allow_html=True)

        # Chunks
        with st.expander("🔍 View Retrieved Chunks"):
            st.markdown('<div class="chunk-scroll">', unsafe_allow_html=True)
            for i, c in enumerate(result.retrieved_chunks):
                st.markdown(f"""<div class="chunk-item">
                  <div class="chunk-src">#{i+1} · {c['source']}</div>
                  <div style="margin-top:4px">{c['content'][:300]}{'…' if len(c['content'])>300 else ''}</div>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        # Validation panel
        pass_html = '<span class="pill-pass">✅ PASSED</span>' if report.passed else '<span class="pill-fail">❌ FAILED</span>'
        st.markdown(f"#### Validation Report &nbsp; {pass_html}", unsafe_allow_html=True)

        render_score_bar("Faithfulness",    report.faithfulness_score)
        render_score_bar("Relevance",       report.relevance_score)
        render_score_bar("Source Coverage", report.source_coverage)

        if report.warnings:
            st.markdown("**⚠️ Warnings**")
            for w in report.warnings:
                st.markdown(f'<div class="warning-item">⚠️ {w}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#064e3b22;border:1px solid #064e3b;border-radius:6px;padding:8px 12px;color:#34d399;font-size:0.82rem">✅ No warnings</div>',
                        unsafe_allow_html=True)

        # Plan details
        st.markdown("<br>**📋 Planner Output**")
        st.json({
            "intent":           plan.intent,
            "strategy":         plan.strategy,
            "retrieval_k":      plan.retrieval_k,
            "chunk_size":       plan.chunk_size,
            "required_sources": plan.required_sources,
        })


if __name__ == "__main__":
    main()
