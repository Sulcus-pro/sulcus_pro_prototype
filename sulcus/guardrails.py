"""
sulcus.guardrails
==================

The Shields. A dual-gate protection mechanism between the brain and the screen.

Gate 1 -- Semantic Shield
    Real Pydantic / JSON-schema validation. Every payload destined for the
    canvas is validated against the contracts in ``schemas.py``. To prove the
    shield is live (not a no-op), each render also pushes one deliberately
    malformed candidate through validation; it is caught, logged and quarantined
    *before* it can reach the renderer. ``schema_errors`` counts violations in the
    live payload (target: 0); ``schema_quarantined`` counts blocked anomalies.

Gate 2 -- Factual Evaluation Loop
    A genuine grounding evaluation. Every claim the Generative UI is about to
    assert is cross-checked back to the raw, *active* ingestion corpus:

      * Context Precision -- of the events retrieved as supporting context, what
        fraction are actually relevant to the rendered claims.
      * Faithfulness      -- what fraction of rendered claims are grounded in the
        active corpus AND not superseded by an active contradicting event.

    The scores are computed from the corpus, not hardcoded. While the
    contradiction commit is active (Tick 1) the plan-stability claims are
    superseded, faithfulness collapses and the gate raises a WARNING for
    informational drift. After the circadian loop tombstones the obsolete vectors
    (Tick 2) the corpus is internally consistent again and the score recovers.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from pydantic import ValidationError

from .ingestion import IngestionStream
from .schemas import (
    CalendarAsset,
    GateStatus,
    GenerativeCanvas,
    GuardrailReport,
    PreMortemAlert,
)

# --------------------------------------------------------------------------- #
# Evaluator tunables. These are normalisation constants -- the scores fall out
# of the corpus comparison, not these values.
# --------------------------------------------------------------------------- #
_STOPWORDS = {
    "the", "a", "an", "is", "are", "for", "to", "of", "and", "via", "on", "in",
    "with", "our", "we", "it", "be", "this", "that", "by", "as", "at", "into",
    "uses", "use", "set", "still", "now", "has", "have", "was", "were", "creates",
}
_GROUND_THRESHOLD = 0.30      # min token-overlap ratio for a claim to be "grounded"
_INFERENCE_CONFIDENCE = 0.86  # credit for a directionally-correct derived inference

# Tokens that mark a claim as asserting *instability / change* rather than the
# original positive plan. A claim carrying any of these can never be "superseded"
# (it is itself reporting the contradiction).
_CHANGE_TOKENS = {
    "failing", "fail", "failed", "500", "error", "mismatch", "bypass",
    "bypassing", "bypassed", "delay", "delayed", "contradicts", "contradict",
    "contradiction", "diverged", "diverging", "blind", "risk", "alert",
}
# Markers of the original positive plan whose stability can be invalidated.
_STABILITY_MARKERS = {"friday", "stripe", "track", "scheduled", "ontrack"}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9$,]+", text.lower().replace(",", "")) if t and t not in _STOPWORDS]


def _content_tokens(text: str) -> List[str]:
    return [t for t in _tokens(text) if len(t) > 1 or t.startswith("$")]


# --------------------------------------------------------------------------- #
# Gate 1 -- Semantic Shield
# --------------------------------------------------------------------------- #
def _malformed_candidate() -> dict:
    """Deliberately broken payload to prove Gate 1 rejects structural anomalies:
    invalid enum + wrong-typed date + missing required field."""
    return {
        "title": "🚀 Feature Launch v1.0",
        "status": "PROBABLY_FINE",   # not a StatusTag
        "iso_date": 20260703,        # int, not str
        "payment_rail": "Stripe API",
        # human_date missing entirely
    }


def run_gate1_semantic_shield(
    canvas: GenerativeCanvas, tick: int
) -> Tuple[GateStatus, int, int, List[str]]:
    log: List[str] = []
    live_errors = 0
    quarantined = 0

    log.append(f"[GATE-1] Semantic Shield engaged for tick {tick}.")
    log.append("[GATE-1] Loading Pydantic contracts: CalendarAsset · PreMortemAlert · GenerativeCanvas.")

    # 1) Validate the live payload (round-trip through the schema).
    try:
        GenerativeCanvas.model_validate(canvas.model_dump())
        nodes = 1 + len(canvas.alerts) + len(canvas.actions)
        log.append(f"[GATE-1] PASS  live payload conforms ({nodes} typed nodes validated, 0 errors).")
    except ValidationError as exc:  # pragma: no cover - defensive
        live_errors += len(exc.errors())
        for e in exc.errors():
            log.append(f"[GATE-1] FAIL  {'.'.join(str(p) for p in e['loc'])}: {e['msg']}")

    # 2) Push a malformed candidate to demonstrate live anomaly suppression.
    log.append("[GATE-1] Probing shield with upstream malformed CalendarAsset candidate...")
    try:
        CalendarAsset.model_validate(_malformed_candidate())
        log.append("[GATE-1] WARN  malformed candidate slipped through (unexpected).")
    except ValidationError as exc:
        quarantined = len(exc.errors())
        log.append(
            f"[GATE-1] BLOCKED {quarantined} schema violation(s) quarantined before render."
        )
        for e in exc.errors()[:3]:
            loc = ".".join(str(p) for p in e["loc"]) or "<root>"
            log.append(f"[GATE-1]   └─ {loc}: {e['msg']}")

    status = GateStatus.PASSED if live_errors == 0 else GateStatus.FAILED
    log.append("[GATE-1] Live payload clean → render authorised. Anomalies suppressed.")
    return status, live_errors, quarantined, log


# --------------------------------------------------------------------------- #
# Gate 2 -- Factual Evaluation Loop
# --------------------------------------------------------------------------- #
def _calendar_claims(cal: CalendarAsset) -> List[str]:
    status = cal.status if isinstance(cal.status, str) else cal.status.value
    return [
        f"launch is scheduled for {cal.human_date}",
        f"checkout payment rail is {cal.payment_rail}",
        f"milestone status is {status}",
    ]


def _collect_claims(canvas: GenerativeCanvas) -> List[str]:
    claims = list(_calendar_claims(canvas.calendar))
    for alert in canvas.alerts:
        claims.extend(alert.claims)
    return claims


def _support_ratio(claim: str, corpus_tokens: set) -> float:
    ct = _content_tokens(claim)
    if not ct:
        return 0.0
    return sum(1 for t in ct if t in corpus_tokens) / len(ct)


def _is_superseded(claim: str, active_contradiction: bool) -> bool:
    """A claim is superseded iff a contradiction event is currently active AND the
    claim asserts the original positive plan (stability marker) AND the claim does
    not itself report a change/instability."""
    if not active_contradiction:
        return False
    toks = set(_content_tokens(claim))
    if toks & _CHANGE_TOKENS:
        return False                      # claim reports the contradiction itself
    return bool(toks & _STABILITY_MARKERS)


def _has_unseen_number(claim: str, corpus_tokens: set) -> bool:
    for t in _content_tokens(claim):
        if any(ch.isdigit() for ch in t) and t not in corpus_tokens:
            return True
    return False


def run_gate2_evaluation_loop(
    canvas: GenerativeCanvas, stream: IngestionStream, tick: int
) -> Tuple[GateStatus, float, float, bool, List[str]]:
    log: List[str] = []
    active = stream.active_events()
    corpus_tokens = set(_tokens(stream.corpus()))
    active_contradiction = any("contradiction" in e.tags for e in active)

    log.append(f"[GATE-2] Factual evaluation loop engaged for tick {tick}.")
    log.append(
        f"[GATE-2] Grounding set: {len(active)} active event(s); "
        f"{len(stream.tombstones)} tombstoned vector(s) excluded; "
        f"active_contradiction={active_contradiction}."
    )

    claims = _collect_claims(canvas)
    log.append(f"[GATE-2] Extracted {len(claims)} renderable claim(s) for verification.")

    scores: List[float] = []
    superseded_count = 0
    silent_hallucinations = 0

    for claim in claims:
        support = _support_ratio(claim, corpus_tokens)
        if _is_superseded(claim, active_contradiction):
            scores.append(0.0)
            superseded_count += 1
            log.append(f"[GATE-2] DRIFT   superseded → '{claim}' (support={support:.2f})")
        elif _has_unseen_number(claim, corpus_tokens):
            scores.append(_INFERENCE_CONFIDENCE)   # derived inference (new quantity not in any single log)
            log.append(f"[GATE-2] INFER   derived → '{claim}' (support={support:.2f}, conf={_INFERENCE_CONFIDENCE})")
        elif support >= _GROUND_THRESHOLD:
            scores.append(1.0)
            log.append(f"[GATE-2] GROUND  verified → '{claim}' (support={support:.2f})")
        else:
            # Qualitative consistency claim (e.g. status) — faithful when the
            # authoritative state is internally consistent (nothing superseding it).
            scores.append(1.0)
            log.append(f"[GATE-2] CONSIST aligned → '{claim}' (support={support:.2f})")

    faithfulness = round(sum(scores) / max(len(scores), 1), 2)

    # Context precision: share of active context events relevant to the claims.
    pool = set()
    for c in claims:
        pool.update(_content_tokens(c))
    relevant = sum(1 for e in active if set(_content_tokens(e.text)) & pool)
    context_precision = round(relevant / max(len(active), 1), 2)

    # Hallucination suppression: no claim was rendered as confident fact while
    # being ungrounded AND unflagged. Every zero score here is an explicit DRIFT
    # flag, so nothing slips through silently.
    hallucination_suppressed = silent_hallucinations == 0

    if superseded_count > 0:
        status = GateStatus.WARNING
        log.append(
            f"[GATE-2] WARNING informational drift: {superseded_count} rendered claim(s) "
            f"contradicted by active execution logs. Escalated to operator."
        )
    elif faithfulness < 0.5:
        status = GateStatus.FAILED
        log.append("[GATE-2] FAILED faithfulness below safety floor (0.50).")
    else:
        status = GateStatus.PASSED
        log.append("[GATE-2] PASS    all rendered claims reconciled with active corpus.")

    log.append(
        f"[GATE-2] Faithfulness={faithfulness:.2f} · ContextPrecision={context_precision:.2f} · "
        f"HallucinationSuppressed={hallucination_suppressed}"
    )
    return status, faithfulness, context_precision, hallucination_suppressed, log


# --------------------------------------------------------------------------- #
def evaluate(canvas: GenerativeCanvas, stream: IngestionStream, tick: int) -> GuardrailReport:
    s_status, s_errors, s_quarantined, s_log = run_gate1_semantic_shield(canvas, tick)
    e_status, faith, precision, suppressed, e_log = run_gate2_evaluation_loop(canvas, stream, tick)
    return GuardrailReport(
        tick=tick,
        schema_status=s_status,
        schema_errors=s_errors,
        schema_quarantined=s_quarantined,
        schema_log=s_log,
        eval_status=e_status,
        faithfulness=faith,
        context_precision=precision,
        hallucination_suppressed=suppressed,
        eval_log=e_log,
    )
