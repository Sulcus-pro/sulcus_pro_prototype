"""
sulcus.storyline
================

Builds the validated Generative Canvas for a given tick.

v1 hardcoded three fixed ticks of a single Stripe/Friday narrative. v2 builds
the canvas dynamically from whatever NovaCorp events actually landed in the
``IngestionStream`` for that tick -- the calendar headline, the pre-mortem
alerts and their grounding ``claims`` are all derived from real event text,
so Gate 2 keeps grounding against genuine data instead of a scripted plot.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import List

from .ingestion import IngestionStream
from .schemas import (
    CalendarAsset,
    GenerativeCanvas,
    PreMortemAlert,
    Severity,
    StatusTag,
)

TOTAL_TICKS = 10  # ticks 0-9

TICK_TITLES = {
    0: "Normal Operations — Plans in Motion",
    1: "Steady State",
    2: "Early Signals",
    3: "Problems Emerging",
    4: "Mounting Pressure",
    5: "Blockers Surface",
    6: "Crisis",
    7: "Crisis Peaks",
    8: "Strategic Pivot & Circadian Consolidation",
    9: "Resolution",
}

# Tick 0 maps to June 30, 2026; each subsequent tick advances one calendar day.
_TICK_EPOCH = date(2026, 6, 30)

_RISK_SEVERITY = {
    "low": Severity.INFO,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}

_RISK_STATUS = {
    "low": StatusTag.ON_TRACK,
    "medium": StatusTag.ON_TRACK,
    "high": StatusTag.AT_RISK,
    "critical": StatusTag.DELAYED,
}


def date_for_tick(tick: int) -> date:
    """Tick 0 = June 30 2026, tick N = June 30 + N days."""
    return _TICK_EPOCH + timedelta(days=tick)


def _risk_of(event) -> str:
    for tag in event.tags:
        if tag.startswith("risk:"):
            return tag.split(":", 1)[1]
    return "low"


def _department_of(event) -> str:
    for tag in event.tags:
        if tag.startswith("dept:"):
            return tag.split(":", 1)[1]
    return "NovaCorp"


def _claims_for(event) -> List[str]:
    """Short grounded claims derived directly from the event's own text."""
    dept = _department_of(event)
    return [event.text.lower(), f"reported by {dept.lower()}"]


def canvas_for_tick(tick: int, stream: IngestionStream) -> GenerativeCanvas:
    """Build the validated generative-UI payload for a given tick from real events."""

    this_tick_events = [e for e in stream.active_events() if e.tick == tick]
    pool = this_tick_events or stream.active_events()[-5:]

    d = date_for_tick(tick)
    iso = d.isoformat()
    human = f"{d.strftime('%A, %B')} {d.day}"

    if not pool:
        calendar = CalendarAsset(
            title="NovaCorp Operations",
            iso_date=iso,
            human_date=human,
            status=StatusTag.ON_TRACK,
            payment_rail="n/a",
            note="No events ingested yet for this tick.",
        )
        return GenerativeCanvas(tick=tick, calendar=calendar, alerts=[], actions=[])

    # Headline = the highest-risk event this tick (ties broken by order).
    risk_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    headline_event = max(pool, key=lambda e: risk_rank.get(_risk_of(e), 0))
    risk = _risk_of(headline_event)
    dept = _department_of(headline_event)

    calendar = CalendarAsset(
        title=f"{dept}: {headline_event.text[:72]}",
        iso_date=iso,
        human_date=human,
        status=_RISK_STATUS.get(risk, StatusTag.ON_TRACK),
        payment_rail=headline_event.channel,
        note=f"Tick {tick} headline event reported via {headline_event.channel}.",
    )

    alerts: List[PreMortemAlert] = []
    high_risk_events = [e for e in pool if _risk_of(e) in ("high", "critical")]
    for e in high_risk_events[:3]:
        sev = _RISK_SEVERITY.get(_risk_of(e), Severity.MEDIUM)
        alerts.append(
            PreMortemAlert(
                headline=f"{_department_of(e)}: {e.text[:90]}",
                severity=sev,
                detail=e.text,
                claims=_claims_for(e),
                likelihood="High" if sev == Severity.CRITICAL else "Medium",
                impact="High" if sev in (Severity.CRITICAL, Severity.HIGH) else "Medium",
            )
        )

    if not alerts:
        alerts.append(
            PreMortemAlert(
                headline="No elevated risks detected this tick",
                severity=Severity.INFO,
                detail="All department feeds are reporting low or medium risk activity.",
                claims=[e.text.lower() for e in pool[:3]],
                likelihood="Low",
                impact="Low",
            )
        )

    return GenerativeCanvas(tick=tick, calendar=calendar, alerts=alerts, actions=[])
