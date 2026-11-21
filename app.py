from pathlib import Path
import os
import sys
import json
import tempfile
import zipfile

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "problem1_promos"))
sys.path.insert(0, str(ROOT / "problem2_legal"))
sys.path.insert(0, str(ROOT / "problem3_continuity"))

from promo_finder import run as run_promos
from llm_ranker import evaluate_top_candidates
from legal_assistant import respond
from continuity_checker import run as run_qc


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def safe_extract_zip(uploaded_file, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(uploaded_file) as z:
        for member in z.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError("ZIP contains an unsafe file path.")
        z.extractall(destination)
    return destination


def show_df(rows):
    """Full-width table that works on older and newer Streamlit versions."""
    try:
        st.dataframe(rows, width="stretch", hide_index=True)
    except TypeError:
        st.dataframe(rows, use_container_width=True, hide_index=True)


def bullets(items):
    for item in items:
        st.markdown(f"- {item}")


def section_intro(title, text):
    st.markdown(
        f"<div class='section-intro'><h2>{title}</h2><p>{text}</p></div>",
        unsafe_allow_html=True,
    )


def note(text, kind="info"):
    st.markdown(f"<div class='note note-{kind}'>{text}</div>", unsafe_allow_html=True)


def has_bundled_pack():
    pack = ROOT / "input_pack"
    return pack.exists() and any(pack.rglob("*.txt"))


# Streamlit only reads .streamlit/config.toml from the folder it is launched in.
# Create the light theme file there if it is missing (applies after a restart).
_THEME = """[theme]
base = "light"
primaryColor = "#D6336C"
backgroundColor = "#F4F6FB"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#1D1B3B"
font = "sans serif"
"""
try:
    _cfg = Path.cwd() / ".streamlit" / "config.toml"
    if not _cfg.exists():
        _cfg.parent.mkdir(exist_ok=True)
        _cfg.write_text(_THEME, encoding="utf-8")
except Exception:
    pass


# ──────────────────────────────────────────────────────────────
# Page setup and styling
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kuku AI Generalist Lab",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=DM+Sans:wght@400;500;600&display=swap');

:root {
  --ink: #1D1B3B;
  --ink-soft: #5B5A78;
  --paper: #F4F6FB;
  --card: #FFFFFF;
  --line: #E1E4F0;
  --rose: #D6336C;
  --rose-soft: #FCE7EF;
  --teal: #0F8B8D;
  --teal-soft: #DDF3F3;
  --amber-soft: #FFF3D6;
}

html, body, .stApp, [class*="css"] { font-family: 'DM Sans', system-ui, sans-serif; }
.stApp { background: var(--paper); color: var(--ink); }
h1, h2, h3, h4 { font-family: 'Bricolage Grotesque', 'DM Sans', sans-serif; color: var(--ink); letter-spacing: -0.01em; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 4.2rem; padding-bottom: 3rem; max-width: 1180px; }

/* Hero with film-strip edges */
.hero {
  position: relative;
  background: var(--ink);
  color: #fff;
  border-radius: 18px;
  padding: 2.2rem 3rem 2rem 3rem;
  margin-bottom: 1.4rem;
  overflow: hidden;
}
.hero::before, .hero::after {
  content: "";
  position: absolute; top: 0; bottom: 0; width: 22px;
  background-image: radial-gradient(circle at center, var(--paper) 4px, transparent 5px);
  background-size: 22px 26px;
  background-repeat: repeat-y;
  background-position: center 8px;
}
.hero::before { left: 0; }
.hero::after { right: 0; }
.hero h1 { color: #fff; font-size: 2.5rem; font-weight: 800; margin: 0 0 .4rem 0; padding: 0; }
.hero p { color: #D9D8F0; font-size: 1.05rem; max-width: 640px; margin: 0 0 1.1rem 0; line-height: 1.55; }
.chip {
  display: inline-block; margin: 0 .5rem .3rem 0; padding: .28rem .8rem;
  border-radius: 999px; font-size: .85rem; font-weight: 500;
  background: rgba(255,255,255,.12); color: #fff; border: 1px solid rgba(255,255,255,.22);
}

/* Section intro */
.section-intro h2 { font-size: 1.55rem; font-weight: 700; margin: .4rem 0 .2rem 0; padding: 0; }
.section-intro p { color: var(--ink-soft); font-size: 1rem; margin: 0 0 1rem 0; max-width: 760px; line-height: 1.55; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: .4rem; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  height: 3rem; padding: 0 1.2rem; border-radius: 10px 10px 0 0;
  font-weight: 600; color: var(--ink-soft);
}
.stTabs [aria-selected="true"] { color: var(--rose) !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--rose) !important; }

/* Bordered containers become cards */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card); border-radius: 14px; border-color: var(--line) !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
  border-radius: 10px; font-weight: 600; padding: .55rem 1.1rem;
  border: 1px solid var(--line); background: #fff; color: var(--ink);
  transition: border-color .15s, background .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--rose); color: var(--rose); }
