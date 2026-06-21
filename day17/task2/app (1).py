"""
VoiceEmo — Emotion Detection from Voice
Researcher-Supervisor-Writer pattern | Groq + Tavily | LangGraph
"""

import os
import operator
import tempfile
import time
import re
from typing import Annotated, List, Literal

import streamlit as st
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VoiceEmo | Emotion Detection",
    page_icon="🎙️",
    layout="wide",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.block-container { padding: 1.8rem 2rem 3rem; }
div[data-testid="stTabs"] button { font-weight: 600; }
.emotion-chip {
    display: inline-block; padding: 4px 14px; border-radius: 20px;
    font-weight: 600; font-size: 0.85rem; margin: 3px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎙️ VoiceEmo")
    st.caption("Emotion Detection · Researcher-Supervisor-Writer")
    st.divider()

    st.subheader("🔑 API Keys")
    groq_key   = st.text_input("Groq API Key",   type="password", value=os.getenv("GROQ_API_KEY", ""))
    tavily_key = st.text_input("Tavily API Key", type="password", value=os.getenv("TAVILY_API_KEY", ""))

    st.divider()
    st.subheader("⚙️ Settings")
    groq_model    = st.selectbox("Groq LLM", ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"])
    tavily_k      = st.slider("Tavily results", 1, 5, 3)
    show_raw      = st.toggle("Show raw research notes", value=False)

    st.divider()
    st.caption("Pattern: Supervisor routes → Researcher searches Tavily → Writer uses Groq LLM → Supervisor routes to FINISH")

# ─────────────────────────────────────────────────────────────────────────────
# State + Schema  (exact same structure as original notebook)
# ─────────────────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    task:              str
    transcript:        str
    research_notes:    Annotated[List[str], operator.add]
    draft:             str
    next_node:         str
    retry_count:       int
    revision_feedback: str
    emotions_detected: List[str]

class Router(BaseModel):
    """Decide which worker to call next."""
    next_worker:  Literal["researcher", "writer", "FINISH"] = Field(description="The next node to act")
    instructions: str  = Field(description="Specific instructions for the worker")
    is_critical:  bool = Field(description="If True, system will pause for human review")

# ─────────────────────────────────────────────────────────────────────────────
# Graph builder — cached per key+model so it's not rebuilt on every run
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def build_emotion_graph(groq_key: str, tavily_key: str, model: str, k: int):
    llm         = ChatGroq(model=model, temperature=0, api_key=groq_key)
    search_tool = TavilySearchResults(k=k, tavily_api_key=tavily_key)

    # ── Researcher node ──────────────────────────────────────────────────
    def researcher(state: AgentState):
        query   = f"speech emotion recognition acoustic features: {state['task'][:180]}"
        results = search_tool.invoke(query)
        notes   = []
        for r in (results if isinstance(results, list) else []):
            if isinstance(r, dict):
                notes.append(f"[{r.get('url','')}]\n{r.get('content','')[:500]}")
        return {"research_notes": notes, "retry_count": 0}

    # ── Writer node ──────────────────────────────────────────────────────
    def writer(state: AgentState):
        context    = "\n\n".join(state["research_notes"][:4])
        transcript = state["transcript"]
        prompt = f"""You are an expert in Speech Emotion Recognition (SER).

Transcript of the speaker:
\"{transcript}\"

Research context (acoustic + psychological findings):
{context}

Produce a detailed emotion analysis with EXACTLY these sections:

## 1. Primary Emotion
Name the dominant emotion and confidence level (High / Medium / Low).

## 2. Secondary Emotions
List up to 3 secondary emotions present.

## 3. Linguistic Cues
Specific words or phrases from the transcript that reveal emotion.

## 4. Acoustic Indicators
Describe expected vocal features: pitch, pace, pauses, energy level.

## 5. Psychological Interpretation
Brief empathetic explanation of the speaker's inner state.

## 6. Recommended Response
How a conversational AI or human should respond to this emotional state.

Be evidence-based and reference the transcript directly."""
        res = llm.invoke(prompt)

        # extract emotion words for badge display
        all_emotions = [
            "joy","sadness","anger","fear","disgust","surprise","neutral",
            "happiness","anxiety","excitement","frustration","calm","boredom","contempt"
        ]
        found = re.findall("|".join(all_emotions), res.content, re.IGNORECASE)
        unique = list(dict.fromkeys(e.capitalize() for e in found))[:6]

        return {"draft": res.content, "emotions_detected": unique}

    # ── Supervisor node ──────────────────────────────────────────────────
    def supervisor(state: AgentState):
        has_notes = len(state.get("research_notes", [])) > 0
        has_draft = bool(state.get("draft", "").strip())
        if has_draft:
            return {"next_node": "FINISH",     "revision_feedback": "Analysis complete."}
        elif has_notes:
            return {"next_node": "writer",     "revision_feedback": "Research gathered. Generate emotion analysis report."}
        else:
            return {"next_node": "researcher", "revision_feedback": "No research yet. Search for emotion context."}

    # ── Build graph (same structure as notebook) ─────────────────────────
    builder = StateGraph(AgentState)
    builder.add_node("supervisor",  supervisor)
    builder.add_node("researcher",  researcher)
    builder.add_node("writer",      writer)
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda x: x["next_node"],
        {"researcher": "researcher", "writer": "writer", "FINISH": END}
    )
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer",     "supervisor")

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)   # interrupt_before removed for live UX

