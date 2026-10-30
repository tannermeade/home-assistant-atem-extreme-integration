"""Talking detection. Thresholds live in Home Assistant, not on the switcher."""

from __future__ import annotations

# Silence on a Fairlight meter is -100 dB. Speech on a sensibly gained strip
# is often somewhere between -45 and -15. -40 is only a starting point.
DEFAULT_TALK_THRESHOLD_DB = -40.0
TALK_THRESHOLD_MIN_DB = -100.0
TALK_THRESHOLD_MAX_DB = 6.0
TALK_THRESHOLD_STEP_DB = 0.5


def clamp_talk_threshold(value: float) -> float:
    """Snap a user value onto the threshold slider."""
    clamped = max(TALK_THRESHOLD_MIN_DB, min(TALK_THRESHOLD_MAX_DB, float(value)))
    steps = round(clamped / TALK_THRESHOLD_STEP_DB)
    return steps * TALK_THRESHOLD_STEP_DB


def is_talking(level_db: float | None, threshold_db: float) -> bool:
    """True when the louder channel is at or above the threshold.

    No sample yet is not talking. The comparison is exact: the sensor turns
    off as soon as the level drops below the threshold. Automations that
    switch cameras should add a short ``for:`` so a breath does not cut.
    """
    if level_db is None:
        return False
    return float(level_db) >= float(threshold_db)