.stButton > button[kind="primary"] { background: var(--rose); border-color: var(--rose); color: #fff; }
.stButton > button[kind="primary"]:hover { background: #B92A5C; border-color: #B92A5C; color: #fff; }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible { outline: 3px solid var(--teal); outline-offset: 2px; }

/* Metrics */
[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: .9rem 1.1rem;
}
[data-testid="stMetricLabel"] { color: var(--ink-soft); }
[data-testid="stMetricValue"] { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; }

/* Inputs */
.stTextArea textarea, .stTextInput input { border-radius: 10px; }
[data-testid="stFileUploader"] section { border-radius: 12px; border: 1.5px dashed #B9BEDC; background: #FAFBFF; }

/* Expanders */
[data-testid="stExpander"] { border-radius: 12px; border: 1px solid var(--line); background: var(--card); }

/* Notes */
.note { border-radius: 12px; padding: .8rem 1.1rem; font-size: .95rem; line-height: 1.5; margin: .6rem 0; }
.note-info { background: var(--teal-soft); color: #0B5E60; }
.note-warn { background: var(--amber-soft); color: #7A5A00; }
.note-human { background: var(--rose-soft); color: #8E1F48; }

/* Sidebar */
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--line); }
.status-row { display: flex; justify-content: space-between; align-items: center; padding: .35rem 0; font-size: .92rem; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: .45rem; }
.dot-on { background: var(--teal); }
.dot-off { background: #C9CBD9; }

@media (max-width: 720px) {
  .hero { padding: 1.6rem 2.2rem; }
  .hero h1 { font-size: 1.9rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }

/* ── Force the light palette even when the browser/Streamlit is in dark mode ── */
html { color-scheme: light; }
header[data-testid="stHeader"] { background: var(--paper) !important; }
header[data-testid="stHeader"] * { color: var(--ink-soft) !important; }

.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li,
.stApp label, .stApp label p,
.stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stMetricValue"],
.stApp [data-testid="stExpander"] summary,
.stApp [data-testid="stExpander"] summary p,
.stApp [data-testid="stToggle"] p { color: var(--ink) !important; }
.stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stCaptionContainer"] p,
.stApp [data-testid="stMetricLabel"],
.stApp [data-testid="stMetricLabel"] p { color: var(--ink-soft) !important; }

/* Sidebar */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background: #FFFFFF !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] li, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] .status-row { color: var(--ink) !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: var(--ink-soft) !important; }
[data-testid="stSidebar"] hr { border-color: var(--line) !important; }

[data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--paper) !important; }
[data-testid="stSidebar"] * { color: var(--ink) !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: var(--ink-soft) !important; }
[data-testid="stSidebar"] .dot-on { background: var(--teal) !important; }
[data-testid="stSidebar"] .dot-off { background: #C9CBD9 !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { background: transparent !important; }
[data-testid="stToolbar"] button, [data-testid="stToolbar"] span { color: var(--ink-soft) !important; }

/* Hero stays light-on-dark */
.stApp .hero h1 { color: #fff !important; }
.stApp .hero p { color: #D9D8F0 !important; }
.stApp .hero .chip { color: #fff !important; }

/* Notes */
.stApp .note, .stApp .note b { color: inherit !important; }
.stApp .note-info { color: #0B5E60 !important; }
.stApp .note-warn { color: #7A5A00 !important; }
.stApp .note-human { color: #8E1F48 !important; }

/* Tabs */
.stApp .stTabs [data-baseweb="tab"] p { color: var(--ink-soft) !important; }
.stApp .stTabs [aria-selected="true"] p { color: var(--rose) !important; }

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid var(--line) !important; background: var(--card) !important; }
[data-testid="stExpander"] { background: var(--card) !important; border: 1px solid var(--line) !important; }

/* Buttons */
.stApp .stButton button, .stApp .stDownloadButton button { background: #fff; border: 1px solid var(--line); }
.stApp .stButton button p, .stApp .stDownloadButton button p { color: var(--ink) !important; }
.stApp .stButton button:hover p, .stApp .stDownloadButton button:hover p { color: var(--rose) !important; }
.stApp .stButton button[kind="primary"],
.stApp .stButton button[data-testid="stBaseButton-primary"] { background: var(--rose) !important; border-color: var(--rose) !important; }
.stApp .stButton button[kind="primary"] p,
.stApp .stButton button[data-testid="stBaseButton-primary"] p,
.stApp .stDownloadButton button[data-testid="stBaseButton-primary"] p { color: #fff !important; }
.stApp .stDownloadButton button[data-testid="stBaseButton-primary"] { background: var(--rose) !important; border-color: var(--rose) !important; }
.stApp .stButton button:disabled { opacity: .5; }

/* File uploader */
[data-testid="stFileUploader"] section { background: #FAFBFF !important; }
[data-testid="stFileUploader"] section span,
[data-testid="stFileUploader"] section small,
[data-testid="stFileUploader"] section p { color: var(--ink-soft) !important; }
[data-testid="stFileUploader"] button { background: #fff !important; border: 1px solid var(--line) !important; }
[data-testid="stFileUploader"] button, [data-testid="stFileUploader"] button p,
[data-testid="stFileUploader"] button span { color: var(--ink) !important; }
[data-testid="stFileUploaderFile"] * { color: var(--ink) !important; }

/* Text inputs */
.stApp [data-baseweb="textarea"], .stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"] { background: #fff !important; }
.stApp .stTextArea textarea, .stApp .stTextInput input {
  background: #fff !important; color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important;
  border: 1px solid var(--line);
}
.stApp .stTextArea textarea::placeholder { color: #8B8AA6 !important; -webkit-text-fill-color: #8B8AA6 !important; }
.stApp [data-testid="stAlert"] p { color: inherit !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────
api_key_present = bool(os.getenv("OPENAI_API_KEY"))
pack_present = has_bundled_pack()

with st.sidebar:
    st.markdown("### 🎬 Kuku Lab")
    st.caption("Three small prototypes. You review, the tools assist.")
    st.divider()
    st.markdown("**Setup status**")
    st.markdown(
        f"<div class='status-row'><span><span class='dot {'dot-on' if pack_present else 'dot-off'}'></span>"
        f"Bundled 50-episode pack</span><span>{'Found' if pack_present else 'Not found'}</span></div>"
        f"<div class='status-row'><span><span class='dot {'dot-on' if api_key_present else 'dot-off'}'></span>"
        f"OpenAI key</span><span>{'Found' if api_key_present else 'Missing'}</span></div>",
        unsafe_allow_html=True,
    )
    if not api_key_present:
        st.caption("Add OPENAI_API_KEY to a local .env file and restart to enable the LLM upgrade in Promo Finder.")
    st.divider()
    st.markdown("**How to use**")
    st.markdown(
        "1. Pick a tab.\n"
        "2. Upload a ZIP or describe your situation.\n"
        "3. Review the results.\n"
        "4. Download what you need."
    )
    st.divider()
    st.caption("Everything here works without paid APIs, except the optional LLM evaluation.")

# ──────────────────────────────────────────────────────────────
# Hero
# ──────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <h1>Kuku AI Generalist Lab</h1>
  <p>Find promo-worthy moments in screenplays, prepare a rental deposit refund request,
  and catch timing and continuity slips. Every result is a draft for a person to review.</p>
  <span class="chip">🎬 Promo Finder</span>
  <span class="chip">🏠 Rental Legal Helper</span>
  <span class="chip">🧾 Script Continuity QA</span>
</div>
""",
    unsafe_allow_html=True,
)

t1, t2, t3 = st.tabs(["🎬  Promo Finder", "🏠  Rental Legal Helper", "🧾  Continuity QA"])

# ══════════════════════════════════════════════════════════════
# TAB 1 · PROMO FINDER
# ══════════════════════════════════════════════════════════════
with t1:
    section_intro(
        "Find promotional moments",
        "Upload a ZIP of timestamped .txt screenplays. The tool ranks 20–60 second windows "
        "that could work as promos, and an editor makes the final call.",
    )

    with st.container(border=True):
        st.markdown("#### Step 1 · Choose your scripts")
        left, right = st.columns(2, gap="large")

        with left:
            st.markdown("**Upload a screenplay ZIP**")
            uploaded = st.file_uploader(
                "Screenplay ZIP", type=["zip"], key="p1zip", label_visibility="collapsed"
            )
            if st.button(
                "Run on uploaded ZIP",
                key="p1upload",
                type="primary",
                disabled=uploaded is None,
                use_container_width=True,
            ):
                try:
                    with st.spinner("Reading scripts and ranking windows…"):
                        inp = safe_extract_zip(uploaded, Path(tempfile.mkdtemp()) / "scripts")
                        st.session_state.pop("p1llm_report", None)
                        out = ROOT / "outputs" / "problem1_uploaded"
                        run_promos(inp, out)
                        st.session_state["p1out"] = out
                except Exception as e:
                    st.error(f"Could not process the ZIP: {e}")

        with right:
            st.markdown("**Or use the included pack**")
            if pack_present:
                st.caption("Runs the heuristic across all 50 bundled episodes.")
                if st.button("Run on 50-episode pack", key="p1", use_container_width=True):
                    with st.spinner("Ranking windows across the pack…"):
                        st.session_state.pop("p1llm_report", None)
                        out = ROOT / "outputs" / "problem1"
                        run_promos(ROOT / "input_pack", out)
                        st.session_state["p1out"] = out
            else:
                st.caption("No bundled input_pack folder found in this project. Upload a ZIP instead.")

    if "p1out" in st.session_state:
        p = st.session_state["p1out"]
        data = json.loads((p / "promo_candidates.json").read_text())

        st.markdown("")
        with st.container(border=True):
            st.markdown("#### Step 2 · Baseline results")
            st.caption("Ranked by the Python heuristic. Showing the top 15.")
            if not data:
                st.warning("No candidate windows were found. Check that your ZIP contains timestamped .txt files.")
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Candidate windows", len(data))
                m2.metric("Episodes covered", len({r["episode"] for r in data}))
                m3.metric("Top heuristic score", data[0]["score"] if "score" in data[0] else "–")

                show_df(
                    [
                        {
                            k: r[k]
                            for k in [
                                "overall_rank", "episode", "start", "end",
                                "duration_seconds", "score", "hook", "cliffhanger",
                            ]
                        }
                        for r in data[:15]
                    ]
                )

            d1, d2, d3 = st.columns(3)
            for col, f in zip(
                (d1, d2, d3),
                ["promo_candidates.csv", "promo_candidates.json", "promo_run_audit.json"],
            ):
                with col:
                    st.download_button(
                        "Download " + f,
                        (p / f).read_bytes(),
                        file_name=f,
                        key="base_" + f,
                        use_container_width=True,
                    )

        st.markdown("")
        with st.container(border=True):
            st.markdown("#### Step 3 · Optional upgrade: LLM review of the top 10")
            st.caption(
                "Only the 10 highest-ranked windows are sent to OpenAI. The heuristic score is kept. "
                "Hybrid score = 40% heuristic + 60% LLM. Failed evaluations fall back to the heuristic "
                "score and are marked. Results are cached locally to avoid repeat charges."
            )
            if not api_key_present:
                note(
                    "OpenAI key not found. Add <b>OPENAI_API_KEY</b> to a local .env file, then restart the app.",
                    "warn",
                )

            if st.button(
                "Evaluate top 10 with OpenAI",
                key="p1_llm",
                type="primary",
                disabled=not api_key_present,
            ):
                try:
                    with st.spinner("Evaluating the top 10 candidates with OpenAI…"):
                        report = evaluate_top_candidates(
                            data,
                            p,
                            top_n=10,
                            model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
                            run_budget_usd=float(os.getenv("OPENAI_RUN_BUDGET_USD", "0.25")),
                        )
                    st.session_state["p1llm_report"] = report
                except Exception as e:
                    st.error(f"OpenAI evaluation could not complete: {e}")

            report = st.session_state.get("p1llm_report")
            if report and Path(p / "promo_llm_comparison.csv").exists():
                st.success("LLM evaluation finished. The heuristic baseline is unchanged.")
                comparison = report["results"]
                ok = len([r for r in comparison if r.get("llm_score") is not None])

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("LLM calls", report["evaluated_candidates"])
                c2.metric("Cache hits", report["cache_hits"])
                c3.metric("Succeeded / failed", f"{ok} / {report['failed_candidates']}")
                c4.metric("Estimated cost", f"${report['actual_usage_cost_usd']:.5f}")

                st.markdown("**Heuristic vs LLM vs hybrid ranking**")
                show_df(
                    [
                        {
                            "Hybrid rank": r.get("hybrid_rank"),
                            "Heuristic rank": r.get("heuristic_rank"),
                            "LLM rank": r.get("llm_rank"),
                            "Episode": r.get("episode"),
                            "Start": r.get("start"),
                            "End": r.get("end"),
                            "Heuristic": r.get("score"),
                            "LLM": r.get("llm_score"),
                            "Hybrid": r.get("hybrid_score"),
                            "Fallback heuristic": r.get("fallback_heuristic_score"),
                            "Recommendation": r.get("llm_recommendation", r.get("recommendation")),
                            "Status": r.get("llm_status"),
                        }
                        for r in comparison
                    ]
                )

                st.markdown("**Why did the LLM score each candidate this way?**")
                for r in comparison:
                    label = f"{r.get('episode')} · {r.get('start')}–{r.get('end')} · Hybrid {r.get('hybrid_score')}"
                    with st.expander(label):
                        st.write(r.get("llm_why_it_works", r.get("llm_error", "No LLM explanation available.")))
                        st.markdown(f"**Hook:** {r.get('llm_hook_explanation', 'Not evaluated')}")
                        st.markdown(f"**Cliffhanger:** {r.get('llm_cliffhanger_explanation', 'Not evaluated')}")
                        if r.get("llm_error"):
                            st.error("Evaluation error: " + str(r["llm_error"]))
                        if r.get("llm_weaknesses"):
                            st.markdown("**Review points:** " + "; ".join(r["llm_weaknesses"]))

                e1, e2 = st.columns(2)
                with e1:
                    st.download_button(
                        "Download comparison CSV",
                        (p / "promo_llm_comparison.csv").read_bytes(),
                        file_name="promo_llm_comparison.csv",
                        key="llm_csv",
                        use_container_width=True,
                    )
                with e2:
                    st.download_button(
                        "Download LLM report JSON",
                        (p / "promo_llm_comparison.json").read_bytes(),
                        file_name="promo_llm_comparison.json",
                        key="llm_json",
                        use_container_width=True,
                    )

    note(
        "<b>Human review needed.</b> Heuristics are fast and repeatable but rely on text patterns. "
        "The LLM adds narrative interpretation, but neither can judge acting, visuals or real clip performance.",
        "human",
    )

# ══════════════════════════════════════════════════════════════
# TAB 2 · RENTAL LEGAL HELPER
# ══════════════════════════════════════════════════════════════
with t2:
    section_intro(
        "Security-deposit refund helper",
        "For tenants in India. Describe what happened and get an organised summary, a list of "
        "evidence to collect, and a polite refund request you can edit. This is not legal advice.",
    )

    with st.container(border=True):
        st.markdown("#### Tell us what happened")
        story = st.text_area(
            "Your situation",
            height=190,
            placeholder=(
                "Example: I rented a flat in Pune from March 2024. I paid a deposit of ₹60,000. "
                "I moved out on 30 June 2025 and the landlord has not returned it…"
            ),
            help="Include dates, the deposit amount, agreement terms and how the landlord has responded.",
        )
        st.caption("Tip: the more specific you are about dates and amounts, the better the draft.")

        c1, c2 = st.columns(2)
        with c1:
            tenant = st.text_input("Your name", value="[Tenant name]")
        with c2:
            landlord = st.text_input("Landlord's name", value="[Landlord name]")

        if st.button("Analyse my situation and draft a request", key="p2", type="primary"):
            if not story.strip():
                st.warning("Describe your situation first.")
            else:
                with st.spinner("Organising your facts and drafting…"):
                    st.session_state["legal_result"] = respond(story)

    if "legal_result" in st.session_state:
        r = st.session_state["legal_result"]
        st.markdown("")
        if r.get("disclaimer"):
            note(r["disclaimer"], "warn")

        if "case_summary" in r:
            summary = r["case_summary"]
            tab_a, tab_b, tab_c = st.tabs(["📋  Case summary", "✉️  Draft request", "🧭  Next steps"])

            with tab_a:
                st.markdown("**In plain language**")
                st.write(r["plain_language"])
                st.markdown("")

                m1, m2 = st.columns(2, gap="large")
                with m1:
                    with st.container(border=True):
                        st.markdown("**Issues**")
                        bullets(summary.get("issue", []) or ["Not stated"])
                        st.markdown("**Amount mentioned**")
                        st.write(summary.get("amount_mentioned", "Not stated"))
                with m2:
                    with st.container(border=True):
                        st.markdown("**Dates mentioned**")
                        dates = summary.get("dates_mentioned", [])
                        st.write(", ".join(dates) if dates else "Not stated")
                        st.markdown("**Evidence to collect**")
                        bullets(summary.get("evidence_to_collect", []) or ["None listed"])

                missing = summary.get("missing_or_unconfirmed", [])
                if missing:
                    with st.container(border=True):
                        st.markdown("**Facts or evidence still to confirm**")
                        bullets(missing)

                questions = summary.get("questions_to_resolve", [])
                if questions:
                    with st.expander("Questions that may need clarification"):
                        bullets(questions)

                with st.expander("Original facts you supplied"):
                    st.write(summary.get("facts_as_provided", ""))

            with tab_b:
                draft = r["draft"].replace("[Tenant name]", tenant).replace("[Landlord name]", landlord)
                st.caption("Check every fact before sending. Edit the text below as needed.")
                edited = st.text_area(
                    "Draft for review",
                    draft,
                    height=320,
                    label_visibility="collapsed",
                )
                st.download_button(
                    "Download draft (.txt)",
                    edited,
                    file_name="rental_deposit_request_draft.txt",
                    type="primary",
                )

            with tab_c:
                st.markdown("**Suggested next steps**")
                steps = r["next_steps"]
                for i, step in enumerate(steps, 1):
                    st.markdown(f"{i}. {step}")
                st.caption(r["legal_citations"])
        else:
            st.write(r)

# ══════════════════════════════════════════════════════════════
# TAB 3 · CONTINUITY QA
# ══════════════════════════════════════════════════════════════
with t3:
    section_intro(
        "Timestamp and continuity checks",
        "Checks scene time ordering, missing timestamps, timing outside the episode envelope, "
        "and continuity-note terms that deserve a second look.",
    )

    with st.container(border=True):
        st.markdown("#### Choose your scripts")
        left, right = st.columns(2, gap="large")

        with left:
            st.markdown("**Upload a screenplay ZIP**")
            qc_upload = st.file_uploader(
                "Screenplay ZIP for QC", type=["zip"], key="p3zip", label_visibility="collapsed"
            )
            if st.button(
                "Run QC on uploaded ZIP",
                key="p3upload",
                type="primary",
                disabled=qc_upload is None,
                use_container_width=True,
            ):
                try:
                    with st.spinner("Checking timestamps and continuity…"):
                        qc_input = safe_extract_zip(qc_upload, Path(tempfile.mkdtemp()) / "scripts")
                        qc_out = ROOT / "outputs" / "problem3_uploaded"
                        run_qc(qc_input, qc_out)
                        qc_rows = json.loads((qc_out / "continuity_qc.json").read_text(encoding="utf-8"))
                    if not qc_rows:
                        st.error("No .txt screenplay files were found in this ZIP. Check the archive contents.")
                        st.session_state.pop("p3out", None)
                    else:
                        st.session_state["p3out"] = qc_out
                except Exception as e:
                    st.error(f"Could not run continuity QC: {e}")

        with right:
            st.markdown("**Or use the included pack**")
            if pack_present:
                st.caption("Runs QC across all 50 bundled episodes.")
                if st.button("Run QC on 50-episode pack", key="p3", use_container_width=True):
                    with st.spinner("Checking the full pack…"):
                        out = ROOT / "outputs" / "problem3"
                        run_qc(ROOT / "input_pack", out)
                        st.session_state["p3out"] = out
            else:
                st.caption("No bundled input_pack folder found in this project. Upload a ZIP instead.")

    if "p3out" in st.session_state:
        p = st.session_state["p3out"]
        rows = json.loads((p / "continuity_qc.json").read_text(encoding="utf-8"))
        st.markdown("")
        with st.container(border=True):
            st.markdown("#### Results")
            if not rows:
                st.error("QC produced zero episode rows, so this is not reported as a successful run.")
            else:
                flagged = sum(bool(x["issues"]) for x in rows)
                c1, c2, c3 = st.columns(3)
                c1.metric("Episodes checked", len(rows))
                c2.metric("With timestamp flags", flagged)
                c3.metric("Clean episodes", len(rows) - flagged)

                only_flagged = st.toggle("Show only episodes with timestamp flags", value=False)
                view = [x for x in rows if x["issues"]] if only_flagged else rows
                show_df(
                    [
                        {
                            "Episode": x["episode"],
                            "Scenes": x["scene_count"],
                            "Runtime (sec)": x["runtime_seconds"],
                            "QC score": x["qc_score"],
                            "Issues": "; ".join(x["issues"]),
                            "Continuity review": "; ".join(x.get("continuity_review_flags", [])),
                        }
                        for x in view
                    ]
                )

                d1, d2 = st.columns(2)
                for col, f in zip((d1, d2), ["continuity_qc.csv", "continuity_qc.json"]):
                    with col:
                        st.download_button(
                            "Download " + f,
                            (p / f).read_bytes(),
                            file_name=f,
                            key="p3_" + f,
                            use_container_width=True,
                        )

    note(
        "<b>Review prompts, not verdicts.</b> A missing character or prop mention is not automatically "
        "a continuity error.",
        "human",
    )

st.markdown("")
st.caption("Built with Python and Streamlit. The model integration is swappable, and the baseline works without paid APIs. · UI v3")