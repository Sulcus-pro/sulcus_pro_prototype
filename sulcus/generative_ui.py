"""
sulcus.generative_ui
=====================

The Mouth. Functions that turn validated payloads into custom HTML/CSS assets
instead of plain text -- the calendar card, the predictive pre-mortem risk card,
the risk matrix, the temporal-brain history trail, and the dark terminal console.

All styling is inline so the module is self-contained and renders identically on
Streamlit Community Cloud or behind a custom domain (sulcus.pro).
"""

from __future__ import annotations

from typing import List

from .schemas import (
    AuditEntry,
    CalendarAsset,
    GenerativeCanvas,
    GuardrailReport,
    PreMortemAlert,
)

# Brand palette --------------------------------------------------------------
INK = "#0B0E1A"
PANEL = "#141826"
PANEL_2 = "#1B2030"
VIOLET = "#7C3AED"
VIOLET_SOFT = "#A78BFA"
GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"
TEXT = "#E6E8F0"
MUTED = "#8A90A6"

_STATUS_COLORS = {
    "On Track": GREEN,
    "At Risk": AMBER,
    "Delayed": RED,
}
_SEV_COLORS = {
    "INFO": GREEN,
    "LOW": GREEN,
    "MEDIUM": AMBER,
    "HIGH": "#FB7185",
    "CRITICAL": RED,
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
             text-transform:uppercase;">The Autonomous Corporate Nervous System</div>
      </div>
    </div>
    """


def calendar_card(cal: CalendarAsset) -> str:
    status = cal.status if isinstance(cal.status, str) else cal.status.value
    color = _STATUS_COLORS.get(status, MUTED)
    return f"""
    <div style="background:linear-gradient(160deg,{PANEL},{PANEL_2});border:1px solid #262C40;
         border-radius:16px;padding:20px 22px;margin-bottom:14px;
         box-shadow:0 8px 30px rgba(0,0,0,0.35);">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:13px;color:{MUTED};letter-spacing:2px;text-transform:uppercase;">
          Live Evolving Calendar</div>
        <span style="background:{color}22;color:{color};border:1px solid {color}55;
             padding:5px 12px;border-radius:999px;font-size:12px;font-weight:700;">
             ● {status}</span>
      </div>
      <div style="font-size:24px;font-weight:800;color:{TEXT};margin-top:14px;">{cal.title}</div>
      <div style="display:flex;gap:26px;margin-top:14px;flex-wrap:wrap;">
        <div>
          <div style="font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:1px;">When</div>
          <div style="font-size:18px;color:{VIOLET_SOFT};font-weight:700;">{cal.human_date}</div>
          <div style="font-size:12px;color:{MUTED};">{cal.iso_date}</div>
        </div>
        <div>
          <div style="font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:1px;">Payment Rail</div>
          <div style="font-size:18px;color:{TEXT};font-weight:700;">{cal.payment_rail}</div>
        </div>
      </div>
      <div style="margin-top:14px;height:8px;border-radius:999px;background:#0E1220;overflow:hidden;">
        <div style="height:100%;width:{'40%' if status=='Delayed' else '100%'};
             background:linear-gradient(90deg,{VIOLET},{color});"></div>
      </div>
      <div style="font-size:12.5px;color:{MUTED};margin-top:10px;">{cal.note}</div>
    </div>
    """


def premortem_card(alert: PreMortemAlert) -> str:
    sev = alert.severity if isinstance(alert.severity, str) else alert.severity.value
    color = _SEV_COLORS.get(sev, MUTED)
    return f"""
    <div style="background:{PANEL};border:1px solid {color}44;border-left:4px solid {color};
         border-radius:14px;padding:18px 20px;margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:16px;font-weight:800;color:{TEXT};">{alert.headline}</div>
        <span style="background:{color}22;color:{color};padding:3px 10px;border-radius:8px;
             font-size:11px;font-weight:800;letter-spacing:1px;">{sev}</span>
      </div>
      <div style="font-size:13.5px;color:{MUTED};margin-top:10px;line-height:1.55;">{alert.detail}</div>
    </div>
    """


def risk_matrix(alert: PreMortemAlert) -> str:
    """A 3x3 likelihood/impact matrix with the alert plotted on it."""
    levels = ["High", "Medium", "Low"]
    like = alert.likelihood
    impact = alert.impact
    cells = ""
    for row in levels:                 # likelihood top→bottom High→Low
        cells += '<div style="display:flex;gap:6px;margin-bottom:6px;">'
        for col in ["Low", "Medium", "High"]:   # impact left→right
            score = (levels.index(row), ["Low", "Medium", "High"].index(col))
            heat = score[1] + (2 - score[0])
            base = [GREEN, GREEN, AMBER, AMBER, RED, RED][min(heat, 5)]
            active = (row == like and col == impact)
            mark = "◉" if active else ""
            border = f"2px solid {TEXT}" if active else f"1px solid #2A3043"
            cells += (
                f'<div style="flex:1;height:38px;border-radius:8px;background:{base}'
                f'{"55" if not active else "AA"};border:{border};display:flex;'
                f'align-items:center;justify-content:center;color:{TEXT};font-size:15px;">{mark}</div>'
            )
        cells += "</div>"
    return f"""
    <div style="background:{PANEL};border:1px solid #262C40;border-radius:14px;padding:16px 18px;margin-bottom:12px;">
      <div style="font-size:12px;color:{MUTED};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
        Downstream Risk Matrix · likelihood × impact</div>
      <div style="display:flex;gap:8px;">
        <div style="display:flex;flex-direction:column;justify-content:space-between;
             font-size:10px;color:{MUTED};padding:4px 0;writing-mode:vertical-rl;transform:rotate(180deg);">
             LIKELIHOOD</div>
        <div style="flex:1;">{cells}
          <div style="display:flex;justify-content:space-between;font-size:10px;color:{MUTED};margin-top:2px;">
            <span>Low</span><span>IMPACT</span><span>High</span></div>
        </div>
      </div>
    </div>
    """


def history_trail(entries: List[AuditEntry]) -> str:
    rows = ""
    for e in entries[:14]:
        is_sys = (e.actor_kind if isinstance(e.actor_kind, str) else e.actor_kind.value) == "SYSTEM"
        dot = VIOLET_SOFT if is_sys else GREEN
        tag = "BRAIN" if is_sys else "HUMAN"
        ts = e.timestamp.strftime("%H:%M")
        rows += f"""
        <div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #20263a;">
          <div style="color:{dot};font-size:9px;padding-top:5px;">●</div>
          <div style="flex:1;">
            <div style="font-size:13px;color:{TEXT};font-weight:600;">{e.action}</div>
            <div style="font-size:12px;color:{MUTED};margin-top:2px;">{e.detail}</div>
            <div style="font-size:10.5px;color:{MUTED};margin-top:4px;letter-spacing:0.5px;">
              {tag} · {e.actor} · {ts} · tick {e.tick}</div>
          </div>
        </div>"""
    return f"""
    <div style="background:{PANEL};border:1px solid #262C40;border-radius:14px;padding:6px 18px 12px 18px;">
      <div style="font-size:12px;color:{MUTED};letter-spacing:1.5px;text-transform:uppercase;
           padding:12px 0 4px 0;">Temporal Brain · history trail</div>
      {rows}
    </div>
    """


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
        safe = (
            ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        body += f'<div style="color:{c};white-space:pre-wrap;">{safe or "&nbsp;"}</div>'
    return f"""
    <div style="background:#1E1E1E;border:1px solid #333;border-radius:12px;padding:16px 18px;
         font-family:'SF Mono','Menlo','Consolas',monospace;font-size:12px;line-height:1.55;
         max-height:340px;overflow-y:auto;box-shadow:inset 0 0 24px rgba(0,0,0,0.5);">
      <div style="color:#6B7280;margin-bottom:8px;">
        sulcus@core:~/transparency-center$ tail -f gate1_gate2_circadian.log</div>
      {body}
      <div style="color:#6B7280;margin-top:8px;">▌</div>
    </div>
    """


def section_label(text: str) -> str:
    return (
        f'<div style="font-size:12px;color:{MUTED};letter-spacing:2px;'
        f'text-transform:uppercase;margin:6px 0 8px 0;">{text}</div>'
    )
