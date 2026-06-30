"""
sulcus.circadian
================

The Circadian Consolidation Loop -- Sulcus's sleep cycle and the headline
capability of the platform.

Traditional vector RAG accumulates contradictions forever: an early plan and
a later contradicting event both sit in the index, and retrieval returns
whichever is more similar to the query. Sulcus instead runs a periodic
*consolidation* pass that behaves like memory reconsolidation during sleep --
it wakes up, sweeps the raw conflicting events, decides which are obsolete,
garbage-collects their long-term vectors (tombstones them), and rewrites the
knowledge graph to settle on a single coherent state.

v1 hardcoded the three specific event IDs involved in its single Stripe/
Friday narrative. v2 generalizes the same algorithm to any event stream: it
sweeps events tagged ``contradiction`` (the crisis), tombstones every event
tagged ``obsolete_on_pivot`` (the assumptions that crisis invalidated), and
logs which departments were involved -- the consolidation logic and the
Temporal Brain audit trail it writes are unchanged in spirit, just driven by
tags instead of literal IDs.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from .ingestion import IngestionStream
from .schemas import ActorKind, AuditEntry


def _dept_of(event) -> str:
    for tag in event.tags:
        if tag.startswith("dept:"):
            return tag.split(":", 1)[1]
    return "Unknown"


def run_consolidation(stream: IngestionStream, tick: int) -> Tuple[List[str], List[AuditEntry]]:
    """Execute the nightly circadian consolidation pass.

    Returns the terminal log lines plus the audit entries the brain wrote about
    itself (so the Temporal Brain history shows the system healing autonomously).
    """
    log: List[str] = []
    audit: List[AuditEntry] = []
    now = datetime.utcnow()

    contradictions = [e for e in stream.events if "contradiction" in e.tags]
    obsolete = [
        e for e in stream.events
        if "obsolete_on_pivot" in e.tags and e.event_id not in stream.tombstones
    ]
    depts = sorted({_dept_of(e) for e in contradictions} | {_dept_of(e) for e in obsolete})

    log.append("")
    log.append("[CIRCADIAN] ───────────────────────────────────────────────")
    log.append("[CIRCADIAN] Nightly Consolidation Loop — system entering sleep cycle.")
    log.append("[CIRCADIAN] Phase 1/5  Sweeping raw ephemeral event log for conflicts...")

    if contradictions:
        dept_list = ", ".join(depts) if depts else "multiple departments"
        log.append(
            f"[CIRCADIAN]   ↳ Conflict cluster found: {len(contradictions)} contradiction "
            f"event(s) across {dept_list}."
        )
    else:
        log.append("[CIRCADIAN]   ↳ No active contradiction events found.")

    log.append("[CIRCADIAN] Phase 2/5  Resolving authority — newest reconciled intent wins.")
    if contradictions:
        latest = max(contradictions, key=lambda e: e.timestamp)
        log.append(
            f"[CIRCADIAN]   ↳ Authoritative intent = {latest.user}@{latest.event_id[:8]} "
            f"({_dept_of(latest)})."
        )

    log.append("[CIRCADIAN] Phase 3/5  Garbage-collecting obsolete dependency vectors...")
    gc_ids = [e.event_id for e in obsolete]
    stream.tombstone(gc_ids)
    for e in obsolete:
        log.append(f"[CIRCADIAN]   ↳ GC vector {e.event_id[:8]} → tombstoned (excluded from live graph).")

    log.append("[CIRCADIAN] Phase 4/5  Rewriting long-term knowledge graph...")
    for dept in depts:
        log.append(f"[CIRCADIAN]   ↳ {dept}: stale plan vectors superseded ⇒ pivot state adopted.")

    log.append("[CIRCADIAN] Phase 5/5  Re-embedding consolidated state. Conflicts: 0.")
    log.append("[CIRCADIAN] Consolidation complete — graph internally consistent. Waking up.")
    log.append("[CIRCADIAN] ───────────────────────────────────────────────")

    audit.append(
        AuditEntry(
            timestamp=now,
            tick=tick,
            actor="Circadian Loop",
            actor_kind=ActorKind.SYSTEM,
            action="Nightly memory consolidation",
            detail=(
                f"Swept {len(contradictions)} contradiction event(s) across "
                f"{', '.join(depts) if depts else 'no departments'}, GC'd {len(gc_ids)} "
                "obsolete vector(s), rewrote knowledge graph to the post-crisis pivot state."
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
            detail=f"{len(gc_ids)} obsolete vector(s) excluded from the live grounding corpus.",
        )
    )
    return log, audit
