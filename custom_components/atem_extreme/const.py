"""Constants for the ATEM Extreme integration."""

from __future__ import annotations

DOMAIN = "atem_extreme"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_METER_HZ = "meter_hz"

DEFAULT_PORT = 9910
DEFAULT_METER_HZ = 2
METER_HZ_OPTIONS = (1, 2, 3, 4)

DEFAULT_ME = 0

# Fairlight source ids (signed int64), shared by Mini / Extreme / Extreme ISO.
FAIRLIGHT_SOURCE_STEREO = -65280  # 0xFFFFFFFFFFFF0100
FAIRLIGHT_SOURCE_MONO_LEFT = -256  # 0xFFFFFFFFFFFFFF00
FAIRLIGHT_SOURCE_MONO_RIGHT = -255  # 0xFFFFFFFFFFFFFF01

# Internal port types (InPr).
PORT_EXTERNAL = 0
PORT_BLACK = 1
PORT_BARS = 2
PORT_COLOR = 3
PORT_MEDIA_FILL = 4
PORT_MEDIA_KEY = 5
PORT_SUPERSOURCE = 6

PROGRAMMABLE_PORTS = {
    PORT_EXTERNAL,
    PORT_BLACK,
    PORT_BARS,
    PORT_COLOR,
    PORT_MEDIA_FILL,
    PORT_SUPERSOURCE,
}

MIX_OFF = 1
MIX_ON = 2
MIX_AFV = 4
MIX_OPTIONS = {
    MIX_OFF: "Off",
    MIX_ON: "On",
    MIX_AFV: "Audio follow video",
}

TRANSITION_STYLES = {
    0: "Mix",
    1: "Dip",
    2: "Wipe",
    3: "DVE",
    4: "Stinger",
}

VIDEO_MODES = {
    0: "525i59.94 NTSC",
    1: "625i50 PAL",
    2: "525i59.94 NTSC 16:9",
    3: "625i50 PAL 16:9",
    4: "720p50",
    5: "720p59.94",
    6: "1080i50",
    7: "1080i59.94",
    8: "1080p23.98",
    9: "1080p24",
    10: "1080p25",
    11: "1080p29.97",
    12: "1080p50",
    13: "1080p59.94",
    14: "2160p23.98",
    15: "2160p24",
    16: "2160p25",
    17: "2160p29.97",
    18: "2160p50",
    19: "2160p59.94",
    24: "1080p30",
    25: "1080p60",
    26: "720p60",
    27: "1080i60",
}
