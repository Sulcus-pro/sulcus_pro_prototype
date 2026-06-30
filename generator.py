"""
generator.py
============

Standalone NovaCorp event generator for Sulcus.pro.

Run once to seed a realistic 10-tick (0-9) operational story arc across all
8 NovaCorp departments:

    python generator.py

Run in scheduled mode to keep inserting new "live" events every 5 minutes,
simulating an organization that never stops generating signal:

    python generator.py --schedule

This script talks to Supabase directly via ``supabase_client.py`` and never
imports Streamlit, so it can run independently of the app (e.g. in a cron job
or a background worker).
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from typing import List, TypedDict

from supabase_client import get_supabase_client

DEPARTMENTS = [
    "Engineering", "Product", "Sales", "Marketing",
    "Finance", "HR", "Legal", "DevOps",
]

ACTORS = {
    "Engineering": ["Sarah Chen, VP Engineering", "Marcus Webb, Staff Engineer", "Priya Nair, SRE"],
    "Product": ["James Okafor, CPO", "Lily Tan, Senior PM", "Dev Patel, PM"],
    "Sales": ["Rachel Torres, VP Sales", "Kevin Park, AE", "Mia Johnson, SDR"],
    "Marketing": ["Tom Bradley, CMO", "Ananya Rao, Growth Lead"],
    "Finance": ["Diana Frost, CFO", "Neil Sharma, FP&A"],
    "HR": ["Carmen Vela, CHRO", "Jake Wu, Recruiter"],
    "Legal": ["Olivia Marsh, General Counsel"],
    "DevOps": ["Chris Adeyemi, DevOps Lead", "Sam Rivera, SRE"],
}

SOURCES = {
    "Engineering": ["github", "jira", "slack", "pagerduty", "datadog"],
    "Product": ["jira", "confluence", "figma", "slack", "notion"],
    "Sales": ["salesforce", "gmail", "outlook", "slack"],
    "Marketing": ["slack", "notion", "gmail", "figma"],
    "Finance": ["outlook", "gmail", "notion", "slack"],
    "HR": ["workday", "outlook", "slack"],
    "Legal": ["outlook", "gmail", "notion"],
    "DevOps": ["pagerduty", "datadog", "github", "slack"],
}


class EventRow(TypedDict):
    department: str
    source: str
    actor: str
    content: str
    risk_level: str
    risk_reason: str
    tick: int
    tags: List[str]


# --------------------------------------------------------------------------- #
# The story arc: NovaCorp's "Helios" enterprise-tier launch.
#   Ticks 0-2  Normal operations, plans being made.
#   Ticks 3-5  Problems emerging (incidents, missed targets, blockers).
#   Ticks 6-7  Crisis (critical risk events, cross-department conflict).
#   Ticks 8-9  Resolution and pivot.
# --------------------------------------------------------------------------- #
EVENTS: List[EventRow] = [
    # ---------------------------------------------------------------- Engineering
    {"department": "Engineering", "source": "jira", "actor": "Sarah Chen, VP Engineering",
     "content": "Sprint planning: Helios enterprise-tier API gateway scoped for the July 10 release.",
     "risk_level": "low", "risk_reason": "Standard sprint planning, no anomalies detected.",
     "tick": 0, "tags": ["planning", "milestone"]},
    {"department": "Engineering", "source": "github", "actor": "Marcus Webb, Staff Engineer",
     "content": "Merged PR #482: rate-limiting middleware for the Helios API gateway.",
     "risk_level": "low", "risk_reason": "Routine merge, passed CI and code review.",
     "tick": 1, "tags": ["execution"]},
    {"department": "Engineering", "source": "slack", "actor": "Sarah Chen, VP Engineering",
     "content": "Helios is on track for July 10 — all services green in staging.",
     "risk_level": "low", "risk_reason": "Status update consistent with current plan.",
     "tick": 2, "tags": ["milestone", "obsolete_on_pivot"]},
    {"department": "Engineering", "source": "datadog", "actor": "Priya Nair, SRE",
     "content": "p99 latency on the auth service climbed 40% after the last deploy; investigating.",
     "risk_level": "medium", "risk_reason": "Latency regression with no confirmed customer impact yet.",
     "tick": 3, "tags": ["incident"]},
    {"department": "Engineering", "source": "pagerduty", "actor": "Marcus Webb, Staff Engineer",
     "content": "Page fired: checkout-service error rate above the 5% threshold, auto-escalated.",
     "risk_level": "high", "risk_reason": "Customer-facing error rate breach on a revenue path.",
     "tick": 4, "tags": ["incident"]},
    {"department": "Engineering", "source": "github", "actor": "Marcus Webb, Staff Engineer",
     "content": "Root cause found: connection pool exhaustion tied to the new Helios gateway; rollback in progress.",
     "risk_level": "high", "risk_reason": "Confirmed regression traced directly to the Helios release.",
     "tick": 5, "tags": ["incident", "execution"]},
    {"department": "Engineering", "source": "pagerduty", "actor": "Priya Nair, SRE",
     "content": "Critical: full checkout-service outage, 100% error rate, primary cloud region degraded.",
     "risk_level": "critical", "risk_reason": "Total outage of a revenue-critical path during business hours.",
     "tick": 6, "tags": ["contradiction", "incident"]},
    {"department": "Engineering", "source": "slack", "actor": "Sarah Chen, VP Engineering",
     "content": "Engineering is declaring SEV-1. All hands paging in to stabilize checkout.",
     "risk_level": "critical", "risk_reason": "Organization-wide incident response now active.",
     "tick": 7, "tags": ["incident"]},
    {"department": "Engineering", "source": "github", "actor": "Marcus Webb, Staff Engineer",
     "content": "Helios gateway rollback complete; checkout-service error rate back to baseline.",
     "risk_level": "medium", "risk_reason": "Mitigation deployed, monitoring for recurrence.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "Engineering", "source": "jira", "actor": "Sarah Chen, VP Engineering",
     "content": "Postmortem filed; Helios re-scheduled for July 17 with a canary rollout plan.",
     "risk_level": "low", "risk_reason": "Incident closed with a documented remediation plan.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # ------------------------------------------------------------------- Product
    {"department": "Product", "source": "confluence", "actor": "Lily Tan, Senior PM",
     "content": "Published the Helios enterprise-tier PRD, target GA July 10.",
     "risk_level": "low", "risk_reason": "Standard planning artifact, no open risks.",
     "tick": 0, "tags": ["planning", "obsolete_on_pivot"]},
    {"department": "Product", "source": "figma", "actor": "Dev Patel, PM",
     "content": "Shared updated onboarding flow mockups for the Helios admin console.",
     "risk_level": "low", "risk_reason": "Design iteration, no schedule impact.",
     "tick": 1, "tags": ["design"]},
    {"department": "Product", "source": "jira", "actor": "James Okafor, CPO",
     "content": "Helios scope locked: no further feature additions before GA.",
     "risk_level": "low", "risk_reason": "Scope freeze reduces delivery risk.",
     "tick": 2, "tags": ["milestone"]},
    {"department": "Product", "source": "notion", "actor": "Lily Tan, Senior PM",
     "content": "Beta customer feedback flags a confusing permission model in the Helios admin console.",
     "risk_level": "medium", "risk_reason": "Usability issue surfaced by real beta usage.",
     "tick": 3, "tags": ["feedback"]},
    {"department": "Product", "source": "slack", "actor": "Dev Patel, PM",
     "content": "Three enterprise beta customers report onboarding drop-off above 30%.",
     "risk_level": "high", "risk_reason": "Drop-off rate threatens enterprise adoption of the new tier.",
     "tick": 4, "tags": ["feedback"]},
    {"department": "Product", "source": "jira", "actor": "James Okafor, CPO",
     "content": "Pausing Helios GA pending Engineering's outage resolution.",
     "risk_level": "critical", "risk_reason": "Launch decision now blocked by a live production incident.",
     "tick": 6, "tags": ["contradiction"]},
    {"department": "Product", "source": "confluence", "actor": "Lily Tan, Senior PM",
     "content": "Revised Helios rollout plan: phased GA starting with 10% of accounts.",
     "risk_level": "medium", "risk_reason": "Lower-risk staged rollout replaces the original big-bang launch.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "Product", "source": "notion", "actor": "James Okafor, CPO",
     "content": "Product and Engineering aligned on the July 17 canary GA date.",
     "risk_level": "low", "risk_reason": "Cross-functional plan reconciled, no open conflicts.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # --------------------------------------------------------------------- Sales
    {"department": "Sales", "source": "salesforce", "actor": "Kevin Park, AE",
     "content": "Meridian Health enterprise deal ($340K ARR) moved to final legal review.",
     "risk_level": "low", "risk_reason": "Deal progressing normally through the pipeline.",
     "tick": 0, "tags": ["pipeline"]},
    {"department": "Sales", "source": "gmail", "actor": "Rachel Torres, VP Sales",
     "content": "Q3 pipeline tracking 12% ahead of target.",
     "risk_level": "low", "risk_reason": "Pipeline coverage healthy relative to quota.",
     "tick": 1, "tags": ["pipeline"]},
    {"department": "Sales", "source": "outlook", "actor": "Mia Johnson, SDR",
     "content": "Booked 14 new discovery calls this week, strong top-of-funnel.",
     "risk_level": "low", "risk_reason": "Lead generation within normal range.",
     "tick": 2, "tags": ["pipeline"]},
    {"department": "Sales", "source": "salesforce", "actor": "Kevin Park, AE",
     "content": "Meridian Health is requesting the Helios enterprise tier as a contract condition.",
     "risk_level": "medium", "risk_reason": "Deal now depends on an unreleased product tier.",
     "tick": 3, "tags": ["dependency", "obsolete_on_pivot"]},
    {"department": "Sales", "source": "slack", "actor": "Rachel Torres, VP Sales",
     "content": "Two more enterprise prospects are gating signature on the Helios GA date.",
     "risk_level": "medium", "risk_reason": "Multiple deals now dependent on the same launch date.",
     "tick": 4, "tags": ["dependency"]},
    {"department": "Sales", "source": "gmail", "actor": "Kevin Park, AE",
     "content": "Meridian Health legal is pausing signature, citing uncertainty after outage news leaked.",
     "risk_level": "critical", "risk_reason": "Largest active deal directly threatened by the production incident.",
     "tick": 6, "tags": ["contradiction"]},
    {"department": "Sales", "source": "salesforce", "actor": "Rachel Torres, VP Sales",
     "content": "$340K Meridian Health deal flagged at-risk in the pipeline review.",
     "risk_level": "critical", "risk_reason": "Material revenue at risk this quarter.",
     "tick": 7, "tags": ["pipeline"]},
    {"department": "Sales", "source": "outlook", "actor": "Rachel Torres, VP Sales",
     "content": "Meridian Health agreed to extend the signature deadline two weeks given the new GA commitment.",
     "risk_level": "medium", "risk_reason": "Deal stabilized but still pending signature.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "Sales", "source": "salesforce", "actor": "Kevin Park, AE",
     "content": "Meridian Health deal moved back to commit-stage; signature expected next week.",
     "risk_level": "low", "risk_reason": "Deal recovered, back on track to close.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # ----------------------------------------------------------------- Marketing
    {"department": "Marketing", "source": "notion", "actor": "Ananya Rao, Growth Lead",
     "content": "Helios launch campaign brief finalized, targeting the July 10 announcement.",
     "risk_level": "low", "risk_reason": "Campaign plan aligned with current launch date.",
     "tick": 0, "tags": ["planning", "obsolete_on_pivot"]},
    {"department": "Marketing", "source": "figma", "actor": "Ananya Rao, Growth Lead",
     "content": "Shared launch landing page designs for the Helios enterprise tier.",
     "risk_level": "low", "risk_reason": "Design iteration, no schedule impact.",
     "tick": 1, "tags": ["design"]},
    {"department": "Marketing", "source": "slack", "actor": "Tom Bradley, CMO",
     "content": "Press embargo set for July 9, briefing three trade outlets.",
     "risk_level": "low", "risk_reason": "Standard press coordination, on schedule.",
     "tick": 2, "tags": ["planning"]},
    {"department": "Marketing", "source": "gmail", "actor": "Tom Bradley, CMO",
     "content": "An analyst at CloudWeekly is asking pointed questions about Helios reliability.",
     "risk_level": "medium", "risk_reason": "Early external signal of reliability concerns ahead of launch.",
     "tick": 3, "tags": ["press"]},
    {"department": "Marketing", "source": "slack", "actor": "Ananya Rao, Growth Lead",
     "content": "Paid campaign spend committed for the July 10 launch window, $85K budget locked.",
     "risk_level": "high", "risk_reason": "Significant spend now committed against an unconfirmed launch date.",
     "tick": 5, "tags": ["budget", "obsolete_on_pivot"]},
    {"department": "Marketing", "source": "notion", "actor": "Tom Bradley, CMO",
     "content": "Pausing all paid launch campaign spend pending Engineering's outage resolution.",
     "risk_level": "critical", "risk_reason": "Campaign spend frozen due to a live production incident.",
     "tick": 6, "tags": ["contradiction"]},
    {"department": "Marketing", "source": "figma", "actor": "Ananya Rao, Growth Lead",
     "content": "Campaign creative reworked for the July 17 phased GA messaging.",
     "risk_level": "medium", "risk_reason": "Creative now aligned with the revised launch plan.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "Marketing", "source": "slack", "actor": "Tom Bradley, CMO",
     "content": "Press embargo reset to July 16, trade outlets re-briefed.",
     "risk_level": "low", "risk_reason": "Press plan realigned with the new launch date.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # ------------------------------------------------------------------- Finance
    {"department": "Finance", "source": "notion", "actor": "Neil Sharma, FP&A",
     "content": "Q3 forecast model updated with Helios enterprise-tier revenue assumptions.",
     "risk_level": "low", "risk_reason": "Routine forecast update.",
     "tick": 0, "tags": ["planning"]},
    {"department": "Finance", "source": "outlook", "actor": "Diana Frost, CFO",
     "content": "Board deck draft circulated ahead of Thursday's Q3 review.",
     "risk_level": "low", "risk_reason": "Standard board cadence, no open issues.",
     "tick": 1, "tags": ["reporting"]},
    {"department": "Finance", "source": "gmail", "actor": "Neil Sharma, FP&A",
     "content": "Burn rate tracking within plan, 14 months of runway at current spend.",
     "risk_level": "low", "risk_reason": "Spend within approved budget.",
     "tick": 2, "tags": ["reporting"]},
    {"department": "Finance", "source": "slack", "actor": "Diana Frost, CFO",
     "content": "Flagging cloud infrastructure spend 22% over budget this month.",
     "risk_level": "medium", "risk_reason": "Spend variance exceeds normal monthly tolerance.",
     "tick": 4, "tags": ["budget"]},
    {"department": "Finance", "source": "outlook", "actor": "Neil Sharma, FP&A",
     "content": "Incident response and emergency cloud scaling costs estimated at $60K this week.",
     "risk_level": "high", "risk_reason": "Unplanned spend directly tied to the production incident.",
     "tick": 6, "tags": ["contradiction", "budget"]},
    {"department": "Finance", "source": "notion", "actor": "Diana Frost, CFO",
     "content": "Revising Q3 forecast down 4% pending Meridian Health and other at-risk deals.",
     "risk_level": "high", "risk_reason": "Revenue forecast directly exposed to at-risk pipeline.",
     "tick": 7, "tags": ["forecast"]},
    {"department": "Finance", "source": "gmail", "actor": "Diana Frost, CFO",
     "content": "Emergency spend approved and contained; Q3 forecast revision limited to 2%.",
     "risk_level": "medium", "risk_reason": "Financial impact contained after mitigation.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "Finance", "source": "outlook", "actor": "Neil Sharma, FP&A",
     "content": "Updated board deck reflects a stabilized Q3 outlook with the phased Helios GA.",
     "risk_level": "low", "risk_reason": "Forecast restabilized after the incident resolved.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # ----------------------------------------------------------------------- HR
    {"department": "HR", "source": "workday", "actor": "Jake Wu, Recruiter",
     "content": "Two senior SRE reqs opened to support Helios launch scaling.",
     "risk_level": "low", "risk_reason": "Routine headcount planning.",
     "tick": 0, "tags": ["hiring"]},
    {"department": "HR", "source": "outlook", "actor": "Carmen Vela, CHRO",
     "content": "Quarterly engagement survey results reviewed, scores stable.",
     "risk_level": "low", "risk_reason": "No material change in engagement metrics.",
     "tick": 1, "tags": ["engagement"]},
    {"department": "HR", "source": "slack", "actor": "Jake Wu, Recruiter",
     "content": "Strong candidate pipeline for SRE roles, three offers extended this week.",
     "risk_level": "low", "risk_reason": "Hiring pipeline healthy.",
     "tick": 2, "tags": ["hiring"]},
    {"department": "HR", "source": "workday", "actor": "Carmen Vela, CHRO",
     "content": "Engineering on-call rotation flagged for burnout risk amid rising incident volume.",
     "risk_level": "medium", "risk_reason": "Sustained incident load creating team health risk.",
     "tick": 4, "tags": ["wellbeing"]},
    {"department": "HR", "source": "slack", "actor": "Carmen Vela, CHRO",
     "content": "Coordinating mental health and overtime support for Engineering during the SEV-1 response.",
     "risk_level": "high", "risk_reason": "Active incident response is straining the on-call team.",
     "tick": 6, "tags": ["contradiction", "wellbeing"]},
    {"department": "HR", "source": "outlook", "actor": "Jake Wu, Recruiter",
     "content": "Pausing new offer extensions until the headcount plan is reconfirmed post-incident.",
     "risk_level": "medium", "risk_reason": "Hiring plan paused pending budget reconfirmation.",
     "tick": 7, "tags": ["hiring"]},
    {"department": "HR", "source": "workday", "actor": "Carmen Vela, CHRO",
     "content": "Overtime and wellness support plan closed out, no attrition risk identified.",
     "risk_level": "low", "risk_reason": "Team health risk resolved after incident closure.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "HR", "source": "slack", "actor": "Jake Wu, Recruiter",
     "content": "SRE offers reinstated, two candidates accepted for an October start.",
     "risk_level": "low", "risk_reason": "Hiring plan back on track.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # -------------------------------------------------------------------- Legal
    {"department": "Legal", "source": "outlook", "actor": "Olivia Marsh, General Counsel",
     "content": "Meridian Health MSA redlines returned, minor liability cap negotiation remaining.",
     "risk_level": "low", "risk_reason": "Standard contract negotiation in progress.",
     "tick": 0, "tags": ["contract"]},
    {"department": "Legal", "source": "gmail", "actor": "Olivia Marsh, General Counsel",
     "content": "Standard enterprise DPA template approved for Helios-tier customers.",
     "risk_level": "low", "risk_reason": "Routine compliance approval.",
     "tick": 1, "tags": ["compliance"]},
    {"department": "Legal", "source": "notion", "actor": "Olivia Marsh, General Counsel",
     "content": "No open compliance items blocking Helios GA.",
     "risk_level": "low", "risk_reason": "Compliance review clean ahead of launch.",
     "tick": 2, "tags": ["compliance"]},
    {"department": "Legal", "source": "outlook", "actor": "Olivia Marsh, General Counsel",
     "content": "Reviewing customer notification obligations following the checkout-service outage.",
     "risk_level": "high", "risk_reason": "Incident may trigger contractual notification requirements.",
     "tick": 6, "tags": ["contradiction", "compliance"]},
    {"department": "Legal", "source": "gmail", "actor": "Olivia Marsh, General Counsel",
     "content": "Drafting incident disclosure language for affected enterprise accounts.",
     "risk_level": "high", "risk_reason": "Active legal exposure from the production incident.",
     "tick": 7, "tags": ["compliance"]},
    {"department": "Legal", "source": "notion", "actor": "Olivia Marsh, General Counsel",
     "content": "Incident disclosure sent to affected accounts, no SLA breach penalties triggered.",
     "risk_level": "medium", "risk_reason": "Disclosure completed without contractual penalty.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "Legal", "source": "outlook", "actor": "Olivia Marsh, General Counsel",
     "content": "Meridian Health MSA finalized with an updated SLA exhibit.",
     "risk_level": "low", "risk_reason": "Contract closed out cleanly.",
     "tick": 9, "tags": ["pivot", "resolution"]},

    # ------------------------------------------------------------------- DevOps
    {"department": "DevOps", "source": "github", "actor": "Chris Adeyemi, DevOps Lead",
     "content": "Infra-as-code review complete for Helios gateway autoscaling rules.",
     "risk_level": "low", "risk_reason": "Routine infrastructure review.",
     "tick": 0, "tags": ["infra"]},
    {"department": "DevOps", "source": "datadog", "actor": "Sam Rivera, SRE",
     "content": "Baseline dashboards configured for Helios gateway rollout monitoring.",
     "risk_level": "low", "risk_reason": "Standard observability setup.",
     "tick": 1, "tags": ["infra"]},
    {"department": "DevOps", "source": "pagerduty", "actor": "Chris Adeyemi, DevOps Lead",
     "content": "On-call schedule confirmed for launch week, no gaps.",
     "risk_level": "low", "risk_reason": "Coverage plan complete ahead of launch.",
     "tick": 2, "tags": ["planning"]},
    {"department": "DevOps", "source": "datadog", "actor": "Sam Rivera, SRE",
     "content": "Anomalous connection pool growth detected on the staging gateway cluster.",
     "risk_level": "medium", "risk_reason": "Early infrastructure signal ahead of the production incident.",
     "tick": 3, "tags": ["infra"]},
    {"department": "DevOps", "source": "pagerduty", "actor": "Chris Adeyemi, DevOps Lead",
     "content": "Primary cloud region showing elevated packet loss, vendor ticket opened.",
     "risk_level": "high", "risk_reason": "Infrastructure degradation outside NovaCorp's direct control.",
     "tick": 5, "tags": ["infra"]},
    {"department": "DevOps", "source": "datadog", "actor": "Sam Rivera, SRE",
     "content": "Cloud provider confirms regional network degradation, ETA unknown.",
     "risk_level": "critical", "risk_reason": "Vendor-confirmed regional outage with no resolution timeline.",
     "tick": 6, "tags": ["contradiction"]},
    {"department": "DevOps", "source": "github", "actor": "Chris Adeyemi, DevOps Lead",
     "content": "Failover to the secondary region executed, traffic rerouted.",
     "risk_level": "critical", "risk_reason": "Emergency failover in progress during the live incident.",
     "tick": 7, "tags": ["incident"]},
    {"department": "DevOps", "source": "pagerduty", "actor": "Sam Rivera, SRE",
     "content": "Vendor confirms the regional incident is resolved, failback to primary scheduled.",
     "risk_level": "medium", "risk_reason": "Vendor incident closed, failback still pending.",
     "tick": 8, "tags": ["pivot", "resolution"]},
    {"department": "DevOps", "source": "datadog", "actor": "Chris Adeyemi, DevOps Lead",
     "content": "All systems nominal, postmortem scheduled with the cloud vendor account team.",
     "risk_level": "low", "risk_reason": "Infrastructure fully recovered, follow-up scheduled.",
     "tick": 9, "tags": ["pivot", "resolution"]},
]


# --------------------------------------------------------------------------- #
# Live "schedule" mode content bank — generic, low/medium-risk chatter used to
# keep the demo feeling alive between manual seedings.
# --------------------------------------------------------------------------- #
_LIVE_TEMPLATES = [
    ("Engineering", "github", "Opened a follow-up PR to harden the checkout-service connection pool."),
    ("Engineering", "slack", "Standup note: no new regressions overnight, monitoring dashboards green."),
    ("Product", "notion", "Logged a new feature request from an enterprise beta customer."),
    ("Product", "jira", "Triaged backlog for the next sprint, three tickets reprioritized."),
    ("Sales", "salesforce", "Logged a new discovery call with a mid-market prospect."),
    ("Sales", "gmail", "Sent a follow-up proposal to an existing pipeline opportunity."),
    ("Marketing", "slack", "Drafted social copy for next week's product update."),
    ("Marketing", "notion", "Reviewed analytics on the latest landing page A/B test."),
    ("Finance", "outlook", "Reconciled monthly cloud spend against the approved budget."),
    ("HR", "workday", "Scheduled onboarding for a new hire starting next week."),
    ("Legal", "notion", "Reviewed a routine vendor contract renewal."),
    ("DevOps", "datadog", "Rotated on-call schedule for the upcoming week."),
]


def _random_live_event(tick: int) -> EventRow:
    department, source, content = random.choice(_LIVE_TEMPLATES)
    actor = random.choice(ACTORS[department])
    risk_level = random.choices(
        ["low", "medium", "high"], weights=[0.7, 0.25, 0.05]
    )[0]
    risk_reason = {
        "low": "Routine operational update, no follow-up required.",
        "medium": "Minor variance from plan, worth monitoring.",
        "high": "Notable deviation surfaced during routine live monitoring.",
    }[risk_level]
    return {
        "department": department,
        "source": source,
        "actor": actor,
        "content": content,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "tick": tick,
        "tags": ["live"],
    }


# --------------------------------------------------------------------------- #
def seed_events() -> None:
    """Insert the full 50+ event NovaCorp story arc into Supabase."""
    client = get_supabase_client()
    if client is None:
        print(
            "ERROR: Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "as environment variables or in .streamlit/secrets.toml before running.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Seeding {len(EVENTS)} events across {len(DEPARTMENTS)} departments...")
    client.table("events").insert(EVENTS).execute()
    print("Done. NovaCorp event stream seeded (ticks 0-9).")


def insert_live_batch(client) -> None:
    n = random.randint(2, 3)
    batch = [_random_live_event(tick=9) for _ in range(n)]
    client.table("events").insert(batch).execute()
    print(f"Inserted {n} live event(s).")


def run_schedule() -> None:
    """Insert 2-3 new live events every 5 minutes using APScheduler."""
    from apscheduler.schedulers.blocking import BlockingScheduler

    client = get_supabase_client()
    if client is None:
        print(
            "ERROR: Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "as environment variables or in .streamlit/secrets.toml before running.",
            file=sys.stderr,
        )
        sys.exit(1)

    scheduler = BlockingScheduler()
    scheduler.add_job(insert_live_batch, "interval", minutes=5, args=[client], next_run_time=None)
    print("Live mode started: inserting 2-3 new events every 5 minutes. Press Ctrl+C to stop.")
    insert_live_batch(client)  # seed one batch immediately
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Live mode stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="NovaCorp event generator for Sulcus.pro")
    parser.add_argument(
        "--schedule", action="store_true",
        help="Run continuously, inserting 2-3 new live events every 5 minutes.",
    )
    args = parser.parse_args()

    if args.schedule:
        run_schedule()
    else:
        seed_events()


if __name__ == "__main__":
    main()
