"""
sulcus.ingestion
================

The Ears of the system.

A *connector* is a small adapter that knows how to turn one external operational
surface (Slack, GitHub, a marketing CRM) into a stream of canonical
``IngestionEvent`` objects. In a production deployment each of these would wrap a
real webhook / polling client; here they emit a deterministic, programmatically
evolving mock stream keyed off the simulation tick so the demo behaves like a
live system without external credentials.

The ``IngestionStream`` is the append-only log that fans the connectors together
and exposes the corpus the evaluation loop grounds against.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List

from .schemas import IngestionEvent, SourceSystem

# A fixed clock so the demo is reproducible across reruns. Each tick advances
# the simulated wall-clock by a few minutes.
_EPOCH = datetime(2026, 6, 29, 9, 0, 0)


def _stamp(tick: int, offset_min: int = 0) -> datetime:
    return _EPOCH + timedelta(minutes=tick * 15 + offset_min)


class BaseConnector(ABC):
    """Common interface for every ingestion source."""

    source: SourceSystem
    name: str

    @abstractmethod
    def poll(self, tick: int) -> List[IngestionEvent]:
        """Return the events this connector emits *on entering* ``tick``."""
        raise NotImplementedError

    def healthcheck(self) -> Dict[str, str]:
        return {"connector": self.name, "source": str(self.source), "status": "LIVE"}


class SlackConnector(BaseConnector):
    """Communication feed -- PM and team chatter."""

    source = SourceSystem.COMMUNICATION
    name = "slack://workspace/product"

    def poll(self, tick: int) -> List[IngestionEvent]:
        if tick == 0:
            return [
                IngestionEvent(
                    event_id="slack-000",
                    tick=0,
                    timestamp=_stamp(0, 2),
                    source=self.source,
                    channel="#product",
                    user="Alice (PM)",
                    text="Team, our hard launch target is set for Friday via Stripe API.",
                    tags=["milestone", "intent:launch"],
                )
            ]
        if tick == 2:
            return [
                IngestionEvent(
                    event_id="slack-002",
                    tick=2,
                    timestamp=_stamp(2, 1),
                    source=self.source,
                    channel="#product",
                    user="Alice (PM)",
                    text="Ugh. Okay, let's delay launch to Next Tuesday. Bypassing Stripe entirely.",
                    tags=["milestone", "pivot", "intent:delay"],
                )
            ]
        return []


class GitHubConnector(BaseConnector):
    """Execution feed -- commits and Jira tickets."""

    source = SourceSystem.EXECUTION
    name = "github://org/checkout-service"

    def poll(self, tick: int) -> List[IngestionEvent]:
        if tick == 0:
            return [
                IngestionEvent(
                    event_id="jira-CHK-41",
                    tick=0,
                    timestamp=_stamp(0, 6),
                    source=self.source,
                    channel="jira:CHK-41",
                    user="Alice (PM)",
                    text="Jira ticket created: Integrate Stripe Webhooks for checkout flow.",
                    tags=["ticket", "stripe"],
                )
            ]
        if tick == 1:
            return [
                IngestionEvent(
                    event_id="gh-9af3c1",
                    tick=1,
                    timestamp=_stamp(1, 3),
                    source=self.source,
                    channel="repo:checkout-service",
                    user="Bob (Dev)",
                    text="Commit: Stripe webhooks are failing with 500 error token mismatch.",
                    tags=["incident", "stripe", "contradiction"],
                )
            ]
        return []


class CRMConnector(BaseConnector):
    """Operations feed -- marketing CRM / campaign locks."""

    source = SourceSystem.OPERATIONS
    name = "crm://marketing/campaigns"

    def poll(self, tick: int) -> List[IngestionEvent]:
        if tick == 0:
            return [
                IngestionEvent(
                    event_id="crm-LNK-7",
                    tick=0,
                    timestamp=_stamp(0, 9),
                    source=self.source,
                    channel="campaign:linkedin-q3",
                    user="Carol (Growth)",
                    text=(
                        "$50,000 LinkedIn launch campaign locked to fire Monday "
                        "morning, gated on the v1.0 checkout being live."
                    ),
                    tags=["budget", "campaign", "dependency:launch"],
                )
            ]
        return []


class IngestionStream:
    """Append-only fan-in log across every connector.

    Holds the full immutable history plus a ``tombstones`` set used by the
    circadian loop to mark events whose long-term vectors have been garbage
    collected (the events stay in the audit log; they simply stop influencing
    the live knowledge graph).
    """

    def __init__(self) -> None:
        self.connectors: List[BaseConnector] = [
            SlackConnector(),
            GitHubConnector(),
            CRMConnector(),
        ]
        self.events: List[IngestionEvent] = []
        self.tombstones: set[str] = set()

    # -- ingestion -------------------------------------------------------- #
    def ingest_tick(self, tick: int) -> List[IngestionEvent]:
        """Poll every connector for ``tick`` and append new events."""
        new: List[IngestionEvent] = []
        for connector in self.connectors:
            for ev in connector.poll(tick):
                self.events.append(ev)
                new.append(ev)
        return new

    # -- queries used by the evaluation loop ------------------------------ #
    def active_events(self) -> List[IngestionEvent]:
        """Events still influencing the live knowledge graph (not tombstoned)."""
        return [e for e in self.events if e.event_id not in self.tombstones]

    def corpus(self) -> str:
        """Lower-cased concatenation of active event text -- the grounding set."""
        return " \n ".join(e.text.lower() for e in self.active_events())

    def tombstone(self, event_ids: List[str]) -> None:
        self.tombstones.update(event_ids)

    def as_records(self) -> List[dict]:
        """Rows for the raw ephemeral event ticker (reverse chronological)."""
        rows = []
        for e in sorted(self.events, key=lambda x: x.timestamp, reverse=True):
            gc = " (GC)" if e.event_id in self.tombstones else ""
            rows.append(
                {
                    "Time": e.timestamp.strftime("%H:%M"),
                    "Source": e.source if isinstance(e.source, str) else e.source.value,
                    "User": e.user,
                    "Event Text": e.text + gc,
                }
            )
        return rows
