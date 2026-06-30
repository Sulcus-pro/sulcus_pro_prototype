"""
Sulcus.pro — The Autonomous Corporate Nervous System
=====================================================

Single Streamlit entry point. All world state lives in a ``SulcusEngine`` stored
in ``st.session_state``; this layer only reads snapshots and calls ``advance()``.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from sulcus import SulcusEngine, TICK_TITLES, TOTAL_TICKS
from sulcus import generative_ui as ui

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="Sulcus.pro — Autonomous Corporate Nervous System",
    page_icon=str(ASSETS / "sulcus_logo_sm.png") if (ASSETS / "sulcus_logo_sm.png").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------- #
# Global styling
# --------------------------------------------------------------------------- #
st.markdown(
    f"""
    <style>
      .stApp {{ background: radial-gradient(1200px 600px at 50% -10%, #15182B 0%, {ui.INK} 55%); }}
      header[data-testid="stHeader"] {{ background: transparent; }}
      .block-container {{ padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px; }}
      div[data-testid="stMetric"] {{
          background:{ui.PANEL}; border:1px solid #262C40; border-radius:14px;
          padding:14px 16px;
      }}
      div[data-testid="stMetricLabel"] p {{ color:{ui.MUTED}; font-size:12px; letter-spacing:1px; }}
      .stButton>button {{
          border-radius:10px; border:1px solid #2E3550; background:{ui.PANEL_2};
          color:{ui.TEXT}; font-weight:600;
      }}
      .stButton>button:hover {{ border-color:{ui.VIOLET}; color:#fff; }}
      .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
      .stTabs [data-baseweb="tab"] {{
          background:{ui.PANEL}; border-radius:10px 10px 0 0; padding:8px 16px; color:{ui.MUTED};
      }}
      .stTabs [aria-selected="true"] {{ background:{ui.PANEL_2}; color:{ui.TEXT}; }}
      [data-testid="stChatInput"] textarea {{ background:{ui.PANEL}; color:{ui.TEXT}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# State + assets
# --------------------------------------------------------------------------- #
def _logo_b64() -> str:
    p = ASSETS / "sulcus_logo_sm.png"
    if not p.exists():
        p = ASSETS / "sulcus_logo.png"
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""


if "engine" not in st.session_state:
    st.session_state.engine = SulcusEngine()
if "chat" not in st.session_state:
    st.session_state.chat = []
if "logo" not in st.session_state:
    st.session_state.logo = _logo_b64()

engine: SulcusEngine = st.session_state.engine


def answer_query(q: str) -> str:
    """Lightweight grounded query portal over current engine state."""
    ql = q.lower()
    cal = engine.canvas.calendar
    status = cal.status if isinstance(cal.status, str) else cal.status.value
    if any(k in ql for k in ["when", "date", "launch", "friday", "tuesday"]):
        return (
            f"The current authoritative launch is **{cal.title}** on **{cal.human_date}** "
            f"({cal.iso_date}), status **{status}**, payment rail **{cal.payment_rail}**. "
            f"Grounded against {len(engine.stream.active_events())} active event(s)."
        )
    if any(k in ql for k in ["risk", "alert", "premortem", "pre-mortem", "campaign", "blind"]):
        if engine.canvas.alerts:
            a = engine.canvas.alerts[0]
            sev = a.severity if isinstance(a.severity, str) else a.severity.value
            return f"Top pre-mortem [{sev}]: {a.headline} — {a.detail}"
        return "No active pre-mortem alerts; feeds are mutually consistent."
    if any(k in ql for k in ["faith", "score", "drift", "trust", "eval"]):
        r = engine.report
        return (
            f"Gate 2 → Faithfulness **{r.faithfulness:.2f}**, Context Precision "
            f"**{r.context_precision:.2f}**, status **{r.eval_status}**. "
            f"Hallucination suppressed: {r.hallucination_suppressed}."
        )
    if any(k in ql for k in ["circadian", "sleep", "consolidat", "heal", "graph"]):
        return (
            f"The circadian loop runs at Tick 2. It tombstoned "
            f"{len(engine.stream.tombstones)} obsolete vector(s) and rewrote the graph "
            f"to settle on {cal.human_date}."
        )
    return (
        f"Sulcus is at Tick {engine.tick} — {TICK_TITLES.get(engine.tick)}. Ask about the "
        f"launch date, current risks, faithfulness scores, or the circadian loop."
    )


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown(ui.brand_header(st.session_state.logo), unsafe_allow_html=True)

prog = engine.tick / (TOTAL_TICKS - 1) if TOTAL_TICKS > 1 else 1.0
st.markdown(
    f"""<div style="display:flex;align-items:center;gap:14px;margin:-4px 0 16px 4px;">
      <div style="flex:1;height:6px;border-radius:999px;background:#0E1220;overflow:hidden;">
        <div style="height:100%;width:{prog*100:.0f}%;
             background:linear-gradient(90deg,{ui.VIOLET},{ui.VIOLET_SOFT});"></div></div>
      <div style="font-size:12px;color:{ui.MUTED};white-space:nowrap;">
        Tick {engine.tick}/{TOTAL_TICKS-1} · {TICK_TITLES.get(engine.tick)}</div>
    </div>""",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.2], gap="large")


# --------------------------------------------------------------------------- #
# LEFT — Control panel & data input
# --------------------------------------------------------------------------- #
with left:
    st.markdown(ui.section_label("Control Panel"), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button(
            "▶  Advance Simulation Storyline",
            use_container_width=True,
            type="primary",
            disabled=engine.is_final,
        ):
            msg = engine.advance()
            st.toast(msg)
            st.rerun()
    with c2:
        if st.button("↺ Reset", use_container_width=True):
            engine.reset()
            st.session_state.chat = []
            st.toast("Simulation reset to Tick 0.")
            st.rerun()

    if engine.is_final:
        st.caption("Storyline at final tick — reset to replay the corporate pivot.")

    st.markdown(ui.section_label("Raw Ephemeral Event Ticker"), unsafe_allow_html=True)
    records = engine.stream.as_records()
    df = pd.DataFrame(records, columns=["Time", "Source", "User", "Event Text"])
    st.dataframe(df, use_container_width=True, hide_index=True, height=260)
    st.caption(
        f"{len(engine.stream.events)} events · {len(engine.stream.active_events())} active · "
        f"{len(engine.stream.tombstones)} garbage-collected (GC)"
    )

    st.markdown(ui.section_label("Conversational Bar · query the brain"), unsafe_allow_html=True)
    for role, text in st.session_state.chat[-4:]:
        with st.chat_message(role):
            st.markdown(text)
    if prompt := st.chat_input("Ask Sulcus about the plan, risks, or memory…"):
        st.session_state.chat.append(("user", prompt))
        st.session_state.chat.append(("assistant", answer_query(prompt)))
        st.rerun()


# --------------------------------------------------------------------------- #
# RIGHT — Generative UI assets & vision canvas
# --------------------------------------------------------------------------- #
with right:
    tab_canvas, tab_cal = st.tabs(["Generative Canvas & History", "Evolving Calendar View"])

    # ---- Tab 1 ---------------------------------------------------------- #
    with tab_canvas:
        st.markdown(ui.section_label("Predictive Pre-Mortem"), unsafe_allow_html=True)
        for alert in engine.canvas.alerts:
            st.markdown(ui.premortem_card(alert), unsafe_allow_html=True)
            sev = alert.severity if isinstance(alert.severity, str) else alert.severity.value
            if sev in ("HIGH", "CRITICAL"):
                st.markdown(ui.risk_matrix(alert), unsafe_allow_html=True)

        if engine.canvas.actions:
            st.markdown(ui.section_label("Click-to-Execute Actions"), unsafe_allow_html=True)
            cols = st.columns(len(engine.canvas.actions))
            for col, action in zip(cols, engine.canvas.actions):
                with col:
                    if st.button(action.label, key=action.key, use_container_width=True):
                        engine.log_action("Operator", action.audit_action, "Fired from pre-mortem card.")
                        st.toast(action.toast)
                        st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(ui.history_trail(engine.audit), unsafe_allow_html=True)

    # ---- Tab 2 ---------------------------------------------------------- #
    with tab_cal:
        st.markdown(ui.section_label("Generative Calendar Asset"), unsafe_allow_html=True)
        st.markdown(ui.calendar_card(engine.canvas.calendar), unsafe_allow_html=True)
        st.caption(
            "This card is generated from a validated CalendarAsset, not free text. "
            "Its date, status colour and progress bar mutate with the storyline."
        )

    # ---- Bottom drawer — Transparency Center ---------------------------- #
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.expander("Transparency Center · System Trust & Verification Log", expanded=True):
        r = engine.report
        m1, m2, m3 = st.columns(3)
        m1.metric("Schema Validation Errors", r.schema_errors,
                  delta=f"{r.schema_quarantined} quarantined", delta_color="off")
        m2.metric("Faithfulness", f"{r.faithfulness:.2f}",
                  delta=f"precision {r.context_precision:.2f}", delta_color="off")
        m3.metric("Hallucination Suppression",
                  "ACTIVE" if r.hallucination_suppressed else "BREACH",
                  delta=str(r.eval_status), delta_color="off")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(ui.terminal_console(engine.terminal_log), unsafe_allow_html=True)


st.markdown(
    f"<div style='text-align:center;color:{ui.MUTED};font-size:11px;margin-top:22px;'>"
    f"Sulcus.pro · circadian memory consolidation · dual-gate guardrails · generative UI "
    f"· prototype build</div>",
    unsafe_allow_html=True,
)
