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
from datetime import date, datetime
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
    initial_sidebar_state="expanded",
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
# Sidebar — filters & controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(ui.section_label("Filters"), unsafe_allow_html=True)
    sel_departments = st.multiselect("Department", DEPARTMENTS, default=DEPARTMENTS)
    sel_sources = st.multiselect("Source", SOURCES, default=SOURCES)
    sel_risks = st.multiselect("Risk", RISK_LEVELS, default=RISK_LEVELS)

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
# Shared filtered dataset for this run
# --------------------------------------------------------------------------- #
all_visible_events = fetch_events(sel_departments, sel_sources, sel_risks, engine.tick)
critical_events = [e for e in all_visible_events if e.get("risk_level") == "critical"]
high_or_critical = [e for e in all_visible_events if e.get("risk_level") in ("high", "critical")]


left, center, right = st.columns([3, 4, 3], gap="medium")


# --------------------------------------------------------------------------- #
# LEFT — Live Event Feed
# --------------------------------------------------------------------------- #
with left:
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

    if not all_visible_events:
        st.caption("No events match the current filters.")
    for row in all_visible_events[:80]:
        render_event_card(row)


# --------------------------------------------------------------------------- #
# CENTER — Department Intelligence
# --------------------------------------------------------------------------- #
with center:
    st.markdown(ui.section_label("Department Intelligence"), unsafe_allow_html=True)
    dept_tabs = st.tabs(DEPARTMENTS + ["Audit Trail"])

    for tab, dept in zip(dept_tabs[:-1], DEPARTMENTS):
        with tab:
            dept_rows = [e for e in all_visible_events if e.get("department") == dept]
            this_tick_rows = [e for e in dept_rows if e.get("tick") == engine.tick]
            avg_risk = (
                sum(RISK_SCORE.get(r.get("risk_level"), 1) for r in dept_rows) / len(dept_rows)
                if dept_rows else 0.0
            )
            open_incidents = sum(1 for r in dept_rows if r.get("risk_level") in ("high", "critical"))
            status = department_status(dept_rows)
            status_color = {"Healthy": ui.GREEN, "At Risk": ui.AMBER, "Critical": ui.RED}[status]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Events This Tick", len(this_tick_rows))
            k2.metric("Risk Score", f"{avg_risk:.1f} / 4")
            k3.metric("Open Incidents", open_incidents)
            k4.markdown(
                f"""<div style="margin-top:6px;">
                  <div style="font-size:11px;color:{ui.MUTED};letter-spacing:1px;
                       text-transform:uppercase;">Status</div>
                  <div style="font-size:18px;font-weight:800;color:{status_color};
                       margin-top:4px;">{status}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            if not dept_rows:
                st.caption(f"No {dept} events match the current filters.")
            for row in dept_rows[:40]:
                render_event_card(row)

    with dept_tabs[-1]:
        st.caption("Temporal Brain · human actions and autonomous system actions, grouped by tick.")
        st.markdown(ui.audit_timeline(engine.audit), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# RIGHT — API key, Evolving Calendar, Chat
# --------------------------------------------------------------------------- #
with right:
    st.text_input(
        "Demo API Key",
        type="password",
        placeholder="sk-ant-...",
        key="anthropic_api_key",
        help="Anthropic API key for this demo session. Stored only in this browser session.",
    )

    st.markdown(ui.section_label("Evolving Calendar — July 2026"), unsafe_allow_html=True)

    epoch = date(2026, 6, 30)
    cal_grid = cal_module.Calendar(firstweekday=0)
    month_dates = list(cal_grid.itermonthdates(2026, 7))
    weeks = [month_dates[i:i + 7] for i in range(0, len(month_dates), 7)]

    st.markdown(
        f"""<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;
             font-size:10px;color:{ui.MUTED};text-align:center;margin-bottom:4px;">
          <div>MON</div><div>TUE</div><div>WED</div><div>THU</div>
          <div>FRI</div><div>SAT</div><div>SUN</div></div>""",
        unsafe_allow_html=True,
    )

    day_events = {}
    for row in all_visible_events:
        d = date_for_tick(int(row.get("tick", 0)))
        day_events.setdefault(d, []).append(row)

    for week in weeks:
        cols = st.columns(7)
        for col, d in zip(cols, week):
            with col:
                in_month = d.month == 7
                tick_for_day = (d - epoch).days
                evs = day_events.get(d, [])
                if evs:
                    worst = max(evs, key=lambda r: RISK_SCORE.get(r.get("risk_level"), 0))
                    block_color = ui.RISK_COLORS.get(worst.get("risk_level"), "#262C40")
                else:
                    block_color = "#1B2030" if (0 <= tick_for_day < TOTAL_TICKS) else "#12151F"
                opacity = "1" if in_month else "0.35"
                st.markdown(
                    f"""<div style="opacity:{opacity};background:{block_color}55;
                         border:1px solid {block_color};border-radius:8px;padding:4px 0;
                         text-align:center;font-size:11px;color:{ui.TEXT};margin-bottom:2px;">
                      {d.day}</div>""",
                    unsafe_allow_html=True,
                )
                with st.popover(f"{len(evs)}", use_container_width=True):
                    st.markdown(f"**{d.strftime('%B %d, %Y')}**")
                    if not evs:
                        st.caption("No events on this date.")
                    for e in evs[:10]:
                        st.markdown(
                            f"- **{_esc(e.get('department',''))}** "
                            f"({e.get('risk_level','')}) — {_esc(e.get('content',''))[:90]}"
                        )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown(ui.section_label("Sulcus — Ask the Intelligence Layer"), unsafe_allow_html=True)

    chat_box = st.container(height=320)
    with chat_box:
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    prompt = st.chat_input("Ask Sulcus about NovaCorp's risks, departments, or status...")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        save_chat_turn("user", prompt)

        api_key = resolve_anthropic_key()
        with chat_box:
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                if not api_key:
                    answer = "Enter an Anthropic API key above to enable Sulcus intelligence."
                    st.markdown(answer)
                else:
                    placeholder = st.empty()
                    placeholder.markdown("Sulcus is thinking...")
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
                        answer = "".join(
                            block.text for block in response.content if hasattr(block, "text")
                        ) or "No response generated."
                    except Exception as exc:
                        answer = f"Sulcus could not reach the model: {exc}"
                    placeholder.markdown(answer)

        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
        save_chat_turn("assistant", answer)


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
