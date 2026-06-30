"""
sulcus.generative_ui
=====================

The Mouth. Shared brand palette plus the HTML/CSS renderers still used by the
v2 UI: the brand header, the dark terminal console (Transparency Center), the
Temporal Brain audit timeline, and small section labels. The v1 calendar/
pre-mortem/risk-matrix card renderers are gone -- v2 replaces those visuals
with the live event-card feed, department KPI tabs and the evolving month
calendar built directly in ``app.py``.

All styling is inline so the module is self-contained and renders identically
on Streamlit Community Cloud or behind a custom domain (sulcus.pro).
"""

from __future__ import annotations

from typing import List

from .schemas import AuditEntry

# Brand palette --------------------------------------------------------------
INK = "#0B0E1A"
PANEL = "#141826"
PANEL_2 = "#1B2030"
VIOLET = "#7C3AED"
VIOLET_SOFT = "#A78BFA"
GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"
ORANGE = "#FB923C"
GREY = "#8A90A6"
TEXT = "#E6E8F0"
MUTED = "#8A90A6"

RISK_COLORS = {
    "low": GREY,
    "medium": AMBER,
    "high": ORANGE,
    "critical": RED,
}


# --------------------------------------------------------------------------- #
def brand_header(logo_b64: str) -> str:
    return f"""
    <div style="display:flex;align-items:center;gap:16px;padding:6px 4px 14px 4px;">
      <img src="data:image/png;base64,{logo_b64}" width="58" height="58"
           style="border-radius:12px;box-shadow:0 0 24px rgba(124,58,237,0.45);"/>
      <div>
        <div style="font-size:30px;font-weight:800;letter-spacing:0.5px;color:{TEXT};
             font-family:'Inter',system-ui,sans-serif;line-height:1;">
          Sulcus<span style="color:{VIOLET_SOFT};">.pro</span>
        </div>
        <div style="font-size:13px;color:{MUTED};margin-top:4px;letter-spacing:2px;
             text-transform:uppercase;">Autonomous Corporate Intelligence · NovaCorp</div>
      </div>
    </div>
    """


def section_label(text: str) -> str:
    return (
        f'<div style="font-size:12px;color:{MUTED};letter-spacing:2px;'
        f'text-transform:uppercase;margin:6px 0 8px 0;">{text}</div>'
    )


def terminal_console(lines: List[str]) -> str:
    body = ""
    for ln in lines:
        c = "#7CFC9B"  # default light green mono
        if "WARNING" in ln or "DRIFT" in ln or "WARN" in ln:
            c = AMBER
        elif "FAIL" in ln or "BLOCKED" in ln or "FAILED" in ln:
            c = "#FF7B7B"
        elif "CIRCADIAN" in ln:
            c = VIOLET_SOFT
        elif "PASS" in ln or "GROUND" in ln:
            c = "#7CFC9B"
        elif ln.startswith("[SULCUS]"):
            c = "#9AD0FF"
        safe = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body += f'<div style="color:{c};white-space:pre-wrap;">{safe or "&nbsp;"}</div>'
    return f"""
    <div style="background:#1E1E1E;border:1px solid #333;border-radius:12px;padding:16px 18px;
         font-family:'SF Mono','Menlo','Consolas',monospace;font-size:12px;line-height:1.55;
         max-height:340px;overflow-y:auto;box-shadow:inset 0 0 24px rgba(0,0,0,0.5);">
      <div style="color:#6B7280;margin-bottom:8px;">
        sulcus@core:~/transparency-center$ tail -f gate1_gate2_circadian.log</div>
      {body}
      <div style="color:#6B7280;margin-top:8px;">|</div>
    </div>
    """


_AUDIT_BADGE = {
    "HUMAN": GREEN,
    "BRAIN": VIOLET_SOFT,
    "SYSTEM": GREY,
}


def _audit_category(entry: AuditEntry) -> str:
    kind = entry.actor_kind if isinstance(entry.actor_kind, str) else entry.actor_kind.value
    if kind != "SYSTEM":
        return "HUMAN"
    if entry.actor in ("Circadian Loop", "Knowledge Graph"):
        return "BRAIN"
    return "SYSTEM"


def audit_timeline(entries: List[AuditEntry]) -> str:
    """Vertical timeline of audit cards, grouped by tick with a divider between groups."""
    if not entries:
        return f'<div style="color:{MUTED};font-size:13px;padding:12px 0;">No audit entries yet.</div>'

    body = ""
    last_tick = None
    for e in entries[:60]:
        if e.tick != last_tick:
            body += (
                f'<div style="display:flex;align-items:center;gap:10px;margin:14px 0 6px 0;">'
                f'<div style="height:1px;flex:0 0 14px;background:#262C40;"></div>'
                f'<div style="font-size:11px;color:{MUTED};letter-spacing:1.5px;'
                f'text-transform:uppercase;white-space:nowrap;">Tick {e.tick}</div>'
                f'<div style="height:1px;flex:1;background:#262C40;"></div></div>'
            )
            last_tick = e.tick
        cat = _audit_category(e)
        color = _AUDIT_BADGE[cat]
        ts = e.timestamp.strftime("%H:%M:%S")
        action = e.action.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        detail = e.detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body += f"""
        <div style="background:{PANEL};border:1px solid #262C40;border-left:3px solid {color};
             border-radius:10px;padding:10px 14px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
            <span style="font-size:13px;font-weight:700;color:{TEXT};">{action}</span>
            <span style="background:{color}22;color:{color};padding:2px 9px;border-radius:7px;
                 font-size:10px;font-weight:800;letter-spacing:1px;white-space:nowrap;">{cat}</span>
          </div>
          <div style="font-size:12.5px;color:{MUTED};margin-top:5px;line-height:1.5;">{detail}</div>
          <div style="font-size:10.5px;color:{MUTED};margin-top:6px;letter-spacing:0.5px;">
            {e.actor} · {ts}</div>
        </div>"""
    return body
