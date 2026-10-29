"""Fairlight level conversion and strip naming."""

from __future__ import annotations

import math

from ..const import (
    FAIRLIGHT_SOURCE_MONO_LEFT,
    FAIRLIGHT_SOURCE_MONO_RIGHT,
    FAIRLIGHT_SOURCE_STEREO,
    PORT_BARS,
    PORT_BLACK,
    PORT_COLOR,
    PORT_EXTERNAL,
    PORT_MEDIA_FILL,
    PORT_MEDIA_KEY,
    PORT_SUPERSOURCE,
)

# Classic mixer fader word → dB (Skårhøj / PyATEMMax). Not used for Fairlight.
def classic_word_to_db(word: int) -> float:
    word &= 0xFFFF
    if word <= 32:
        return -60.0
    return math.log10((word / 2048.0) / 16.0) * 20.0


def fairlight_to_db(raw: int) -> float:
    """Fairlight meter and fader words are hundredths of a dB."""
    if raw <= -10000:
        return -100.0
    return raw / 100.0


def db_to_fairlight(db: float, *, minimum: float = -100.0, maximum: float = 10.0) -> int:
    clamped = max(minimum, min(maximum, float(db)))
    return int(round(clamped * 100))


def source_channel_label(source_id: int) -> str:
    if source_id == FAIRLIGHT_SOURCE_STEREO:
        return "Stereo"
    if source_id == FAIRLIGHT_SOURCE_MONO_LEFT:
        return "Left"
    if source_id == FAIRLIGHT_SOURCE_MONO_RIGHT:
        return "Right"
    if source_id < 0:
        return f"Source {source_id}"
    return f"Source {source_id}"


def fairlight_strip_name(index: int, source_id: int, input_type: int, input_name: str | None) -> str:
    """Human name for a Fairlight strip.

    Input indexes are whatever the switcher reports (HDMI usually matches the
    video source id; original Extreme mics are 1301/1302; Extreme ISO G2 XLRs
    are 1001/1002). Names are never hardcoded to one hardware revision.
    """
    channel = source_channel_label(source_id)
    if input_name:
        base = input_name
    elif input_type == 1:
        base = f"Media player {index - 2000}" if index >= 2001 else f"Media {index}"
    elif input_type == 2:
        if index in (1301, 1302):
            base = f"Mic {index - 1300}"
        elif index in (1001, 1002):
            base = f"XLR {index - 1000}"
        elif 1101 <= index <= 1108:
            base = f"AES {index - 1100}"
        elif index == 1201:
            base = "RCA"
        else:
            base = f"Audio {index}"
    elif input_type == 4:
        base = f"MADI {index}"
    else:
        base = f"Input {index}"
    if source_id == FAIRLIGHT_SOURCE_STEREO:
        return base
    return f"{base} {channel}"


def port_kind(port: int) -> str:
    return {
        PORT_EXTERNAL: "external",
        PORT_BLACK: "black",
        PORT_BARS: "bars",
        PORT_COLOR: "color",
        PORT_MEDIA_FILL: "media",
        PORT_MEDIA_KEY: "media_key",
        PORT_SUPERSOURCE: "supersource",
    }.get(port, "other")
