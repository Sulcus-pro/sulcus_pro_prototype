"""Sulcus — The Autonomous Corporate Nervous System.

A self-contained, deterministic simulation of an operational-event intelligence
platform with circadian memory consolidation and a dual-gate guardrail system.
"""

from .state_engine import SulcusEngine
from .storyline import TICK_TITLES, TOTAL_TICKS

__all__ = ["SulcusEngine", "TICK_TITLES", "TOTAL_TICKS"]
__version__ = "1.0.0"
