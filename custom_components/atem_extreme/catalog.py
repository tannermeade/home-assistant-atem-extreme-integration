"""Entity catalog derived from a switcher snapshot.

Platforms and the unit tests share this so the README, the entities, and the
tests cannot drift apart. Nothing in this module imports Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass

from .atem.audio import fairlight_strip_name, fairlight_to_db
from .atem.state import AtemState, FairlightSource
from .const import (
    DEFAULT_ME,
    MIX_OPTIONS,
    PORT_EXTERNAL,
    TRANSITION_STYLES,
)


@dataclass(frozen=True)
class EntitySpec:
    platform: str
    key: str
    name: str
    kind: str
    address: tuple
    read_only: bool
    icon: str
    entity_category: str | None = None
    unit: str | None = None
    description: str = ""
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None


def build_specs(state: AtemState, me: int = DEFAULT_ME) -> list[EntitySpec]:
    """Return every entity the integration would create for this snapshot."""
    specs: list[EntitySpec] = []
    specs.extend(_switching(state, me))
    specs.extend(_keyers(state, me))
    specs.extend(_routing(state))
    specs.extend(_audio(state))
    specs.extend(_record_stream(state))
    specs.extend(_tally(state))
    specs.extend(_extras(state))
    return specs


def _switching(state: AtemState, me: int) -> list[EntitySpec]:
    specs = [
        EntitySpec(
            "select",
            f"me{me}_program",
            "Program",
            "program",
            (me,),
            False,
            "mdi:television",
            description="Video source currently on the program bus (what is on air).",
        ),
        EntitySpec(
            "select",
            f"me{me}_preview",
            "Preview",
            "preview",
            (me,),
            False,
            "mdi:monitor",
            description="Video source currently on the preview bus.",
        ),
        EntitySpec(
            "select",
            f"me{me}_transition_style",
            "Transition style",
            "transition_style",
            (me,),
            False,
            "mdi:transition",
            description="Mix, dip, wipe, DVE, or stinger.",
        ),
        EntitySpec(
            "switch",
            f"me{me}_ftb",
            "Fade to black",
            "ftb",
            (me,),
            False,
            "mdi:brightness-4",
            description="On when the program output is fully faded to black. Changing it runs FTB.",
        ),
        EntitySpec(
            "button",
            f"me{me}_cut",
            "Cut",
            "cut",
            (me,),
            False,
            "mdi:content-cut",
            description="Immediate cut. The layers included follow Next transition.",
        ),
        EntitySpec(
            "button",
            f"me{me}_auto",
            "Auto transition",
            "auto",
            (me,),
            False,
            "mdi:play-speed",
            description="Auto transition at the current rate.",
        ),
        EntitySpec(
            "button",
            f"me{me}_ftb_go",
            "Fade to black trigger",
            "ftb_trigger",
            (me,),
            False,
            "mdi:circle-half-full",
            description="Start a fade to or from black, the same as the FTB button.",
        ),
        EntitySpec(
            "switch",
            f"me{me}_preview_transition",
            "Preview transition",
            "preview_transition",
            (me,),
            False,
            "mdi:eye-outline",
            description="PREV TRANS. Shows the next transition on the preview output.",
        ),
        EntitySpec(
            "switch",
            f"me{me}_next_background",
            "Next transition background",
            "transition_layer",
            (me, 0),
            False,
            "mdi:layers",
            description="Whether the next cut/auto includes the background.",
        ),
        EntitySpec(
            "number",
            f"me{me}_mix_rate",
            "Mix rate",
            "mix_rate",
            (me,),
            False,
            "mdi:timer-outline",
            unit="frames",
            description="Mix transition duration in frames.",
            min_value=1,
            max_value=250,
            step=1,
        ),
        EntitySpec(
            "number",
            f"me{me}_ftb_rate",
            "Fade to black rate",
            "ftb_rate",
            (me,),
            False,
            "mdi:timer-outline",
            unit="frames",
            min_value=1,
            max_value=250,
            step=1,
            description="Fade to black duration in frames.",
        ),
        EntitySpec(
            "sensor",
            f"me{me}_transition_position",
            "Transition position",
            "transition_position",
            (me,),
            True,
            "mdi:percent",
            entity_category="diagnostic",
            unit="%",
            description="0 at the start of a transition, 100 at the end.",
        ),
        EntitySpec(
            "binary_sensor",
            f"me{me}_in_transition",
            "Transition in progress",
            "in_transition",
            (me,),
            True,
            "mdi:swap-horizontal",
            description="On while an auto or T-bar transition is running.",
        ),
        EntitySpec(
            "binary_sensor",
            f"me{me}_ftb_active",
            "Fade to black running",
            "ftb_running",
            (me,),
            True,
            "mdi:progress-clock",
            entity_category="diagnostic",
            description="On while a fade to black is animating.",
        ),
        EntitySpec(
            "sensor",
            "video_mode",
            "Video mode",
            "video_mode",
            (),
            True,
            "mdi:video",
            entity_category="diagnostic",
            description="Switcher video standard reported by VidM.",
        ),
    ]
    for info in state.programmable_inputs():
        if info.internal_port not in (PORT_EXTERNAL, 1, 2):  # HDMI/SDI, black, bars
            # Still offer internal sources on the select. Buttons only for the
            # physical inputs plus black and color bars, which are the ones
            # people map to dashboard buttons.
            if info.internal_port != 0 and info.id not in (0, 1000):
                continue
        specs.append(
            EntitySpec(
                "button",
                f"take_{info.id}",
                f"Take {info.label}",
                "take",
                (me, info.id),
                False,
                "mdi:video-input-hdmi" if info.internal_port == PORT_EXTERNAL else "mdi:rectangle",
                description=f"Put {info.label} on program immediately.",
            )
        )
    for keyer in state.usk_ids(me):
        specs.append(
            EntitySpec(
                "switch",
                f"me{me}_next_key_{keyer}",
                f"Next transition key {keyer + 1}",
                "transition_layer",
                (me, keyer + 1),
                False,
                "mdi:layers-outline",
                description="Include this upstream keyer in the next cut or auto.",
            )
        )
    return specs


def _keyers(state: AtemState, me: int) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    for keyer in state.usk_ids(me):
        specs.append(
            EntitySpec(
                "switch",
                f"me{me}_usk_{keyer}",
                f"Upstream key {keyer + 1}",
                "usk",
                (me, keyer),
                False,
                "mdi:key",
                description="Upstream keyer on air.",
            )
        )
    for index in sorted(state.dsk):
        specs.extend(
            [
                EntitySpec(
                    "switch",
                    f"dsk_{index}_on_air",
                    f"Downstream key {index + 1}",
                    "dsk_on_air",
                    (index,),
                    False,
                    "mdi:key-variant",
                    description="Downstream keyer on air.",
                ),
                EntitySpec(
                    "switch",
                    f"dsk_{index}_tie",
                    f"Downstream key {index + 1} tie",
                    "dsk_tie",
                    (index,),
                    False,
                    "mdi:link-variant",
                    description="Tie this downstream keyer to the next transition.",
                ),
                EntitySpec(
                    "button",
                    f"dsk_{index}_auto",
                    f"Downstream key {index + 1} auto",
                    "dsk_auto",
                    (index,),
                    False,
                    "mdi:play",
                    description="Auto transition this downstream keyer.",
                ),
                EntitySpec(
                    "binary_sensor",
                    f"dsk_{index}_transition",
                    f"Downstream key {index + 1} transitioning",
                    "dsk_transition",
                    (index,),
                    True,
                    "mdi:progress-clock",
                    entity_category="diagnostic",
                    description="On while this downstream keyer is animating.",
                ),
            ]
        )
    return specs


def _routing(state: AtemState) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    for index in sorted(state.aux):
        specs.append(
            EntitySpec(
                "select",
                f"aux_{index}",
                f"Aux {index + 1}",
                "aux",
                (index,),
                False,
                "mdi:video-input-scart",
                description="Source routed to this auxiliary output.",
            )
        )
    for player, info in sorted(state.media_players.items()):
        kind = "Still" if info.get("type") == 1 else "Clip" if info.get("type") == 2 else "Source"
        specs.append(
            EntitySpec(
                "sensor",
                f"media_player_{player}",
                f"Media player {player + 1}",
                "media_player",
                (player,),
                True,
                "mdi:image",
                entity_category="diagnostic",
                description=f"Current media player source ({kind} {info.get('index', 0) + 1}). Read-only.",
            )
        )
    return specs


def _audio(state: AtemState) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    if state.has_fairlight or state.fairlight_sources:
        for key in sorted(state.fairlight_sources):
            source = state.fairlight_sources[key]
            label = _strip_label(state, source)
            specs.extend(_fairlight_strip(source, label))
        specs.extend(
            [
                EntitySpec(
                    "sensor",
                    "master_level",
                    "Master level",
                    "master_level",
                    (),
                    True,
                    "mdi:volume-high",
                    unit="dB",
                    description="Fairlight master post-fader level (louder of left/right), from FDLv.",
                ),
                EntitySpec(
                    "number",
                    "master_fader",
                    "Master fader",
                    "master_fader",
                    (),
                    False,
                    "mdi:tune-vertical",
                    unit="dB",
                    min_value=-100,
                    max_value=10,
                    step=0.5,
                    description="Fairlight master fader gain.",
                ),
                EntitySpec(
                    "switch",
                    "master_follow_ftb",
                    "Master follows fade to black",
                    "master_follow_ftb",
                    (),
                    False,
                    "mdi:link",
                    description="Duck the master fader with fade to black.",
                ),
            ]
        )
    elif state.has_classic_audio:
        for source_id in sorted(state.classic_mix):
            label = state.input_label(source_id)
            specs.append(
                EntitySpec(
                    "sensor",
                    f"classic_level_{source_id}",
                    f"{label} level",
                    "classic_level",
                    (source_id,),
                    True,
                    "mdi:volume-medium",
                    unit="dB",
                    description="Classic audio mixer meter (best effort, not used by Extreme ISO).",
                )
            )
        specs.append(
            EntitySpec(
                "sensor",
                "master_level",
                "Master level",
                "master_level",
                (),
                True,
                "mdi:volume-high",
                unit="dB",
                description="Classic master meter.",
            )
        )
    return specs


def _fairlight_strip(source: FairlightSource, label: str) -> list[EntitySpec]:
    index, source_id = source.index, source.source
    return [
        EntitySpec(
            "sensor",
            f"level_{index}_{source_id}",
            f"{label} level",
            "level",
            (index, source_id),
            True,
            "mdi:volume-medium",
            unit="dB",
            description="Fairlight post-fader meter in dB. Left/right, peaks, and gain reduction are attributes. Updated at the configured rate, not the switcher's 10 Hz.",
        ),
        EntitySpec(
            "select",
            f"mix_{index}_{source_id}",
            f"{label} mix",
            "mix",
            (index, source_id),
            False,
            "mdi:volume-source",
            description="Off, On, or Audio follow video.",
        ),
        EntitySpec(
            "number",
            f"fader_{index}_{source_id}",
            f"{label} fader",
            "fader",
            (index, source_id),
            False,
            "mdi:tune-vertical",
            unit="dB",
            min_value=-100,
            max_value=10,
            step=0.5,
            description="Fairlight channel fader.",
        ),
    ]


def _strip_label(state: AtemState, source: FairlightSource) -> str:
    video = state.inputs.get(source.index)
    input_name = video.label if video and source.input_type == 0 else None
    return fairlight_strip_name(source.index, source.source, source.input_type, input_name)


def _record_stream(state: AtemState) -> list[EntitySpec]:
    specs = [
        EntitySpec(
            "switch",
            "recording",
            "Recording",
            "recording",
            (),
            False,
            "mdi:record-rec",
            description="Start or stop program recording.",
        ),
        EntitySpec(
            "sensor",
            "recording_status",
            "Recording status",
            "recording_status",
            (),
            True,
            "mdi:record-circle",
            description="idle, recording, or stopping, plus any disk error.",
        ),
        EntitySpec(
            "sensor",
            "recording_duration",
            "Recording duration",
            "recording_duration",
            (),
            True,
            "mdi:timer",
            entity_category="diagnostic",
            description="Elapsed recording timecode.",
        ),
        EntitySpec(
            "switch",
            "iso_recording",
            "ISO record all inputs",
            "iso",
            (),
            False,
            "mdi:video-input-component",
            entity_category="config",
            description="Record every input (ISO) along with the program file. This is the switcher's record-all-inputs setting.",
        ),
        EntitySpec(
            "switch",
            "streaming",
            "Streaming",
            "streaming",
            (),
            False,
            "mdi:access-point",
            description="Start or stop the onboard RTMP encoder.",
        ),
        EntitySpec(
            "sensor",
            "streaming_status",
            "Streaming status",
            "streaming_status",
            (),
            True,
            "mdi:broadcast",
            description="idle, connecting, streaming, or stopping.",
        ),
        EntitySpec(
            "sensor",
            "streaming_bitrate",
            "Streaming bitrate",
            "streaming_bitrate",
            (),
            True,
            "mdi:speedometer",
            entity_category="diagnostic",
            unit="bit/s",
            description="Onboard encoder bitrate reported by the switcher.",
        ),
        EntitySpec(
            "sensor",
            "streaming_duration",
            "Streaming duration",
            "streaming_duration",
            (),
            True,
            "mdi:timer",
            entity_category="diagnostic",
            description="Elapsed stream timecode.",
        ),
    ]
    for disk_id, info in sorted(state.disks.items()):
        name = info.get("volume") or f"Disk {disk_id}"
        specs.append(
            EntitySpec(
                "sensor",
                f"disk_{disk_id}",
                f"Recording disk {name}",
                "disk",
                (disk_id,),
                True,
                "mdi:harddisk",
                entity_category="diagnostic",
                description="Remaining record time and disk status.",
            )
        )
    return specs


def _tally(state: AtemState) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    for info in state.programmable_inputs():
        if info.internal_port != PORT_EXTERNAL and info.id > 40:
            continue
        if info.internal_port not in (PORT_EXTERNAL,) and not (1 <= info.id <= 40):
            continue
        specs.append(
            EntitySpec(
                "binary_sensor",
                f"tally_pgm_{info.id}",
                f"{info.label} program tally",
                "tally_pgm",
                (info.id,),
                True,
                "mdi:circle",
                entity_category="diagnostic",
                description="On when this input is on program.",
            )
        )
        specs.append(
            EntitySpec(
                "binary_sensor",
                f"tally_pvw_{info.id}",
                f"{info.label} preview tally",
                "tally_pvw",
                (info.id,),
                True,
                "mdi:circle-outline",
                entity_category="diagnostic",
                description="On when this input is on preview.",
            )
        )
    return specs


def _extras(state: AtemState) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    if state.multiview_layout or state.multiview_windows:
        specs.append(
            EntitySpec(
                "sensor",
                "multiview",
                "Multiview",
                "multiview",
                (),
                True,
                "mdi:view-grid",
                entity_category="diagnostic",
                description="Multiview layout. Window sources are attributes. Read-only.",
            )
        )
    if state.supersource_boxes or state.topology.get("supersources"):
        specs.append(
            EntitySpec(
                "sensor",
                "supersource",
                "SuperSource",
                "supersource",
                (),
                True,
                "mdi:picture-in-picture-bottom-right",
                entity_category="diagnostic",
                description="SuperSource box enable and source. Geometry is best-effort and read-only.",
            )
        )
    return specs


def programmable_labels(state: AtemState) -> list[str]:
    labels = []
    seen: set[str] = set()
    for info in state.programmable_inputs():
        label = info.label
        if label in seen:
            label = f"{label} ({info.id})"
        seen.add(label)
        labels.append(label)
    return labels


def label_to_source(state: AtemState, label: str) -> int | None:
    for info in state.programmable_inputs():
        if info.label == label or f"{info.label} ({info.id})" == label:
            if label == info.label or label.endswith(f"({info.id})"):
                # Prefer an exact unique label; the disambiguated form wins when needed.
                if label == info.label and sum(1 for item in state.programmable_inputs() if item.label == label) > 1:
                    continue
                return info.id
    return None


def source_to_label(state: AtemState, source_id: int) -> str | None:
    labels = programmable_labels(state)
    infos = state.programmable_inputs()
    for info, label in zip(infos, labels):
        if info.id == source_id:
            return label
    return state.input_label(source_id) if source_id in state.inputs else None


def transition_style_options() -> list[str]:
    return [TRANSITION_STYLES[index] for index in range(5)]


def mix_option_labels() -> list[str]:
    return [MIX_OPTIONS[1], MIX_OPTIONS[2], MIX_OPTIONS[4]]


def fader_db(raw: int | None) -> float | None:
    if raw is None:
        return None
    return round(fairlight_to_db(raw), 1)
