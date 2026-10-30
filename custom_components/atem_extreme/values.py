"""Read and write entity values without importing Home Assistant."""

from __future__ import annotations

from .atem.audio import fairlight_to_db
from .atem.client import AtemClient
from .atem.state import AtemState, Levels
from .catalog import EntitySpec, label_to_source, source_to_label
from .const import MIX_OPTIONS, TRANSITION_STYLES, VIDEO_MODES

_MIX_BY_LABEL = {label: value for value, label in MIX_OPTIONS.items()}
_STYLE_BY_LABEL = {label: value for value, label in TRANSITION_STYLES.items()}


def read_value(state: AtemState, spec: EntitySpec):
    kind = spec.kind
    me = spec.address[0] if spec.address else 0
    if kind == "program":
        return source_to_label(state, state.program.get(me, 0))
    if kind == "preview":
        return source_to_label(state, state.preview.get(me, 0))
    if kind == "transition_style":
        return TRANSITION_STYLES.get(state.transition_style.get(me, 0), "Mix")
    if kind == "ftb":
        return bool(state.ftb_black.get(me, False))
    if kind == "preview_transition":
        return bool(state.preview_transition.get(me, False))
    if kind == "transition_layer":
        bit = spec.address[1]
        return bool(state.transition_selection.get(me, 0) & (1 << bit))
    if kind == "mix_rate":
        return state.mix_rate.get(me, 25)
    if kind == "ftb_rate":
        return state.ftb_rate.get(me, 25)
    if kind == "transition_position":
        raw = state.transition_position.get(me)
        if raw is None:
            return 0 if state.in_transition.get(me) else None
        return round(raw / 100.0, 1)
    if kind == "in_transition":
        return bool(state.in_transition.get(me, False))
    if kind == "ftb_running":
        return bool(state.ftb_in_transition.get(me, False))
    if kind == "video_mode":
        if state.video_mode is None:
            return state.video_mode_name
        return VIDEO_MODES.get(state.video_mode, f"Mode {state.video_mode}")
    if kind == "usk":
        return bool(state.usk_on_air.get((spec.address[0], spec.address[1]), False))
    if kind == "dsk_on_air":
        dsk = state.dsk.get(spec.address[0])
        return bool(dsk and dsk.on_air)
    if kind == "dsk_tie":
        dsk = state.dsk.get(spec.address[0])
        return bool(dsk and dsk.tie)
    if kind == "dsk_transition":
        dsk = state.dsk.get(spec.address[0])
        return bool(dsk and dsk.in_transition)
    if kind == "aux":
        return source_to_label(state, state.aux.get(spec.address[0], 0))
    if kind == "media_player":
        info = state.media_players.get(spec.address[0], {})
        kind_name = {1: "Still", 2: "Clip"}.get(info.get("type"), "Source")
        return f"{kind_name} {int(info.get('index', 0)) + 1}"
    if kind == "level":
        return _loud(state.levels.get((spec.address[0], spec.address[1])))
    if kind == "classic_level":
        return _loud(state.levels.get((spec.address[0], 0)))
    if kind == "master_level":
        return _loud(state.master_levels)
    if kind == "mix":
        source = state.fairlight_sources.get((spec.address[0], spec.address[1]))
        return MIX_OPTIONS.get(source.mix_option if source else 0, "Off")
    if kind == "fader":
        source = state.fairlight_sources.get((spec.address[0], spec.address[1]))
        if source is None:
            return None
        return round(fairlight_to_db(source.fader_gain), 1)
    if kind == "master_fader":
        if state.master_fader is None:
            return None
        return round(fairlight_to_db(state.master_fader), 1)
    if kind == "master_follow_ftb":
        return bool(state.master_follow_ftb)
    if kind == "recording":
        return state.recording_status == "recording"
    if kind == "recording_status":
        if state.recording_status == "unknown":
            return None
        if state.recording_error not in ("none", "unknown", "no_media"):
            return f"{state.recording_status} ({state.recording_error})"
        return state.recording_status
    if kind == "recording_duration":
        return state.recording_duration
    if kind == "iso":
        return bool(state.record_all_inputs)
    if kind == "streaming":
        return state.streaming_status == "streaming"
    if kind == "streaming_status":
        return None if state.streaming_status == "unknown" else state.streaming_status
    if kind == "streaming_bitrate":
        return state.streaming_bitrate
    if kind == "streaming_duration":
        return state.streaming_duration
    if kind == "disk":
        info = state.disks.get(spec.address[0])
        if not info:
            return None
        seconds = info.get("seconds_available")
        if seconds is None:
            return info.get("status")
        return seconds
    if kind == "tally_pgm":
        return bool(state.tally.get(spec.address[0], 0) & 0x01)
    if kind == "tally_pvw":
        return bool(state.tally.get(spec.address[0], 0) & 0x02)
    if kind == "multiview":
        if not state.multiview_layout:
            return "Unknown"
        layout = next(iter(state.multiview_layout.values()))
        return f"Layout {layout}"
    if kind == "supersource":
        enabled = sum(1 for box in state.supersource_boxes.values() if box.get("enabled"))
        return f"{enabled} boxes on"
    return None


