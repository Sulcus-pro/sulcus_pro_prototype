"""
sulcus.schemas
==============

The canonical data contracts for the Sulcus Autonomous Corporate Nervous System.

Every object that flows through the system -- a raw ingestion event, a rendered
generative-UI asset, or a guardrail verdict -- is described here as a strict
Pydantic v2 model. Gate 1 (the Semantic Shield) validates real payloads against
these schemas before anything is allowed to render, which is what lets the system
catch structural/format anomalies *before* they reach a human.

These are not decorative type hints; the app constructs and validates real
instances of these models on every simulation tick.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# Ingestion layer (The Ears)
# --------------------------------------------------------------------------- #
class SourceSystem(str, Enum):
    """The three operational feeds Sulcus listens to."""

    COMMUNICATION = "Communication"   # Slack / Teams
    EXECUTION = "Execution"           # GitHub commits / Jira tickets
    OPERATIONS = "Operations"         # Marketing CRM logs


class IngestionEvent(BaseModel):
    """A single immutable, append-only operational event."""

    event_id: str = Field(..., min_length=3)
    tick: int = Field(..., ge=0)
    timestamp: datetime
    source: SourceSystem
    channel: str = Field(..., min_length=1)   # e.g. "#product", "repo:checkout"
    user: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1, max_length=2000)
    # Free-form tags the connectors attach (e.g. "milestone", "incident").
    tags: List[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Ingestion event text must not be empty after trim.")
        return v

    model_config = {"use_enum_values": True}


# --------------------------------------------------------------------------- #
# Generative UI layer (The Mouth)
# --------------------------------------------------------------------------- #
class StatusTag(str, Enum):
    ON_TRACK = "On Track"
    AT_RISK = "At Risk"
    DELAYED = "Delayed"


class CalendarAsset(BaseModel):
    """A structured calendar event the Generative Canvas renders as HTML."""

    title: str
    iso_date: str               # YYYY-MM-DD
    human_date: str             # "This Friday"
    status: StatusTag
    payment_rail: str           # "Stripe API", "Bypassed", ...
    note: str = ""

    model_config = {"use_enum_values": True}


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PreMortemAlert(BaseModel):
    """A predictive risk surfaced before it becomes an incident."""

    headline: str
    severity: Severity
    detail: str
    # Each claim is a short canonical assertion the evaluation loop will try to
    # ground back to the raw ingestion logs. This is what makes Gate 2 real.
    claims: List[str] = Field(default_factory=list)
    # Optional impact band used by the risk matrix renderer.
    likelihood: Literal["Low", "Medium", "High"] = "Medium"
    impact: Literal["Low", "Medium", "High"] = "Medium"

    model_config = {"use_enum_values": True}


class ActionButton(BaseModel):
    """A click-to-execute remediation the operator can fire from inside a card."""

    key: str
    label: str
    toast: str
    audit_action: str


class GenerativeCanvas(BaseModel):
    """The full validated payload for one render of the right-hand canvas."""

    tick: int = Field(..., ge=0)
    calendar: CalendarAsset
    alerts: List[PreMortemAlert] = Field(default_factory=list)
    actions: List[ActionButton] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Guardrail layer (The Shields)
# --------------------------------------------------------------------------- #
class GateStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class GuardrailReport(BaseModel):
    """The combined verdict of Gate 1 (schema) and Gate 2 (evaluation)."""

    tick: int
    # Gate 1 -- Semantic Shield
    schema_status: GateStatus
    schema_errors: int = 0          # violations in the LIVE payload (should be 0)
    schema_quarantined: int = 0     # malformed candidates caught & blocked pre-render
    schema_log: List[str] = Field(default_factory=list)
    # Gate 2 -- Factual Evaluation Loop
    eval_status: GateStatus
    faithfulness: float = Field(..., ge=0.0, le=1.0)
    context_precision: float = Field(..., ge=0.0, le=1.0)
    hallucination_suppressed: bool = True
    eval_log: List[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


# --------------------------------------------------------------------------- #
# Memory / audit layer (The Storyline + Temporal Brain)
# --------------------------------------------------------------------------- #
class ActorKind(str, Enum):
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"      # the autonomous brain (circadian loop, GC, etc.)


class AuditEntry(BaseModel):
    """One line in the Temporal Brain history trail: who / what / when."""

    timestamp: datetime
    tick: int
    actor: str
    actor_kind: ActorKind
    action: str
    detail: str = ""

    model_config = {"use_enum_values": True}
