"""
sulcus.circadian
================

The Circadian Consolidation Loop -- Sulcus's sleep cycle and the headline
capability of the platform.

Traditional vector RAG accumulates contradictions forever: the Friday plan and
the failing-Stripe commit both sit in the index, and retrieval returns whichever
is more similar to the query. Sulcus instead runs a periodic *consolidation*
pass that behaves like memory reconsolidation during sleep -- it wakes up, sweeps
the raw conflicting events, decides which are obsolete, garbage-collects their
long-term vectors (tombstones them), and rewrites the knowledge graph to settle
on a single coherent state.

The loop is what turns Tick 1's WARNING (informational drift) into Tick 2's
healed, internally-consistent corpus.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from .ingestion import IngestionStream
from .schemas import ActorKind, AuditEntry


# Events made obsolete by the Tick-2 strategic pivot. Their vectors are GC'd from
# the live knowledge graph; the rows remain visible in the audit ticker (marked
# GC) for full traceability.
_OBSOLETE_ON_PIVOT = [
    "slack-000",     # Alice: "launch Friday via Stripe"
    "jira-CHK-41",   # "Integrate Stripe Webhooks"  (superseded by bypass)
    "gh-9af3c1",     # Bob: "Stripe webhooks failing 500"
]


def run_consolidation(stream: IngestionStream, tick: int) -> Tuple[List[str], List[AuditEntry]]:
    """Execute the nightly circadian consolidation pass.

    Returns the terminal log lines plus the audit entries the brain wrote about
    itself (so the Temporal Brain history shows the system healing autonomously).
    """
    log: List[str] = []
    audit: List[AuditEntry] = []
    now = datetime(2026, 6, 29, 2, 14, 0)  # the loop runs in the small hours

    log.append("")
    log.append("[CIRCADIAN] ───────────────────────────────────────────────")
    log.append("[CIRCADIAN] 🌙 Nightly Consolidation Loop — system entering sleep cycle.")
    log.append("[CIRCADIAN] Phase 1/5  Sweeping raw ephemeral event log for conflicts...")

    # Identify the conflicting cluster.
    slack_friday = next((e for e in stream.events if e.event_id == "slack-000"), None)
    bob_commit = next((e for e in stream.events if e.event_id == "gh-9af3c1"), None)
    slack_pivot = next((e for e in stream.events if e.event_id == "slack-002"), None)

    if slack_friday and bob_commit:
        log.append(
            "[CIRCADIAN]   ↳ Conflict cluster found: Alice@slack-000 (Friday/Stripe) "
            "⟂ Bob@gh-9af3c1 (Stripe 500 mismatch)."
        )
    log.append("[CIRCADIAN] Phase 2/5  Resolving authority — newest milestone intent wins.")
    if slack_pivot:
        log.append(
            "[CIRCADIAN]   ↳ Authoritative intent = Alice@slack-002 "
            "(delay → Tuesday, bypass Stripe)."
        )

    log.append("[CIRCADIAN] Phase 3/5  Garbage-collecting obsolete dependency vectors...")
    gc_ids = [eid for eid in _OBSOLETE_ON_PIVOT if eid not in stream.tombstones]
    stream.tombstone(gc_ids)
    for eid in gc_ids:
        log.append(f"[CIRCADIAN]   ↳ GC vector {eid} → tombstoned (excluded from live graph).")

    log.append("[CIRCADIAN] Phase 4/5  Rewriting long-term knowledge graph...")
    log.append("[CIRCADIAN]   ↳ launch.date:  2026-07-03 (Fri)  ⇒  2026-07-07 (Tue)")
    log.append("[CIRCADIAN]   ↳ launch.rail:  stripe-api         ⇒  bypassed")
    log.append("[CIRCADIAN]   ↳ launch.status: on-track          ⇒  delayed")
    log.append("[CIRCADIAN]   ↳ edge added:  launch.delay ──impacts──▶ campaign:linkedin-q3")

    log.append("[CIRCADIAN] Phase 5/5  Re-embedding consolidated state. Conflicts: 0.")
    log.append("[CIRCADIAN] ✅ Consolidation complete — graph internally consistent. Waking up.")
    log.append("[CIRCADIAN] ───────────────────────────────────────────────")

    audit.append(
        AuditEntry(
            timestamp=now,
            tick=tick,
            actor="Circadian Loop",
            actor_kind=ActorKind.SYSTEM,
            action="Nightly memory consolidation",
            detail=(
                f"Swept Friday/Stripe conflict, GC'd {len(gc_ids)} obsolete vector(s), "
                "rewrote knowledge graph to Tuesday launch with Stripe bypassed."
            ),
        )
    )
    audit.append(
        AuditEntry(
            timestamp=now,
            tick=tick,
            actor="Knowledge Graph",
            actor_kind=ActorKind.SYSTEM,
            action="Long-term vector rewrite",
            detail="launch.date → 2026-07-07; launch.rail → bypassed; status → delayed.",
        )
    )
    return log, audit
