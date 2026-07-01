"""
Sulcus.pro — Autonomous Corporate Intelligence for NovaCorp
=============================================================

Single Streamlit entry point. World state (ticks, guardrail evaluation,
circadian consolidation, audit trail) lives in a ``SulcusEngine`` stored in
``st.session_state``; the raw NovaCorp event data that drives the UI lives in
Supabase and is queried directly here.

Run the generator first to seed data, then run the app:
    python generator.py
    streamlit run app.py
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import calendar as cal_module

import streamlit as st

from sulcus import SulcusEngine, TICK_TITLES, TOTAL_TICKS
from sulcus import generative_ui as ui
from sulcus.storyline import date_for_tick
from supabase_client import get_supabase_client

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title="Sulcus.pro — Autonomous Corporate Intelligence",
    page_icon=str(ASSETS / "sulcus_logo_sm.png") if (ASSETS / "sulcus_logo_sm.png").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEPARTMENTS = [
    "Engineering", "Product", "Sales", "Marketing",
    "Finance", "HR", "Legal", "DevOps",
]
SOURCES = [
    "slack", "github", "jira", "gmail", "outlook", "salesforce",
    "pagerduty", "datadog", "confluence", "figma", "workday", "notion",
]
RISK_LEVELS = ["low", "medium", "high", "critical"]
RISK_SCORE = {"low": 1, "medium": 2, "high": 3, "critical": 4}

DEPT_COLORS = {
    "Engineering": "#7C3AED",
    "Product": "#2563EB",
    "Sales": "#16A34A",
    "Marketing": "#F59E0B",
    "Finance": "#0EA5E9",
    "HR": "#EC4899",
    "Legal": "#6366F1",
    "DevOps": "#DC2626",
}
SOURCE_COLORS = {
    "slack": "#7C3AED",
    "github": "#374151",
    "jira": "#2563EB",
    "gmail": "#DC2626",
    "outlook": "#0EA5E9",
    "salesforce": "#0284C7",
    "pagerduty": "#16A34A",
    "datadog": "#9333EA",
    "confluence": "#2563EB",
    "figma": "#F59E0B",
    "workday": "#0F766E",
    "notion": "#475569",
}
STATUS_COLORS = {"Healthy": ui.GREEN, "At Risk": ui.AMBER, "Critical": ui.RED}


# --------------------------------------------------------------------------- #
# Global styling
# --------------------------------------------------------------------------- #
st.markdown(
    f"""
    <style>
      .stApp {{ background: radial-gradient(1200px 600px at 50% -10%, #15182B 0%, {ui.INK} 55%); }}
      header[data-testid="stHeader"] {{ background: transparent; }}
      .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1700px; }}
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
      .stTabs [data-baseweb="tab-list"] {{ gap: 4px; flex-wrap: wrap; }}
      .stTabs [data-baseweb="tab"] {{
          background:{ui.PANEL}; border-radius:10px 10px 0 0; padding:8px 14px; color:{ui.MUTED};
          font-size:13px;
      }}
      .stTabs [aria-selected="true"] {{ background:{ui.PANEL_2}; color:{ui.TEXT}; }}
      [data-testid="stChatInput"] textarea {{ background:{ui.PANEL}; color:{ui.TEXT}; }}
      .event-card {{ animation: sulcusFadeIn 0.4s ease-in; }}
      @keyframes sulcusFadeIn {{
          from {{ opacity: 0; transform: translateY(-6px); }}
          to {{ opacity: 1; transform: translateY(0); }}
      }}
      div[data-testid="stPopoverBody"] {{ background:{ui.PANEL}; }}

      /* --- Sidebar overlays content instead of pushing it --- */
      section[data-testid="stSidebar"] {{
          position: fixed;
          z-index: 999;
      }}
      .main .block-container {{
          padding-left: 1rem;
          transition: none;
      }}
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
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "logo" not in st.session_state:
    st.session_state.logo = _logo_b64()
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "tick_slider" not in st.session_state:
    st.session_state.tick_slider = st.session_state.engine.tick
if "anthropic_api_key" not in st.session_state:
    st.session_state.anthropic_api_key = ""
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False
if "selected_dept" not in st.session_state:
    st.session_state.selected_dept = None
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None

engine: SulcusEngine = st.session_state.engine
supabase = get_supabase_client()


def sync_engine_to_tick(target_tick: int) -> None:
    if target_tick == engine.tick:
        return
    if target_tick < engine.tick:
        engine.reset()
    while engine.tick < target_tick:
        engine.advance()


def resolve_anthropic_key() -> Optional[str]:
    if st.session_state.get("anthropic_api_key"):
        return st.session_state["anthropic_api_key"]
    try:
        if "ANTHROPIC_API_KEY" in st.secrets and st.secrets["ANTHROPIC_API_KEY"]:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY") or None


# --------------------------------------------------------------------------- #
# Supabase data access (raw NovaCorp events, queried directly for the UI)
# --------------------------------------------------------------------------- #
def fetch_events(
    departments: List[str],
    sources: List[str],
    risks: List[str],
    max_tick: int,
    limit: int = 800,
) -> List[dict]:
    if supabase is None:
        return []
    try:
        query = (
            supabase.table("events")
            .select("*")
            .lte("tick", max_tick)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if departments:
            query = query.in_("department", departments)
        if sources:
            query = query.in_("source", sources)
        if risks:
            query = query.in_("risk_level", risks)
        resp = query.execute()
        return resp.data or []
    except Exception:
        return []


def fetch_department_counts(max_tick: int) -> dict:
    if supabase is None:
        return {d: 0 for d in DEPARTMENTS}
    try:
        resp = (
            supabase.table("events")
            .select("department")
            .lte("tick", max_tick)
            .execute()
        )
        rows = resp.data or []
    except Exception:
        rows = []
    counts = {d: 0 for d in DEPARTMENTS}
    for r in rows:
        d = r.get("department")
        if d in counts:
            counts[d] += 1
    return counts


def fetch_total_events_processed() -> int:
    if supabase is None:
        return 0
    try:
        resp = supabase.table("events").select("id", count="exact").execute()
        return resp.count or 0
    except Exception:
        return 0


def fetch_last_n_events(n: int = 20) -> List[dict]:
    if supabase is None:
        return []
    try:
        resp = (
            supabase.table("events")
            .select("*")
            .order("created_at", desc=True)
            .limit(n)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def save_chat_turn(role: str, content: str) -> None:
    if supabase is None:
        return
    try:
        supabase.table("chat_history").insert(
            {"role": role, "content": content, "session_id": st.session_state.session_id}
        ).execute()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _fmt_ts(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return str(value)


def _fmt_time(value: Optional[str]) -> str:
    if not value:
        return "--:--"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return "--:--"


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_event_card(row: dict) -> None:
    dept = row.get("department", "Unknown")
    source = row.get("source", "")
    risk = row.get("risk_level", "low")
    actor = row.get("actor", "Unknown")
    content = row.get("content", "")
    ts = _fmt_ts(row.get("created_at"))

    dept_color = DEPT_COLORS.get(dept, ui.MUTED)
    src_color = SOURCE_COLORS.get(source, ui.MUTED)
    risk_color = ui.RISK_COLORS.get(risk, ui.MUTED)

    st.markdown(
        f"""
        <div class="event-card" style="background:{ui.PANEL};border:1px solid #262C40;
             border-left:4px solid {risk_color};border-radius:12px;padding:14px 16px;
             margin-bottom:10px;">
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px;">
            <span style="background:{src_color}33;color:{src_color};border:1px solid {src_color}66;
                 padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:700;
                 letter-spacing:0.5px;">{_esc(source)}</span>
            <span style="background:{dept_color}22;color:{dept_color};border:1px solid {dept_color}55;
                 padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:700;">{_esc(dept)}</span>
            <span style="background:{risk_color}22;color:{risk_color};border:1px solid {risk_color}66;
                 padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:800;
                 text-transform:uppercase;letter-spacing:0.5px;">{risk}</span>
          </div>
          <div style="font-size:13px;font-weight:700;color:{ui.TEXT};">{_esc(actor)}</div>
          <div style="font-size:13.5px;color:{ui.TEXT};margin-top:4px;line-height:1.5;">{_esc(content)}</div>
          <div style="font-size:11px;color:{ui.MUTED};margin-top:8px;">{ts} · tick {row.get('tick', '-')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("View Risk", expanded=False):
        st.write(row.get("risk_reason", "No risk detail available."))


def department_status(rows: List[dict]) -> str:
    risks = {r.get("risk_level") for r in rows}
    if "critical" in risks:
        return "Critical"
    if "high" in risks:
        return "At Risk"
    return "Healthy"


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

if supabase is None:
    st.warning(
        "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY to "
        ".streamlit/secrets.toml, then run `python generator.py` to seed data."
    )


# --------------------------------------------------------------------------- #
# Floating chat widget — toggle button + panel, fixed bottom-right.
# Rendered early so it lives high in the DOM; CSS position:fixed keeps it
# pinned to the viewport corner regardless of where the rest of the page
# scrolls, and it stays out of the main dashboard/calendar/audit panels.
# --------------------------------------------------------------------------- #
def render_chat_bubble(role: str, content: str) -> None:
    is_user = role == "user"
    justify = "flex-end" if is_user else "flex-start"
    bg = "#2A3050" if is_user else "#242A3D"
    st.markdown(
        f"""<div style="display:flex;justify-content:{justify};margin-bottom:8px;">
          <div style="max-width:85%;background:{bg};color:{ui.TEXT};padding:8px 12px;
               border-radius:12px;font-size:12.5px;line-height:1.45;white-space:pre-wrap;">
            {_esc(content)}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def run_sulcus_chat(prompt: str) -> str:
    api_key = resolve_anthropic_key()
    if not api_key:
        return "Enter an Anthropic API key above to enable Sulcus intelligence."
    try:
        import anthropic

        context_events = fetch_last_n_events(20)
        context_lines = "\n".join(
            f"- [{e.get('department')}/{e.get('source')}] "
            f"{e.get('actor')}: {e.get('content')} "
            f"(risk={e.get('risk_level')}, tick={e.get('tick')})"
            for e in context_events
        ) or "No events available."

        system_prompt = (
            "You are Sulcus, the autonomous corporate intelligence agent for "
            "NovaCorp. You have access to all operational events across "
            "departments. Be concise, direct, and risk-aware. Never "
            "hallucinate — only reference events that exist in the context "
            "provided.\n\nRecent NovaCorp events:\n" + context_lines
        )

        client = anthropic.Anthropic(api_key=api_key)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages
            if m["role"] in ("user", "assistant")
        ]
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=system_prompt,
            messages=history,
        )
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        ) or "No response generated."
    except Exception as exc:
        return f"Sulcus could not reach the model: {exc}"


def render_floating_chat() -> None:
    bubble_svg = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'>"
        "<path d='M4 4h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H9l-4.3 3.3A1 1 0 0 1 3 19.5V5a1 1 0 0 1 1-1z'/>"
        "</svg>"
    )
    st.markdown(
        f"""
        <style>
          .st-key-chat_toggle_btn button {{
              position: fixed !important; bottom: 28px; right: 28px; z-index: 9999;
              width: 56px; height: 56px; border-radius: 50% !important;
              background: {ui.VIOLET} !important; border: none !important;
              font-size: 0 !important; background-image: url("{bubble_svg}") !important;
              background-repeat: no-repeat !important; background-position: center !important;
              background-size: 24px 24px !important;
              box-shadow: 0 6px 20px rgba(124,58,237,0.55) !important;
          }}
          .st-key-chat_panel_wrap {{
              position: fixed !important; bottom: 96px; right: 28px; z-index: 9998;
              width: 380px; max-width: 90vw; max-height: 520px; overflow-y: auto;
              background: #1A1F2E; border: 1px solid #2E3550; border-radius: 16px;
              box-shadow: 0 12px 40px rgba(0,0,0,0.55); padding: 14px 14px 8px 14px;
          }}
          .st-key-chat_close_btn button {{
              width: 28px; height: 28px; padding: 0; border-radius: 8px;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Chat", key="chat_toggle_btn"):
        st.session_state.chat_open = not st.session_state.chat_open

    if not st.session_state.chat_open:
        return

    with st.container(key="chat_panel_wrap"):
        head_l, head_r = st.columns([5, 1])
        with head_l:
            st.markdown(
                f"""<div style="color:{ui.TEXT};font-weight:800;font-size:14px;
                     padding-top:4px;">Sulcus Intelligence</div>""",
                unsafe_allow_html=True,
            )
        with head_r:
            if st.button("X", key="chat_close_btn"):
                st.session_state.chat_open = False
                st.rerun()

        st.text_input(
            "Demo API Key",
            type="password",
            placeholder="sk-ant-...",
            key="anthropic_api_key",
            label_visibility="collapsed",
            help="Anthropic API key for this demo session. Stored only in this browser session.",
        )

        message_area = st.container(height=260)
        with message_area:
            if not st.session_state.chat_messages:
                st.caption("Ask Sulcus about NovaCorp's risks, departments, or status.")
            for msg in st.session_state.chat_messages:
                render_chat_bubble(msg["role"], msg["content"])

        prompt = st.chat_input("Message Sulcus...", key="floating_chat_input")
        if prompt:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            save_chat_turn("user", prompt)
            with message_area:
                render_chat_bubble("user", prompt)
                thinking = st.empty()
                thinking.markdown(
                    f'<div style="color:{ui.MUTED};font-size:12px;padding:4px 0;">'
                    f"Sulcus is thinking...</div>",
                    unsafe_allow_html=True,
                )
                answer = run_sulcus_chat(prompt)
                thinking.empty()
                render_chat_bubble("assistant", answer)
            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
            save_chat_turn("assistant", answer)


render_floating_chat()


# --------------------------------------------------------------------------- #
# Sidebar — filters & controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(ui.section_label("Filters"), unsafe_allow_html=True)
    sel_departments = st.multiselect(
        "Departments", DEPARTMENTS, default=[], placeholder="All Departments"
    )
    sel_sources = st.multiselect(
        "Sources", SOURCES, default=[], placeholder="All Sources"
    )
    sel_risks = st.multiselect(
        "Risk Level", RISK_LEVELS, default=[], placeholder="All Levels"
    )

    st.markdown(ui.section_label("Simulation"), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Advance", use_container_width=True, type="primary", disabled=engine.is_final):
            msg = engine.advance()
            st.session_state.tick_slider = engine.tick
            st.toast(msg)
            st.rerun()
    with c2:
        if st.button("Reset", use_container_width=True):
            engine.reset()
            st.session_state.chat_messages = []
            st.session_state.tick_slider = 0
            st.toast("Simulation reset to Tick 0.")
            st.rerun()

    selected_tick = st.slider("Tick", 0, TOTAL_TICKS - 1, key="tick_slider")
    if selected_tick != engine.tick:
        sync_engine_to_tick(selected_tick)
        st.rerun()

    if engine.is_final:
        st.caption("Story at final tick — reset to replay.")

    st.markdown(ui.section_label("Events Live Per Department"), unsafe_allow_html=True)
    dept_counts = fetch_department_counts(engine.tick)
    for d in DEPARTMENTS:
        n = dept_counts.get(d, 0)
        color = DEPT_COLORS.get(d, ui.MUTED)
        st.markdown(
            f"""<div style="display:flex;justify-content:space-between;align-items:center;
                 padding:3px 0;font-size:12.5px;">
              <span style="color:{ui.TEXT};">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                     background:{color};margin-right:7px;"></span>{d}</span>
              <span style="color:{ui.MUTED};font-weight:700;">{n}</span>
            </div>""",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Shared filtered dataset for this run. Empty filter selections mean "show
# all" — fetch_events only applies an .in_() clause when the list is non-empty.
# --------------------------------------------------------------------------- #
all_visible_events = fetch_events(sel_departments, sel_sources, sel_risks, engine.tick)
critical_events = [e for e in all_visible_events if e.get("risk_level") == "critical"]
high_or_critical = [e for e in all_visible_events if e.get("risk_level") in ("high", "critical")]


tab_dashboard, tab_calendar, tab_audit = st.tabs(["Dashboard", "Calendar", "Audit Trail"])


# --------------------------------------------------------------------------- #
# DASHBOARD — Live Event Feed + Department Intelligence
# --------------------------------------------------------------------------- #
with tab_dashboard:
    head_l, head_r = st.columns([3, 1])
    with head_l:
        st.markdown(ui.section_label("Live Event Feed"), unsafe_allow_html=True)
    with head_r:
        st.markdown(
            f"""<div style="text-align:right;">
              <span style="background:{ui.RED}22;color:{ui.RED};border:1px solid {ui.RED}55;
                   padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;">
                ALERTS {len(high_or_critical)}</span></div>""",
            unsafe_allow_html=True,
        )

    if critical_events:
        top = critical_events[0]
        st.markdown(
            f"""<div style="border:1px solid {ui.RED}88;background:{ui.RED}15;border-radius:10px;
                 padding:10px 14px;margin-bottom:12px;">
              <span style="color:{ui.RED};font-weight:800;font-size:13px;">CRITICAL —
              {_esc(top.get('department',''))}: {_esc(top.get('content',''))[:110]}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    with st.container(height=520, border=False):
        if not all_visible_events:
            st.caption("No events match the current filters.")
        for row in all_visible_events[:80]:
            render_event_card(row)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(ui.section_label("Department Intelligence"), unsafe_allow_html=True)

    dept_cols = st.columns(8)
    for col, dept in zip(dept_cols, DEPARTMENTS):
        dept_rows = [e for e in all_visible_events if e.get("department") == dept]
        this_tick_rows = [e for e in dept_rows if e.get("tick") == engine.tick]
        status = department_status(this_tick_rows)
        status_color = STATUS_COLORS[status]
        with col:
            st.markdown(
                f"""<div style="text-align:center;">
                  <div style="font-size:12px;font-weight:800;color:{ui.TEXT};
                       margin-bottom:6px;white-space:nowrap;overflow:hidden;
                       text-overflow:ellipsis;">{_esc(dept.split()[0])}</div>
                  <span style="display:inline-block;background:{status_color};color:#0B0E1A;
                       padding:2px 10px;border-radius:999px;font-size:10px;font-weight:800;
                       letter-spacing:0.3px;">{status}</span>
                  <div style="font-size:16px;font-weight:800;color:{ui.MUTED};margin-top:6px;">
                       {len(this_tick_rows)}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            if st.button("View", key=f"deptbtn_{dept}", use_container_width=True):
                st.session_state.selected_dept = (
                    None if st.session_state.selected_dept == dept else dept
                )

    if st.session_state.selected_dept:
        sel_dept = st.session_state.selected_dept
        sel_dept_rows = [e for e in all_visible_events if e.get("department") == sel_dept]
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown(
            ui.section_label(f"{sel_dept} — Event Detail"), unsafe_allow_html=True
        )
        with st.container(height=400, border=False):
            if not sel_dept_rows:
                st.caption(f"No {sel_dept} events match the current filters.")
            for row in sel_dept_rows[:60]:
                render_event_card(row)


# --------------------------------------------------------------------------- #
# CALENDAR — full month grid, click a date to inspect its events
# --------------------------------------------------------------------------- #
with tab_calendar:
    st.markdown(ui.section_label("Evolving Calendar — July 2026"), unsafe_allow_html=True)

    epoch = date_for_tick(0)
    cal_grid = cal_module.Calendar(firstweekday=0)
    month_dates = list(cal_grid.itermonthdates(2026, 7))
    weeks = [month_dates[i:i + 7] for i in range(0, len(month_dates), 7)]

    day_events = {}
    for row in all_visible_events:
        d = date_for_tick(int(row.get("tick", 0)))
        day_events.setdefault(d, []).append(row)

    cal_css_rules = []
    for week in weeks:
        for d in week:
            tick_for_day = (d - epoch).days
            evs = day_events.get(d, [])
            if evs:
                worst = max(evs, key=lambda r: RISK_SCORE.get(r.get("risk_level"), 0))
                color = ui.RISK_COLORS.get(worst.get("risk_level"), "#262C40")
            elif 0 <= tick_for_day < TOTAL_TICKS:
                color = "#1B2030"
            else:
                color = "#12151F"
            text_color = ui.TEXT if d.month == 7 else ui.MUTED
            key = f"cal_{d.isoformat()}"
            cal_css_rules.append(
                f'.st-key-{key} button {{ background:{color} !important; '
                f'color:{text_color} !important; border:1px solid #2A3043 !important; }}'
            )
    st.markdown(f"<style>{''.join(cal_css_rules)}</style>", unsafe_allow_html=True)

    st.markdown(
        f"""<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;
             font-size:10px;color:{ui.MUTED};text-align:center;margin-bottom:4px;">
          <div>MON</div><div>TUE</div><div>WED</div><div>THU</div>
          <div>FRI</div><div>SAT</div><div>SUN</div></div>""",
        unsafe_allow_html=True,
    )

    for week in weeks:
        cols = st.columns(7)
        for col, d in zip(cols, week):
            with col:
                key = f"cal_{d.isoformat()}"
                if st.button(str(d.day), key=key, use_container_width=True):
                    st.session_state.selected_date = d.isoformat()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(ui.section_label("Events On Selected Date"), unsafe_allow_html=True)

    if not st.session_state.selected_date:
        st.caption("Select a date on the calendar to view events.")
    else:
        sel_d = st.session_state.selected_date
        try:
            sel_date_obj = datetime.fromisoformat(sel_d).date()
        except Exception:
            sel_date_obj = None
        day_rows = day_events.get(sel_date_obj, []) if sel_date_obj else []

        st.caption(
            (sel_date_obj.strftime("%B %d, %Y") if sel_date_obj else sel_d)
        )
        if not day_rows:
            st.caption("No events on this date.")
        else:
            options = [
                f"{_fmt_time(r.get('created_at'))} — {r.get('actor','Unknown')} — "
                f"{r.get('content','')[:60]}"
                for r in day_rows
            ]
            picked = st.selectbox("Events", options, label_visibility="collapsed", key="calendar_event_pick")
            picked_row = day_rows[options.index(picked)]
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            render_event_card(picked_row)


# --------------------------------------------------------------------------- #
# AUDIT TRAIL — Temporal Brain history, grouped by tick
# --------------------------------------------------------------------------- #
with tab_audit:
    st.markdown(ui.section_label("Audit Trail"), unsafe_allow_html=True)
    st.caption("Temporal Brain · human actions and autonomous system actions, grouped by tick.")
    st.markdown(ui.audit_timeline(engine.audit), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# BOTTOM — Transparency Center (always visible)
# --------------------------------------------------------------------------- #
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
st.markdown(ui.section_label("Transparency Center · System Trust & Verification Log"), unsafe_allow_html=True)

r = engine.report
m1, m2, m3, m4 = st.columns(4)
m1.metric("Schema Errors", r.schema_errors, delta=f"{r.schema_quarantined} quarantined", delta_color="off")
m2.metric("Faithfulness Score", f"{r.faithfulness:.2f}", delta=f"precision {r.context_precision:.2f}", delta_color="off")
m3.metric("Hallucination Suppression", "ACTIVE" if r.hallucination_suppressed else "BREACH", delta=str(r.eval_status), delta_color="off")
m4.metric("Events Processed", fetch_total_events_processed())

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown(ui.terminal_console(engine.terminal_log), unsafe_allow_html=True)

st.markdown(
    f"<div style='text-align:center;color:{ui.MUTED};font-size:11px;margin-top:22px;'>"
    f"Sulcus.pro · circadian memory consolidation · dual-gate guardrails · live NovaCorp data "
    f"· prototype build</div>",
    unsafe_allow_html=True,
)
