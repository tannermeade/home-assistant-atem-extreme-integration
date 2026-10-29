"""Switcher state assembled from ATEM command payloads.

Field layouts follow sofie-atem-connection (the parser Bitfocus Companion
uses) for firmware 8+, which is what the ATEM Mini Extreme ISO speaks.
Where a newer and an older layout both exist, the firmware 8 layout is
preferred and the difference is noted in the README.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from ..const import (
    PROGRAMMABLE_PORTS,
    VIDEO_MODES,
)
from .audio import classic_word_to_db
from .protocol import AtemCommand, cstring, i16, i32, i64, u16, u32, u8


def _flag_name(raw: int, table: list[tuple[int, str]], default: str) -> str:
    chosen = default
    for bit, name in table:
        if bit and (raw & bit) == bit:
            chosen = name
            break
    return chosen


RECORDING_STATUS_BITS = [(1 << 7, "stopping"), (1 << 0, "recording")]
RECORDING_ERROR_BITS = [
    (1 << 15, "unknown"),
    (1 << 5, "dropping_frames"),
    (1 << 4, "media_unformatted"),
    (1 << 3, "media_error"),
    (1 << 2, "media_full"),
    (1 << 1, "none"),
]
STREAM_STATUS_BITS = [
    (1 << 5, "stopping"),
    (1 << 2, "streaming"),
    (1 << 1, "connecting"),
    (1 << 0, "idle"),
]
DISK_STATUS_BITS = [
    (1 << 3, "recording"),
    (1 << 2, "ready"),
    (1 << 1, "unformatted"),
    (1 << 0, "idle"),
    (1 << 5, "removed"),
]


@dataclass
class InputInfo:
    id: int
    long_name: str
    short_name: str
    internal_port: int = 0
    external_port: int = 0
    me_availability: int = 0
    source_availability: int = 0

    @property
    def label(self) -> str:
        return self.long_name or self.short_name or f"Input {self.id}"


@dataclass
class FairlightSource:
    index: int
    source: int
    source_type: int = 0
    input_type: int = 0
    mix_option: int = 0
    fader_gain: int = 0
    input_gain: int = 0
    balance: int = 0
    eq_enabled: bool = False
    delay_frames: int = 0


@dataclass
class Levels:
    left: float = -100.0
    right: float = -100.0
    left_peak: float = -100.0
    right_peak: float = -100.0
    input_left: float = -100.0
    input_right: float = -100.0
    output_left: float = -100.0
    output_right: float = -100.0
    compressor_gr: float = 0.0
    limiter_gr: float = 0.0
    expander_gr: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "left_db": self.left,
            "right_db": self.right,
            "left_peak_db": self.left_peak,
            "right_peak_db": self.right_peak,
            "input_left_db": self.input_left,
            "input_right_db": self.input_right,
            "output_left_db": self.output_left,
            "output_right_db": self.output_right,
            "compressor_gain_reduction_db": self.compressor_gr,
            "limiter_gain_reduction_db": self.limiter_gr,
            "expander_gain_reduction_db": self.expander_gr,
        }


@dataclass
class DskState:
    on_air: bool = False
    in_transition: bool = False
    is_auto: bool = False
    remaining_frames: int = 0
    tie: bool = False
    rate: int = 0


@dataclass
class AtemState:
    product_name: str = ""
    protocol_version: str = ""
    video_mode: int | None = None
    topology: dict[str, int] = field(default_factory=dict)
    inputs: dict[int, InputInfo] = field(default_factory=dict)
    program: dict[int, int] = field(default_factory=dict)
    preview: dict[int, int] = field(default_factory=dict)
    preview_mixed: dict[int, bool] = field(default_factory=dict)
    transition_style: dict[int, int] = field(default_factory=dict)
    transition_selection: dict[int, int] = field(default_factory=dict)
    transition_position: dict[int, int] = field(default_factory=dict)
    in_transition: dict[int, bool] = field(default_factory=dict)
    transition_frames: dict[int, int] = field(default_factory=dict)
    mix_rate: dict[int, int] = field(default_factory=dict)
    dip_rate: dict[int, int] = field(default_factory=dict)
    wipe_rate: dict[int, int] = field(default_factory=dict)
    dve_rate: dict[int, int] = field(default_factory=dict)
    preview_transition: dict[int, bool] = field(default_factory=dict)
    ftb_black: dict[int, bool] = field(default_factory=dict)
    ftb_in_transition: dict[int, bool] = field(default_factory=dict)
    ftb_frames: dict[int, int] = field(default_factory=dict)
    ftb_rate: dict[int, int] = field(default_factory=dict)
    keyer_count: dict[int, int] = field(default_factory=dict)
    usk_on_air: dict[tuple[int, int], bool] = field(default_factory=dict)
    dsk: dict[int, DskState] = field(default_factory=dict)
    aux: dict[int, int] = field(default_factory=dict)
    fairlight_input_type: dict[int, int] = field(default_factory=dict)
    fairlight_sources: dict[tuple[int, int], FairlightSource] = field(default_factory=dict)
    master_fader: int | None = None
    master_follow_ftb: bool | None = None
    master_eq: bool | None = None
    levels: dict[tuple[int, int], Levels] = field(default_factory=dict)
    master_levels: Levels | None = None
    tally: dict[int, int] = field(default_factory=dict)
    classic_mix: dict[int, int] = field(default_factory=dict)
    classic_fader: dict[int, int] = field(default_factory=dict)
    has_fairlight: bool = False
    has_classic_audio: bool = False
    recording_raw: int = 0
    recording_status: str = "unknown"
    recording_error: str = "unknown"
    recording_time_available: int | None = None
    record_all_inputs: bool | None = None
    recording_duration: str | None = None
    recording_dropped: bool | None = None
    disks: dict[int, dict] = field(default_factory=dict)
    streaming_raw: int = 0
    streaming_status: str = "unknown"
    streaming_error: str = "unknown"
    streaming_bitrate: int | None = None
    streaming_cache: int | None = None
    streaming_duration: str | None = None
    media_players: dict[int, dict] = field(default_factory=dict)
    multiview_layout: dict[int, int] = field(default_factory=dict)
    multiview_windows: dict[tuple[int, int], int] = field(default_factory=dict)
    supersource_boxes: dict[int, dict] = field(default_factory=dict)
    init_complete: bool = False
    seen_commands: set[str] = field(default_factory=set)

    def copy(self) -> AtemState:
        return deepcopy(self)

    @property
    def video_mode_name(self) -> str | None:
        if self.video_mode is None:
            return None
        return VIDEO_MODES.get(self.video_mode, f"Mode {self.video_mode}")

    def input_label(self, source_id: int) -> str:
        info = self.inputs.get(source_id)
        if info:
            return info.label
        if source_id == 0:
            return "Black"
        return f"Source {source_id}"

    def programmable_inputs(self) -> list[InputInfo]:
        inputs = list(self.inputs.values())
        if any(item.me_availability for item in inputs):
            chosen = [item for item in inputs if item.me_availability & 0x01]
        else:
            chosen = [item for item in inputs if item.internal_port in PROGRAMMABLE_PORTS]
        if not chosen:
            chosen = inputs
        return sorted(chosen, key=lambda item: (item.internal_port != 0, item.id))

    def usk_ids(self, me: int = 0) -> list[int]:
        declared = self.keyer_count.get(me)
        seen = sorted(key for mix, key in self.usk_on_air if mix == me)
        if declared is not None and declared >= 0:
            count = max(declared, (max(seen) + 1) if seen else 0)
            return list(range(count))
        return seen

    def apply(self, command: AtemCommand) -> str:
        """Apply one command. Returns 'state', 'levels', or '' if ignored."""
        name = command.name
        self.seen_commands.add(name)
        payload = command.payload
        handler = _HANDLERS.get(name)
        if handler is None:
            return ""
        return handler(self, payload)


def _on_pin(state: AtemState, payload: bytes) -> str:
    state.product_name = cstring(payload, 0, min(44, len(payload))) or state.product_name
    return "state"


def _on_ver(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 4:
        state.protocol_version = f"{u16(payload, 0)}.{u16(payload, 2)}"
    elif len(payload) >= 2:
        state.protocol_version = str(u16(payload, 0))
    return "state"


def _on_top(state: AtemState, payload: bytes) -> str:
    names = (
        "me",
        "sources",
        "dsk",
        "aux",
        "mix_minus",
        "media_players",
        "multiviewers",
        "serial",
        "hyperdecks",
        "dve",
        "stingers",
        "supersources",
        "talkback",
        "camera_control",
    )
    state.topology = {names[index]: payload[index] for index in range(min(len(names), len(payload)))}
    return "state"


def _on_mec(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.keyer_count[payload[0]] = payload[1]
    return "state"


def _on_vidm(state: AtemState, payload: bytes) -> str:
    if payload:
        state.video_mode = payload[0]
    return "state"


def _on_inpr(state: AtemState, payload: bytes) -> str:
    if len(payload) < 24:
        return ""
    source = u16(payload, 0)
    state.inputs[source] = InputInfo(
        id=source,
        long_name=cstring(payload, 2, 20),
        short_name=cstring(payload, 22, 4),
        external_port=u16(payload, 30) if len(payload) >= 32 else 0,
        internal_port=u8(payload, 32) if len(payload) >= 33 else 0,
        source_availability=u8(payload, 34) if len(payload) >= 35 else 0,
        me_availability=u8(payload, 35) if len(payload) >= 36 else 0,
    )
    return "state"


def _on_prgi(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 4:
        state.program[payload[0]] = u16(payload, 2)
    return "state"


def _on_prvi(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 4:
        state.preview[payload[0]] = u16(payload, 2)
        if len(payload) >= 5:
            state.preview_mixed[payload[0]] = payload[4] == 1
    return "state"


def _on_trss(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 3:
        me = payload[0]
        state.transition_style[me] = payload[1]
        state.transition_selection[me] = payload[2]
    return "state"


def _on_trps(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 3:
        me = payload[0]
        state.in_transition[me] = payload[1] == 1
        state.transition_frames[me] = payload[2]
        if len(payload) >= 6:
            state.transition_position[me] = u16(payload, 4)
    return "state"


def _on_tmxp(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.mix_rate[payload[0]] = payload[1]
    return "state"


def _on_tdpp(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.dip_rate[payload[0]] = payload[1]
    return "state"


def _on_twpp(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.wipe_rate[payload[0]] = payload[1]
    return "state"


def _on_tdvp(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.dve_rate[payload[0]] = payload[1]
    return "state"


def _on_trpr(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.preview_transition[payload[0]] = payload[1] == 1
    return "state"


def _on_ftbs(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 3:
        me = payload[0]
        state.ftb_black[me] = payload[1] == 1
        state.ftb_in_transition[me] = payload[2] == 1
        if len(payload) >= 4:
            state.ftb_frames[me] = payload[3]
    return "state"


def _on_ftbp(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.ftb_rate[payload[0]] = payload[1]
    return "state"


def _on_keon(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 3:
        state.usk_on_air[(payload[0], payload[1])] = payload[2] == 1
    return "state"


def _on_dsks(state: AtemState, payload: bytes) -> str:
    if len(payload) < 4:
        return ""
    current = state.dsk.get(payload[0], DskState())
    current.on_air = payload[1] == 1
    current.in_transition = payload[2] == 1
    current.is_auto = payload[3] == 1
    # Firmware 8 inserts "transitioning towards on-air" at byte 4.
    if len(payload) >= 6:
        current.remaining_frames = payload[5]
    elif len(payload) >= 5:
        current.remaining_frames = payload[4]
    state.dsk[payload[0]] = current
    return "state"


def _on_dskp(state: AtemState, payload: bytes) -> str:
    if len(payload) < 3:
        return ""
    current = state.dsk.get(payload[0], DskState())
    current.tie = payload[1] == 1
    current.rate = payload[2]
    state.dsk[payload[0]] = current
    return "state"


def _on_auxs(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 4:
        state.aux[payload[0]] = u16(payload, 2)
    return "state"


def _on_tl(state: AtemState, payload: bytes, *, by_source: bool) -> str:
    if len(payload) < 2:
        return ""
    count = u16(payload, 0)
    rest = payload[2:]
    stride = 4 if by_source else 1
    if by_source and count and len(rest) < count * 4 and len(rest) >= count * 3:
        stride = 3
    for index in range(count):
        offset = index * stride
        if offset >= len(rest):
            break
        if by_source:
            if offset + 3 > len(rest):
                break
            source = int.from_bytes(rest[offset : offset + 2], "big")
            flags = rest[offset + 2]
            state.tally[source] = flags
        else:
            # TlIn is ordered, not keyed. Only used when TlSr never arrives.
            flags = rest[offset]
            state.tally.setdefault(-(index + 1), flags)
    return "state"


def _on_tlsr(state: AtemState, payload: bytes) -> str:
    return _on_tl(state, payload, by_source=True)


def _on_tlin(state: AtemState, payload: bytes) -> str:
    if state.tally and all(key >= 0 for key in state.tally):
        return ""
    return _on_tl(state, payload, by_source=False)


def _on_faip(state: AtemState, payload: bytes) -> str:
    if len(payload) < 3:
        return ""
    state.has_fairlight = True
    index = u16(payload, 0)
    input_type = payload[2]
    state.fairlight_input_type[index] = input_type
    for key, source in state.fairlight_sources.items():
        if key[0] == index:
            source.input_type = input_type
    return "state"


def _on_fasp(state: AtemState, payload: bytes) -> str:
    if len(payload) < 45:
        return ""
    state.has_fairlight = True
    index = u16(payload, 0)
    source = i64(payload, 8)
    current = state.fairlight_sources.get((index, source), FairlightSource(index, source))
    current.source_type = u8(payload, 16)
    current.delay_frames = u8(payload, 18)
    current.input_gain = i32(payload, 20)
    current.eq_enabled = u8(payload, 29) == 1
    current.balance = i16(payload, 40)
    current.fader_gain = i32(payload, 44)
    if len(payload) >= 50:
        current.mix_option = payload[49]
    current.input_type = state.fairlight_input_type.get(index, current.input_type)
    state.fairlight_sources[(index, source)] = current
    return "state"


def _on_famp(state: AtemState, payload: bytes) -> str:
    state.has_fairlight = True
    if len(payload) >= 16:
        state.master_eq = payload[1] == 1
        state.master_fader = i32(payload, 12)
        state.master_follow_ftb = payload[16] == 1 if len(payload) > 16 else None
    return "state"


def _on_fmlv(state: AtemState, payload: bytes) -> str:
    # FMLv (firmware 8+): int64 source, uint16 index, then 16 int16 meter words.
    if len(payload) < 40:
        return ""
    state.has_fairlight = True
    source = i64(payload, 0)
    index = u16(payload, 8)
    from .audio import fairlight_to_db

    def db(at: int) -> float:
        return fairlight_to_db(i16(payload, at))

    state.levels[(index, source)] = Levels(
        input_left=db(10),
        input_right=db(12),
        left_peak=db(36),
        right_peak=db(38),
        expander_gr=db(18),
        compressor_gr=db(20),
        limiter_gr=db(22),
        output_left=db(24),
        output_right=db(26),
        left=db(32),
        right=db(34),
    )
    # Peaks of the pre-fader input are kept alongside post-fader peaks.
    levels = state.levels[(index, source)]
    levels.input_left = db(10)
    levels.input_right = db(12)
    return "levels"


def _on_fdlv(state: AtemState, payload: bytes) -> str:
    if len(payload) < 24:
        return ""
    state.has_fairlight = True
    from .audio import fairlight_to_db

    def db(at: int) -> float:
        return fairlight_to_db(i16(payload, at))

    state.master_levels = Levels(
        input_left=db(0),
        input_right=db(2),
        compressor_gr=db(8),
        limiter_gr=db(10),
        output_left=db(12),
        output_right=db(14),
        left=db(20),
        right=db(22),
        left_peak=db(24) if len(payload) >= 26 else db(4),
        right_peak=db(26) if len(payload) >= 28 else db(6),
    )
    return "levels"


def _on_amip(state: AtemState, payload: bytes) -> str:
    if len(payload) < 10:
        return ""
    state.has_classic_audio = True
    source = u16(payload, 0)
    # Classic mix option lives at byte 8 on the AMIP field (0 off, 1 on, 2 AFV).
    state.classic_mix[source] = u8(payload, 8)
    if len(payload) >= 12:
        state.classic_fader[source] = u16(payload, 10)
    return "state"


def _on_amlv(state: AtemState, payload: bytes) -> str:
    if len(payload) < 20:
        return ""
    state.has_classic_audio = True
    state.master_levels = Levels(
        left=classic_word_to_db(u32(payload, 4)),
        right=classic_word_to_db(u32(payload, 8)),
        left_peak=classic_word_to_db(u32(payload, 12)),
        right_peak=classic_word_to_db(u32(payload, 16)),
    )
    sources = sorted(state.classic_mix)
    # After the 36-byte master/monitor header, four uint32 meter words per input.
    offset = 36
    for source in sources:
        if offset + 16 > len(payload):
            break
        state.levels[(source, 0)] = Levels(
            left=classic_word_to_db(u32(payload, offset)),
            right=classic_word_to_db(u32(payload, offset + 4)),
            left_peak=classic_word_to_db(u32(payload, offset + 8)),
            right_peak=classic_word_to_db(u32(payload, offset + 12)),
        )
        offset += 16
    return "levels"


def _on_rtms(state: AtemState, payload: bytes) -> str:
    raw = u16(payload, 0)
    state.recording_raw = raw
    state.recording_status = _flag_name(raw, RECORDING_STATUS_BITS, "idle")
    state.recording_error = _flag_name(raw, RECORDING_ERROR_BITS, "no_media" if raw == 0 else "none")
    if raw == 0:
        state.recording_status = "idle"
        state.recording_error = "no_media"
    if len(payload) >= 8:
        state.recording_time_available = u32(payload, 4)
    return "state"


def _on_rtmr(state: AtemState, payload: bytes) -> str:
    state.recording_duration = _timecode(payload)
    if len(payload) >= 5:
        state.recording_dropped = payload[4] != 0
    return "state"


def _on_isoi(state: AtemState, payload: bytes) -> str:
    if payload:
        state.record_all_inputs = payload[0] == 1
    return "state"


def _on_rtmd(state: AtemState, payload: bytes) -> str:
    if len(payload) < 10:
        return ""
    disk_id = u32(payload, 0)
    raw_status = u16(payload, 8)
    removed = bool(raw_status & (1 << 5))
    info = {
        "id": disk_id,
        "seconds_available": u32(payload, 4),
        "status": _flag_name(raw_status & ~(1 << 5), DISK_STATUS_BITS, "unknown"),
        "volume": cstring(payload, 10, 64),
    }
    if removed:
        state.disks.pop(disk_id, None)
    else:
        state.disks[disk_id] = info
    return "state"


def _on_strs(state: AtemState, payload: bytes) -> str:
    raw = u16(payload, 0)
    state.streaming_raw = raw
    state.streaming_status = _flag_name(raw, STREAM_STATUS_BITS, "idle")
    if raw & (1 << 15):
        state.streaming_error = "unknown"
    elif raw & (1 << 4):
        state.streaming_error = "invalid_state"
    else:
        state.streaming_error = "none"
    return "state"


def _on_srss(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 4:
        state.streaming_bitrate = u32(payload, 0)
    if len(payload) >= 6:
        state.streaming_cache = u16(payload, 4)
    return "state"


def _on_srst(state: AtemState, payload: bytes) -> str:
    state.streaming_duration = _timecode(payload)
    return "state"


def _on_mpce(state: AtemState, payload: bytes) -> str:
    if len(payload) < 3:
        return ""
    state.media_players[payload[0]] = {
        "type": payload[1],
        "index": payload[2],
    }
    return "state"


def _on_mvpr(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 2:
        state.multiview_layout[payload[0]] = payload[1]
    return "state"


def _on_mvin(state: AtemState, payload: bytes) -> str:
    if len(payload) >= 4:
        state.multiview_windows[(payload[0], payload[1])] = u16(payload, 2)
    return "state"


def _on_ssbp(state: AtemState, payload: bytes) -> str:
    # Single-supersource layout used by the Mini Extreme family:
    # box, enabled, source, x, y, size. Marked unverified on hardware.
    if len(payload) < 4:
        return ""
    box = payload[0]
    info = {
        "enabled": payload[1] == 1,
        "source": u16(payload, 2),
    }
    if len(payload) >= 10:
        info["x"] = i16(payload, 4)
        info["y"] = i16(payload, 6)
        info["size"] = u16(payload, 8)
    state.supersource_boxes[box] = info
    return "state"


def _on_incm(state: AtemState, payload: bytes) -> str:
    state.init_complete = True
    return "init"


def _timecode(payload: bytes) -> str | None:
    if len(payload) < 4:
        return None
    return f"{payload[0]:02d}:{payload[1]:02d}:{payload[2]:02d}:{payload[3]:02d}"


_HANDLERS = {
    "_pin": _on_pin,
    "_ver": _on_ver,
    "_top": _on_top,
    "_MeC": _on_mec,
    "VidM": _on_vidm,
    "InPr": _on_inpr,
    "PrgI": _on_prgi,
    "PrvI": _on_prvi,
    "TrSS": _on_trss,
    "TrPs": _on_trps,
    "TMxP": _on_tmxp,
    "TDpP": _on_tdpp,
    "TWpP": _on_twpp,
    "TDvP": _on_tdvp,
    "TrPr": _on_trpr,
    "TsPr": _on_trpr,
    "FtbS": _on_ftbs,
    "FtbP": _on_ftbp,
    "KeOn": _on_keon,
    "DskS": _on_dsks,
    "DskP": _on_dskp,
    "AuxS": _on_auxs,
    "TlSr": _on_tlsr,
    "TlIn": _on_tlin,
    "FAIP": _on_faip,
    "FASP": _on_fasp,
    "FAMP": _on_famp,
    "FMLv": _on_fmlv,
    "FDLv": _on_fdlv,
    "AMIP": _on_amip,
    "AMLv": _on_amlv,
    "RTMS": _on_rtms,
    "RTMR": _on_rtmr,
    "ISOi": _on_isoi,
    "RTMD": _on_rtmd,
    "StRS": _on_strs,
    "SRSS": _on_srss,
    "SRST": _on_srst,
    "MPCE": _on_mpce,
    "MvPr": _on_mvpr,
    "MvIn": _on_mvin,
    "SSBP": _on_ssbp,
    "InCm": _on_incm,
}
