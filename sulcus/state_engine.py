"""
sulcus.state_engine
====================

The Evolving State Engine -- the storyline state machine.

Each call to :meth:`SulcusEngine.advance` performs one tick of the corporate
pivot:

    1. Poll every ingestion connector for the new tick and append events.
    2. If the tick is a consolidation tick, run the circadian loop (sweep,
       garbage-collect, rewrite the graph).
    3. Build the typed Generative Canvas for the new tick.
    4. Run both guardrail gates against it.
    5. Append audit entries to the Temporal Brain history.

The engine owns all mutable state. The Streamlit layer stores a single
``SulcusEngine`` in ``st.session_state`` and never mutates the world directly --
it only reads the engine's snapshot and calls ``advance()``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from .circadian import run_consolidation
from .guardrails import evaluate
from .ingestion import IngestionStream
from .schemas import (
    ActorKind,
    AuditEntry,
    GenerativeCanvas,
    GuardrailReport,
)
from .storyline import TICK_TITLES, TOTAL_TICKS, canvas_for_tick

# The tick at which the autonomous circadian consolidation fires.
CONSOLIDATION_TICK = 2

_EPOCH = datetime(2026, 6, 29, 9, 0, 0)


class SulcusEngine:
    """Single source of truth for the running simulation."""

    def __init__(self) -> None:
        self.tick: int = 0
        self.stream = IngestionStream()
        self.audit: List[AuditEntry] = []
        self.terminal_log: List[str] = []
        self.canvas: GenerativeCanvas
        self.report: GuardrailReport
        self._bootstrap()

    # ------------------------------------------------------------------ #
    def _bootstrap(self) -> None:
        """Initialise the world at Tick 0."""
        new_events = self.stream.ingest_tick(0)
        self._record_ingestion_audit(0, new_events)
        self.canvas = canvas_for_tick(0)
        self.terminal_log = self._render_log_header(0)
        self.report = evaluate(self.canvas, self.stream, 0)
        self.terminal_log += self.report.schema_log + self.report.eval_log
        self.audit.insert(
            0,
            AuditEntry(
                timestamp=_EPOCH,
                tick=0,
                actor="Sulcus Core",
                actor_kind=ActorKind.SYSTEM,
                action="System initialised",
                detail="Ingestion connectors LIVE (Slack, GitHub, CRM). Baseline plan ingested.",
            ),
        )

    # ------------------------------------------------------------------ #
    def advance(self) -> str:
        """Advance the storyline by one tick. Returns a toast message."""
        if self.tick >= TOTAL_TICKS - 1:
            return "Simulation complete — storyline already at final tick."

        self.tick += 1
        tick = self.tick
        self.terminal_log = self._render_log_header(tick)

        # 1) Ingest the new tick's events.
        new_events = self.stream.ingest_tick(tick)
        self._record_ingestion_audit(tick, new_events)
        self.terminal_log.append(
            f"[INGEST] {len(new_events)} new event(s) appended from live connectors."
        )

        # 2) Circadian consolidation (autonomous healing) if applicable.
        if tick == CONSOLIDATION_TICK:
            cons_log, cons_audit = run_consolidation(self.stream, tick)
            self.terminal_log += cons_log
            self.audit = cons_audit + self.audit

        # 3) Build the new canvas.
        self.canvas = canvas_for_tick(tick)

        # 4) Guardrails.
        self.report = evaluate(self.canvas, self.stream, tick)
        self.terminal_log += self.report.schema_log + self.report.eval_log

        # 5) Toast summary.
        title = TICK_TITLES.get(tick, f"Tick {tick}")
        if self.report.eval_status in ("WARNING", "WARNING".lower()):
            return f"⚠️ Tick {tick} — {title}: informational drift detected by Gate 2."
        return f"✅ Tick {tick} — {title}: state mutated & reconciled (faithfulness {self.report.faithfulness:.2f})."

    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        self.__init__()

    # ------------------------------------------------------------------ #
    def log_action(self, actor: str, action: str, detail: str = "") -> None:
        """Record a human-fired click-to-execute action in the brain history."""
        self.audit.insert(
            0,
            AuditEntry(
                timestamp=_EPOCH + timedelta(minutes=self.tick * 15 + 12),
                tick=self.tick,
                actor=actor,
                actor_kind=ActorKind.HUMAN,
                action=action,
                detail=detail,
            ),
        )

    # ------------------------------------------------------------------ #
    def _record_ingestion_audit(self, tick: int, events) -> None:
        for e in events:
            self.audit.insert(
                0,
                AuditEntry(
                    timestamp=e.timestamp,
                    tick=tick,
                    actor=e.user,
                    actor_kind=ActorKind.HUMAN,
                    action=f"Event ingested via {e.source if isinstance(e.source, str) else e.source.value}",
                    detail=e.text,
                ),
            )

    @staticmethod
    def _render_log_header(tick: int) -> List[str]:
        title = TICK_TITLES.get(tick, f"Tick {tick}")
        return [
            f"[SULCUS] ╔══════════════════════════════════════════════════╗",
            f"[SULCUS] ║  TICK {tick} — {title}",
            f"[SULCUS] ╚══════════════════════════════════════════════════╝",
        ]

    # ------------------------------------------------------------------ #
    @property
    def is_final(self) -> bool:
        return self.tick >= TOTAL_TICKS - 1
