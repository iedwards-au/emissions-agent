"""
Scope3 Inventory Agent — Streamlit Web App
Run locally:  streamlit run app.py
"""

import io
import json
import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Scope3 Inventory Agent",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Scope3 brand CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

  /* Global */
  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0C0E12;
    color: #FAFFF0;
  }

  /* Hide Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }

  /* Main container */
  .block-container {
    padding-top: 2rem;
    max-width: 900px;
  }

  /* Logo / header */
  .s3-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 0.25rem;
  }
  .s3-logo {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.05rem;
    font-weight: 600;
    color: #DBFC01;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .s3-tagline {
    font-size: 0.78rem;
    color: #888;
    font-weight: 300;
  }
  h1 {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 2rem !important;
    font-weight: 600 !important;
    color: #FAFFF0 !important;
    margin-top: 0.25rem !important;
    line-height: 1.2 !important;
  }
  .accent { color: #DBFC01; }

  /* Divider */
  .s3-divider {
    border: none;
    border-top: 1px solid #DBFC01;
    margin: 1rem 0 1.5rem 0;
    opacity: 0.4;
  }

  /* Mode pills */
  .stRadio > div {
    flex-direction: row !important;
    gap: 12px;
  }
  .stRadio label {
    background: #1A1D22 !important;
    border: 1px solid #2E3138 !important;
    border-radius: 6px !important;
    padding: 8px 20px !important;
    cursor: pointer !important;
    font-size: 0.88rem !important;
    color: #FAFFF0 !important;
    transition: all 0.15s !important;
  }
  .stRadio label:hover {
    border-color: #DBFC01 !important;
    color: #DBFC01 !important;
  }

  /* Text areas + inputs */
  .stTextArea textarea, .stTextInput input {
    background: #1A1D22 !important;
    border: 1px solid #2E3138 !important;
    border-radius: 6px !important;
    color: #FAFFF0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem !important;
  }
  .stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #DBFC01 !important;
    box-shadow: 0 0 0 1px #DBFC01 !important;
  }

  /* Primary button */
  .stButton > button {
    background: #DBFC01 !important;
    color: #0C0E12 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 10px 28px !important;
    cursor: pointer !important;
    transition: opacity 0.15s !important;
  }
  .stButton > button:hover { opacity: 0.85 !important; }

  /* Download button */
  .stDownloadButton > button {
    background: transparent !important;
    color: #DBFC01 !important;
    border: 1px solid #DBFC01 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem !important;
    border-radius: 6px !important;
  }

  /* Tool call log */
  .tool-log {
    background: #111318;
    border-left: 2px solid #DBFC01;
    border-radius: 0 6px 6px 0;
    padding: 10px 14px;
    margin: 4px 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #82E500;
  }
  .tool-icon { margin-right: 6px; }

  /* Response box */
  .response-box {
    background: #13161B;
    border: 1px solid #2E3138;
    border-radius: 8px;
    padding: 20px 24px;
    font-size: 0.9rem;
    line-height: 1.65;
    color: #FAFFF0;
    margin-top: 1rem;
  }

  /* Info/warning pills */
  .stInfo, .stWarning, .stSuccess, .stError {
    border-radius: 6px !important;
  }

  /* Selectbox */
  .stSelectbox > div > div {
    background: #1A1D22 !important;
    border-color: #2E3138 !important;
    color: #FAFFF0 !important;
  }

  /* Labels */
  .stTextArea label, .stTextInput label, .stSelectbox label, .stRadio label span {
    color: #FAFFF0 !important;
    font-size: 0.85rem !important;
  }

  /* Expander */
  .streamlit-expanderHeader {
    background: #1A1D22 !important;
    border-radius: 6px !important;
    color: #888 !important;
    font-size: 0.8rem !important;
  }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="s3-header">
  <span class="s3-logo">⬡ Scope3</span>
  <span class="s3-tagline">Inventory Carbon Intelligence</span>