def extra_attributes(state: AtemState, spec: EntitySpec) -> dict:
    kind = spec.kind
    if kind in {"level", "classic_level"}:
        levels = state.levels.get((spec.address[0], spec.address[1] if kind == "level" else 0))
        return _level_attrs(levels)
    if kind == "master_level":
        attrs = _level_attrs(state.master_levels)
        if state.master_fader is not None:
            attrs["fader_db"] = round(fairlight_to_db(state.master_fader), 1)
        return attrs
    if kind == "recording_status":
        return {
            "error": state.recording_error,
            "seconds_available": state.recording_time_available,
            "dropped_frames": state.recording_dropped,
            "iso_all_inputs": state.record_all_inputs,
        }
    if kind == "streaming_status":
        return {"error": state.streaming_error, "bitrate": state.streaming_bitrate}
    if kind == "disk":
        return dict(state.disks.get(spec.address[0], {}))
    if kind == "multiview":
        windows = {}
        for (mv, window), source in sorted(state.multiview_windows.items()):
            windows[f"{mv}:{window}"] = state.input_label(source)
        return {"layouts": dict(state.multiview_layout), "windows": windows}
    if kind == "supersource":
        boxes = {}
        for index, box in sorted(state.supersource_boxes.items()):
            copied = dict(box)
            if "source" in copied:
                copied["source_name"] = state.input_label(copied["source"])
            boxes[str(index)] = copied
        return {
            "boxes": boxes,
            "art_fill": state.input_label(state.supersource_art) if state.supersource_art is not None else None,
            "art_option": state.supersource_art_option,
            "units": "x and y are SuperSource units (visible frame -16..16 by -9..9). Size 1 fills the frame.",
            "layout_verified_on_hardware": False,
        }
    if kind == "fader":
        source = state.fairlight_sources.get((spec.address[0], spec.address[1]))
        if not source:
            return {}
        return {
            "input_gain_db": round(fairlight_to_db(source.input_gain), 1),
            "balance": source.balance / 100.0,
            "eq_enabled": source.eq_enabled,
            "delay_frames": source.delay_frames,
        }
    if kind in {"program", "preview", "aux"}:
        return {"source_id": _selected_source(state, spec)}
    return {}


def _selected_source(state: AtemState, spec: EntitySpec) -> int | None:
    me = spec.address[0] if spec.address else 0
    if spec.kind == "program":
        return state.program.get(me)
    if spec.kind == "preview":
        return state.preview.get(me)
    if spec.kind == "aux":
        return state.aux.get(spec.address[0])
    return None


def _loud(levels: Levels | None) -> float | None:
    if levels is None:
        return None
    return round(max(levels.left, levels.right), 1)


def strip_level(state: AtemState, spec: EntitySpec) -> float | None:
    """Louder channel for a talking sensor, in dB."""
    if spec.kind == "classic_talking":
        return _loud(state.levels.get((spec.address[0], 0)))
    if len(spec.address) < 2:
        return None
    return _loud(state.levels.get((spec.address[0], spec.address[1])))


def _level_attrs(levels: Levels | None) -> dict:
    if levels is None:
        return {}
    return {key: round(value, 1) for key, value in levels.as_dict().items()}


async def async_write(client: AtemClient, spec: EntitySpec, value) -> None:
    """Send the command for a user change. `value` is the new select/switch/number."""
    kind = spec.kind
    me = spec.address[0] if spec.address else 0
    if kind == "program":
        await client.set_program(_require_source(client.state, value), me)
    elif kind == "preview":
        await client.set_preview(_require_source(client.state, value), me)
    elif kind == "aux":
        await client.set_aux(spec.address[0], _require_source(client.state, value))
    elif kind == "transition_style":
        if value not in _STYLE_BY_LABEL:
            raise ValueError(f"Unknown transition style {value}")
        await client.set_transition_style(_STYLE_BY_LABEL[value], me)
    elif kind == "ftb":
        fully_black = bool(client.state.ftb_black.get(me, False))
        if bool(value) != fully_black:
            await client.fade_to_black(me)
    elif kind == "ftb_trigger":
        await client.fade_to_black(me)
    elif kind == "cut":
        await client.cut(me)
    elif kind == "auto":
        await client.auto(me)
    elif kind == "take":
        await client.set_program(spec.address[1], me)
    elif kind == "preview_transition":
        await client.set_preview_transition(bool(value), me)
    elif kind == "transition_layer":
        bit = spec.address[1]
        selection = client.state.transition_selection.get(me, 0)
        mask = 1 << bit
        selection = selection | mask if value else selection & ~mask
        await client.set_transition_selection(selection, me)
    elif kind == "mix_rate":
        await client.set_mix_rate(int(value), me)
    elif kind == "ftb_rate":
        await client.set_ftb_rate(int(value), me)
    elif kind == "usk":
        await client.set_usk_on_air(spec.address[1], bool(value), me)
    elif kind == "dsk_on_air":
        await client.set_dsk_on_air(spec.address[0], bool(value))
    elif kind == "dsk_tie":
        await client.set_dsk_tie(spec.address[0], bool(value))
    elif kind == "dsk_auto":
        await client.dsk_auto(spec.address[0])
    elif kind == "mix":
        option = _MIX_BY_LABEL.get(value)
        if option is None:
            raise ValueError(f"Unknown mix option {value}")
        await client.set_fairlight_mix(spec.address[0], spec.address[1], option)
    elif kind == "fader":
        await client.set_fairlight_fader(spec.address[0], spec.address[1], float(value))
    elif kind == "master_fader":
        await client.set_master_fader(float(value))
    elif kind == "master_follow_ftb":
        await client.set_master_follow_ftb(bool(value))
    elif kind == "recording":
        await client.set_recording(bool(value))
    elif kind == "iso":
        await client.set_record_all_inputs(bool(value))
    elif kind == "streaming":
        await client.set_streaming(bool(value))
    else:
        raise ValueError(f"{spec.key} is read-only")


def _require_source(state: AtemState, label: str) -> int:
    source = label_to_source(state, label)
    if source is None:
        raise ValueError(f"Unknown input {label}")
    return source