# ─────────────────────────────────────────────────────────────────────────────
# Groq Whisper transcription
# ─────────────────────────────────────────────────────────────────────────────
def transcribe(audio_bytes: bytes, groq_key: str) -> str:
    client = Groq(api_key=groq_key)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    try:
        with open(tmp, "rb") as af:
            result = client.audio.transcriptions.create(
                model="whisper-large-v3", file=af, response_format="text")
        return result if isinstance(result, str) else result.text
    finally:
        os.unlink(tmp)

# ─────────────────────────────────────────────────────────────────────────────
# Emotion → colour mapping
# ─────────────────────────────────────────────────────────────────────────────
EMOTION_COLORS = {
    "Joy":         ("#fbbf24", "#1a1200"),
    "Happiness":   ("#fbbf24", "#1a1200"),
    "Excitement":  ("#f97316", "#180a00"),
    "Sadness":     ("#60a5fa", "#001220"),
    "Fear":        ("#818cf8", "#0a0820"),
    "Anxiety":     ("#a78bfa", "#0d0820"),
    "Anger":       ("#f87171", "#1a0000"),
    "Frustration": ("#fb923c", "#180800"),
    "Disgust":     ("#4ade80", "#001a08"),
    "Surprise":    ("#34d399", "#001a10"),
    "Neutral":     ("#94a3b8", "#111827"),
    "Calm":        ("#6ee7b7", "#001a10"),
    "Boredom":     ("#94a3b8", "#111827"),
    "Contempt":    ("#f472b6", "#1a0012"),
}