</div>
""", unsafe_allow_html=True)

st.markdown("# Inventory <span class='accent'>Agent</span>", unsafe_allow_html=True)
st.markdown('<hr class="s3-divider">', unsafe_allow_html=True)


# ── Lazy imports (so app loads even if deps missing) ──────────────────────────
def _import_agent():
    try:
        from agent import run_agent, check_brief_clarity
        return run_agent, check_brief_clarity
    except ImportError as e:
        st.error(f"Could not import agent: {e}. Make sure all dependencies are installed.")
        st.stop()


# ── Mode selector ─────────────────────────────────────────────────────────────
mode = st.radio(
    "Select mode",
    ["🔍  ANALYSE — score my inventory list", "🧭  DISCOVER — find inventory for a brief"],
    label_visibility="collapsed"
)
is_analyse = mode.startswith("🔍")

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ── Input area ────────────────────────────────────────────────────────────────
if is_analyse:
    st.markdown("**Paste your inventory list** — one domain or app bundle ID per line")
    raw_input = st.text_area(
        "inventory",
        placeholder="nytimes.com\nspotify.com\ncom.espn.android\ncnn.com\nweather.com",
        height=180,
        label_visibility="collapsed"
    )
    country = st.text_input("Country (ISO code)", value="US", max_chars=2).upper()

    # Build the agent message from the list
    def build_message():
        lines = [l.strip() for l in raw_input.strip().splitlines() if l.strip()]
        if not lines:
            return None
        items = "\n".join(f"- {l}" for l in lines)
        return f"Please analyse and score this inventory list for carbon emissions (country: {country}):\n\n{items}"

else:
    st.markdown("**Describe your campaign brief**")
    raw_input = st.text_area(
        "brief",
        placeholder="e.g. We're running a sustainability-focused campaign for a car brand targeting 25-45 year olds in Australia. We want premium lifestyle and news inventory, web and app only.",
        height=130,
        label_visibility="collapsed"
    )

    def build_message():
        if not raw_input.strip():
            return None
        return raw_input.strip()


# ── Session state for conversation history ────────────────────────────────────
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "last_pdf_bytes" not in st.session_state:
    st.session_state.last_pdf_bytes = None
if "last_pdf_name" not in st.session_state:
    st.session_state.last_pdf_name = None


# ── Run button ────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
with col1:
    run_clicked = st.button("▶  Run Agent")
with col2:
    if st.button("↺  Reset conversation"):
        st.session_state.conversation = []
        st.session_state.last_pdf_bytes = None
        st.rerun()

if run_clicked:
    message = build_message()
    if not message:
        st.warning("Please enter some inventory or a brief first.")
    else:
        run_agent, check_brief_clarity = _import_agent()

        # Brief clarification check for discover mode
        if not is_analyse:
            clarification = check_brief_clarity(raw_input)
            if clarification:
                st.info(f"💬 **Clarification needed:** {clarification}")
                st.stop()

        # Tool call display container
        tool_container = st.container()
        status_placeholder = st.empty()

        with st.spinner("Agent thinking..."):
            # Monkey-patch to capture tool calls live
            tool_calls_display = []

            import agent as agent_module
            original_execute = None

            try:
                from tools import execute_tool as _orig_execute
                original_execute = _orig_execute

                def traced_execute(tool_name, tool_input):
                    tool_calls_display.append(tool_name)
                    with tool_container:
                        st.markdown(
                            f'<div class="tool-log"><span class="tool-icon">⚙</span> Calling <b>{tool_name}</b>…</div>',
                            unsafe_allow_html=True
                        )
                    return _orig_execute(tool_name, tool_input)

                import tools
                tools.execute_tool = traced_execute
                agent_module.execute_tool = traced_execute

            except Exception:
                pass

            result = run_agent(message, st.session_state.conversation)
            st.session_state.conversation = result["conversation"]

            # Restore original
            if original_execute:
                try:
                    tools.execute_tool = original_execute
                    agent_module.execute_tool = original_execute
                except Exception:
                    pass

        status_placeholder.empty()

        # ── Response ──────────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            f'<div class="response-box">{result["response"].replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True
        )

        # ── PDF generation ────────────────────────────────────────────────────
        tool_calls_log = result.get("tool_calls", [])
        _try_generate_pdf(result, tool_calls_log, is_analyse)


# ── PDF helper (defined before use via Python hoisting of defs) ───────────────
def _try_generate_pdf(result, tool_calls_log, is_analyse):
    """Attempt to generate and offer PDF download from tool call results."""
    try:
        from pdf_report import generate_pdf
        import tempfile, os

        ranked = []
        unmodelled = []
        recommendations = []
        brief_text = None

        # Fish results out of the conversation history
        for entry in st.session_state.conversation:
            if isinstance(entry.get("content"), list):
                for block in entry["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        try:
                            data = json.loads(block["content"])
                            if "ranked_inventory" in data:
                                ranked = data["ranked_inventory"]
                                unmodelled = data.get("unmodelled_inventory", [])
                            # match_brief returns a list directly
                            if isinstance(data, list) and data and "reason" in data[0]:
                                recommendations = data
                        except Exception:
                            pass

        for call in tool_calls_log:
            if call["tool"] == "match_brief_to_inventory":
                brief_text = call["input"].get("brief")

        if not ranked:
            return  # Nothing to report

        mode_str = "analyse" if is_analyse else "discover"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        generate_pdf(
            mode=mode_str,
            ranked_inventory=ranked,
            unmodelled_inventory=unmodelled,
            recommendations=recommendations if not is_analyse else None,
            brief=brief_text,
            output_path=tmp_path
        )

        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
        os.unlink(tmp_path)

        st.session_state.last_pdf_bytes = pdf_bytes
        st.session_state.last_pdf_name = f"scope3_report.pdf"

    except Exception as e:
        st.caption(f"PDF generation skipped: {e}")


# ── PDF download button (persists between reruns) ─────────────────────────────
if st.session_state.last_pdf_bytes:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.download_button(
        label="⬇  Download PDF Report",
        data=st.session_state.last_pdf_bytes,
        file_name=st.session_state.last_pdf_name,
        mime="application/pdf"
    )

# ── Conversation history expander ─────────────────────────────────────────────
if st.session_state.conversation:
    with st.expander(f"📜 Conversation history ({len(st.session_state.conversation)} messages)"):
        for msg in st.session_state.conversation:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                st.markdown(f"**{role.upper()}:** {content[:300]}{'…' if len(content) > 300 else ''}")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        st.markdown(f"**{role.upper()}:** {text[:300]}{'…' if len(text) > 300 else ''}")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-top:3rem; padding-top:1rem; border-top:1px solid #1E2128; text-align:center; color:#444; font-size:0.72rem; font-family:"IBM Plex Mono", monospace;'>
  SCOPE3 INVENTORY AGENT &nbsp;·&nbsp; Powered by Scope3 Emissions Data &nbsp;·&nbsp; scope3.com
</div>
""", unsafe_allow_html=True)
