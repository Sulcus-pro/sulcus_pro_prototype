"""
sulcus.storyline
================

Defines what the Generative Canvas asserts at each tick of the simulation.

Each tick produces a fully-typed ``GenerativeCanvas`` (calendar + predictive
pre-mortem alerts + click-to-execute actions). The ``claims`` carried by each
alert/calendar are the canonical assertions that Gate 2 grounds back against the
raw ingestion corpus -- so the storyline and the evaluation loop stay coupled.
"""

from __future__ import annotations

from .schemas import (
    ActionButton,
    CalendarAsset,
    GenerativeCanvas,
    PreMortemAlert,
    Severity,
    StatusTag,
)

TOTAL_TICKS = 3  # ticks 0, 1, 2

TICK_TITLES = {
    0: "The Ideal Plan",
    1: "The Hidden Crisis",
    2: "The Strategic Pivot & Circadian Cycle",
}


def canvas_for_tick(tick: int) -> GenerativeCanvas:
    """Build the validated generative-UI payload for a given tick."""

    if tick <= 0:
        return GenerativeCanvas(
            tick=0,
            calendar=CalendarAsset(
                title="Feature Launch v1.0",
                iso_date="2026-07-03",
                human_date="This Friday",
                status=StatusTag.ON_TRACK,
                payment_rail="Stripe API",
                note="Checkout flow shipping via Stripe webhooks.",
            ),
            alerts=[
                PreMortemAlert(
                    headline="No risks detected",
                    severity=Severity.INFO,
                    detail=(
                        "Communication, execution and operations feeds are mutually "
                        "consistent. Launch is grounded in the active knowledge graph."
                    ),
                    claims=[
                        "launch is scheduled for friday",
                        "checkout uses the stripe api",
                        "milestone status is on track",
                    ],
                    likelihood="Low",
                    impact="Low",
                )
            ],
            actions=[],
        )

    if tick == 1:
        return GenerativeCanvas(
            tick=1,
            # The calendar has NOT updated yet -- the PM milestone still says
            # Friday/On Track even though the codebase now contradicts it. This
            # stale claim is exactly what Gate 2 will flag as informational drift.
            calendar=CalendarAsset(
                title="Feature Launch v1.0",
                iso_date="2026-07-03",
                human_date="This Friday",
                status=StatusTag.ON_TRACK,
                payment_rail="Stripe API",
                note="Milestone unchanged — but execution feed is now diverging.",
            ),
            alerts=[
                PreMortemAlert(
                    headline="Predictive Pre-Mortem: implementation contradicts milestone",
                    severity=Severity.HIGH,
                    detail=(
                        "GitHub execution feed reports Stripe webhooks failing with a "
                        "500 token-mismatch error, while the PM milestone still asserts "
                        "a Friday launch on the Stripe API. The plan and the code have "
                        "silently diverged."
                    ),
                    claims=[
                        "stripe webhooks are failing",
                        "code implementation contradicts the friday milestone",
                    ],
                    likelihood="High",
                    impact="High",
                )
            ],
            actions=[
                ActionButton(
                    key="act_open_incident",
                    label="Open Incident on CHK-41",
                    toast="Incident opened against Jira CHK-41 (Stripe webhooks).",
                    audit_action="Opened incident on CHK-41 from pre-mortem alert",
                ),
                ActionButton(
                    key="act_ping_dev",
                    label="Ping Bob for ETA",
                    toast="Drafted a Slack message to Bob requesting a fix ETA.",
                    audit_action="Drafted Slack message to Bob (Dev) requesting ETA",
                ),
            ],
        )

    # tick >= 2 -- the strategic pivot, post circadian consolidation.
    return GenerativeCanvas(
        tick=2,
        calendar=CalendarAsset(
            title="Feature Launch v1.0",
            iso_date="2026-07-07",
            human_date="Next Tuesday",
            status=StatusTag.DELAYED,
            payment_rail="Stripe bypassed",
            note="Knowledge graph rewritten by the circadian loop to settle on Tuesday.",
        ),
        alerts=[
            PreMortemAlert(
                headline="Downstream risk: $50K campaign blind spot",
                severity=Severity.CRITICAL,
                detail=(
                    "Delaying launch to Tuesday creates a 24-hour blind spot for the "
                    "$50,000 LinkedIn marketing campaign locked to fire Monday morning. "
                    "The campaign is gated on a live checkout that will not exist yet."
                ),
                claims=[
                    "launch is delayed to tuesday",
                    "stripe is bypassed",
                    "a $50,000 linkedin campaign is locked for monday",
                    "the delay creates a 24-hour campaign blind spot",
                ],
                likelihood="High",
                impact="High",
            )
        ],
        actions=[
            ActionButton(
                key="act_sync_jira",
                label="Sync Jira to Tuesday",
                toast="Jira CHK-41 due date synced to Next Tuesday (2026-07-07).",
                audit_action="Synced Jira CHK-41 milestone to Tuesday 2026-07-07",
            ),
            ActionButton(
                key="act_draft_slack",
                label="Draft Automated Slack Warning",
                toast="Drafted automated Slack warning to Growth about the campaign lock.",
                audit_action="Drafted automated Slack warning to Carol (Growth) re: $50K lock",
            ),
            ActionButton(
                key="act_hold_campaign",
                label="Request 24h Campaign Hold",
                toast="Requested a 24-hour hold on the LinkedIn campaign.",
                audit_action="Requested 24h hold on LinkedIn campaign:linkedin-q3",
            ),
        ],
    )