def emotion_chip(emotion: str) -> str:
    fg, bg = EMOTION_COLORS.get(emotion, ("#6366f1", "#0d0f2a"))
    return (f'<span class="emotion-chip" '
            f'style="background:{bg};color:{fg};border:1.5px solid {fg}66">'
            f'{emotion}</span>')

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_diagram, tab_detect, tab_arch = st.tabs([
    "📐 LangGraph Diagram",
    "🎤 Emotion Detection",
    "🏗️ Architecture",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DIAGRAM (rendered from matplotlib/IPython)
# ══════════════════════════════════════════════════════════════════════════════
with tab_diagram:
    st.subheader("LangGraph Architecture — Researcher · Supervisor · Writer")
    st.caption("Diagram generated with matplotlib from the IPython notebook structure.")

    diagram_path = os.path.join(os.path.dirname(__file__), "langgraph_diagram.png")
    if os.path.exists(diagram_path):
        st.image(diagram_path, use_container_width=True)
    else:
        st.warning("Diagram image not found. Run `generate_diagram.py` first.")

    st.divider()

    # Explain each node inline
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 🧠 Supervisor")
        st.markdown("""
- Entry point of the graph
- Uses `with_structured_output(Router)` to decide next step
- **Conditional edges** → researcher / writer / FINISH
- Reads `research_notes` count + `draft` presence to decide
        """)
    with col2:
        st.markdown("#### 🔍 Researcher")
        st.markdown("""
- Calls **Tavily search** with the task query
- Appends results to `research_notes` using `operator.add`
- Unconditional edge back to Supervisor
- `retry_count` reset to 0
        """)
    with col3:
        st.markdown("#### ✍️ Writer")
        st.markdown("""
- Reads `research_notes` + `task`
- Calls **LLM** to synthesise a structured report
- Stores result in `draft`
- Unconditional edge back to Supervisor
- `interrupt_before=["writer"]` in original notebook
        """)

    st.divider()
    with st.expander("🗂️ AgentState schema"):
        st.code("""
class AgentState(TypedDict):
    task:              str                              # research query
    research_notes:    Annotated[List[str], operator.add]  # Tavily results (appended)
    draft:             str                              # final output
    next_node:         str                              # router decision
    retry_count:       int                              # loop guard
    revision_feedback: str                              # supervisor instructions
        """, language="python")

    with st.expander("🗂️ Router schema (Pydantic)"):
        st.code("""
class Router(BaseModel):
    next_worker:  Literal["researcher", "writer", "FINISH"]
    instructions: str
    is_critical:  bool   # True → pause for human review (breakpoint)
        """, language="python")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — EMOTION DETECTION
# ══════════════════════════════════════════════════════════════════════════════
with tab_detect:
    st.subheader("Emotion Detection from Voice")
    st.caption(
        "Speak or paste text → Groq Whisper transcribes → "
        "Researcher searches Tavily → Writer (Groq LLM) analyses emotions."
    )

    if not groq_key or not tavily_key:
        st.warning("Enter your **Groq** and **Tavily** API keys in the sidebar to proceed.")
        st.stop()

    # ── Input ──────────────────────────────────────────────────────────
    input_col, result_col = st.columns([1, 1.4], gap="large")

    with input_col:
        st.markdown("#### Input")
        mode = st.radio("Mode", ["Upload audio file", "Type / paste text"], horizontal=True)

        transcript_text = ""

        if mode == "Upload audio file":
            uploaded = st.file_uploader(
                "Upload a WAV / MP3 / M4A / OGG file",
                type=["wav","mp3","m4a","ogg","webm"],
            )
            if uploaded:
                st.audio(uploaded)
                if st.button("Transcribe with Groq Whisper", type="secondary"):
                    with st.spinner("Transcribing…"):
                        try:
                            transcript_text = transcribe(uploaded.read(), groq_key)
                            st.session_state["transcript"] = transcript_text
                            st.success("Transcribed!")
                        except Exception as e:
                            st.error(f"Transcription error: {e}")
            # show stored transcript
            if "transcript" in st.session_state and st.session_state["transcript"]:
                transcript_text = st.session_state["transcript"]
        else:
            transcript_text = st.text_area(
                "Enter speech text:",
                placeholder="e.g. I can't believe they did this again. I'm exhausted and fed up.",
                height=130,
                label_visibility="collapsed",
            )

        if transcript_text:
            st.markdown("**Transcript:**")
            st.info(f'"{transcript_text}"')

        run_btn = st.button(
            "Analyse Emotions",
            type="primary",
            use_container_width=True,
            disabled=not transcript_text,
        )

    # ── Output ────────────────────────────────────────────────────────
    with result_col:
        if run_btn and transcript_text:
            progress_bar = st.progress(0, text="Starting agent graph…")
            status_box   = st.empty()

            step_pct = {"researcher": 40, "writer": 75, "FINISH": 100}
            step_msg = {
                "researcher": "Researcher searching Tavily…",
                "writer":     "Writer generating emotion analysis…",
                "FINISH":     "Complete!",
            }

            final_state = None
            try:
                graph = build_emotion_graph(groq_key, tavily_key, groq_model, tavily_k)
                config = {"configurable": {"thread_id": f"emotion_{int(time.time())}"}}
                initial = {
                    "task":              transcript_text,
                    "transcript":        transcript_text,
                    "research_notes":    [],
                    "draft":             "",
                    "next_node":         "",
                    "retry_count":       0,
                    "revision_feedback": "",
                    "emotions_detected": [],
                }

                for event in graph.stream(initial, config, stream_mode="values"):
                    node = event.get("next_node", "")
                    if node in step_pct:
                        progress_bar.progress(step_pct[node], text=step_msg[node])
                        status_box.caption(f"→ {step_msg[node]}")
                    final_state = event

                progress_bar.empty()
                status_box.empty()

                if final_state and final_state.get("draft"):
                    # emotion chips
                    emotions = final_state.get("emotions_detected", [])
                    if emotions:
                        st.markdown("**Detected Emotions:**")
                        chips = "".join(emotion_chip(e) for e in emotions)
                        st.markdown(chips, unsafe_allow_html=True)
                        st.write("")

                    # main report
                    st.markdown("**Analysis Report:**")
                    st.markdown(final_state["draft"])

                    # raw notes
                    if show_raw and final_state.get("research_notes"):
                        with st.expander("Raw research notes from Tavily"):
                            for i, note in enumerate(final_state["research_notes"], 1):
                                st.markdown(f"**Note {i}:**")
                                st.code(note, language="text")

            except Exception as e:
                progress_bar.empty()
                st.error(f"Graph error: {e}")
                import traceback; st.code(traceback.format_exc())

        elif not run_btn:
            st.markdown(
                "<div style='text-align:center;padding:4rem 1rem;color:#475569'>"
                "<div style='font-size:3rem;margin-bottom:1rem'>🎭</div>"
                "<div>Upload audio or type text, then click<br>"
                "<strong>Analyse Emotions</strong></div></div>",
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ARCHITECTURE EXPLANATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_arch:
    st.subheader("How the Researcher-Writer Pattern Maps to Emotion Detection")

    st.markdown("""
| Step | Original Notebook | This App |
|------|------------------|----------|
| **Input** | Research topic string | Voice file → Groq Whisper → transcript |
| **Supervisor** | Structured LLM routes to researcher/writer/FINISH | Same — checks `research_notes` and `draft` in state |
| **Researcher** | Tavily search on topic | Tavily searches `"speech emotion recognition acoustic features: [transcript]"` |
| **Writer** | LLM writes a topic report | Groq `llama-3.3-70b-versatile` generates 6-section emotion analysis |
| **State merge** | `operator.add` on `research_notes` | Identical — safe concurrent append |
| **Persistence** | `MemorySaver` checkpointer | Same — per thread_id |
| **Breakpoint** | `interrupt_before=["writer"]` | Removed for live UX; can be re-enabled |
    """)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Graph execution flow")
        st.markdown("""
1. **START → Supervisor** — entry point, state has no notes/draft
2. **Supervisor → Researcher** — `next_node = 'researcher'`
3. **Researcher** — runs Tavily, appends to `research_notes`
4. **Researcher → Supervisor** — unconditional edge
5. **Supervisor → Writer** — notes exist, no draft yet
6. **Writer** — calls Groq LLM, stores emotion report in `draft`
7. **Writer → Supervisor** — unconditional edge
8. **Supervisor → FINISH** — draft is populated → END
        """)

    with col_b:
        st.markdown("#### Tech stack")
        st.markdown("""
| Component | Tool |
|-----------|------|
| Speech-to-Text | Groq `whisper-large-v3` |
| LLM (Writer + Supervisor) | Groq `llama-3.3-70b-versatile` |
| Web Research | Tavily Search API |
| Agent Orchestration | LangGraph `StateGraph` |
| State Persistence | LangGraph `MemorySaver` |
| Diagram | Python `matplotlib` (IPython-style) |
| Frontend | Streamlit |
        """)

    st.divider()
    st.markdown("#### Full graph code")
    st.code("""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

builder = StateGraph(AgentState)
builder.add_node("supervisor",  supervisor)
builder.add_node("researcher",  researcher)
builder.add_node("writer",      writer)
builder.set_entry_point("supervisor")

builder.add_conditional_edges(
    "supervisor",
    lambda x: x["next_node"],
    {"researcher": "researcher", "writer": "writer", "FINISH": END}
)
builder.add_edge("researcher", "supervisor")
builder.add_edge("writer",     "supervisor")

memory = MemorySaver()
graph  = builder.compile(
    checkpointer=memory,
    interrupt_before=["writer"]   # pause for human review
)
    """, language="python")
