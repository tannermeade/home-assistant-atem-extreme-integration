"""SuperSource layouts for the Mini Extreme.

Positions are the same numbers ATEM Software Control shows. The visible
frame is centered: x from -16 to 16, y from -9 to 9, positive y up.
A size of 1 fills the frame. The wire protocol stores x and y in
hundredths and size and crop in thousandths.

Nothing here is verified on hardware. The geometry is the firmware 8
coordinate system used by the Extreme family.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .atem.state import AtemState
from .const import PORT_EXTERNAL

# Firmware 8 CSBP mask: enabled, source, x, y, size, cropped, four crops.
_BOX_MASK = 0x03FF
# Firmware 8 CSSc mask: art fill source and art option (behind the boxes).
_ART_MASK = (1 << 0) | (1 << 2)

CORNERS = ("Bottom right", "Bottom left", "Top right", "Top left")
_CORNER_SIGN = {
    "Bottom right": (1, -1),
    "Bottom left": (-1, -1),
    "Top right": (1, 1),
    "Top left": (-1, 1),
}

DEFAULT_CORNER = "Bottom right"
DEFAULT_CORNER_SIZE = 0.30
DEFAULT_CORNER_MARGIN = 0.8
DEFAULT_ZOOM_COLUMN = 0.25

CORNER_SIZE_RANGE = (0.15, 0.45, 0.01)
CORNER_MARGIN_RANGE = (0.0, 3.0, 0.1)
ZOOM_COLUMN_RANGE = (0.18, 0.32, 0.01)


@dataclass(frozen=True)
class Box:
    enabled: bool
    source: int
    x: float
    y: float
    size: float
    crop_top: float = 0.0
    crop_bottom: float = 0.0
    crop_left: float = 0.0
    crop_right: float = 0.0

    @property
    def cropped(self) -> bool:
        return any(
            value > 0 for value in (self.crop_top, self.crop_bottom, self.crop_left, self.crop_right)
        )


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    kind: str
    box_role: str = ""
    cameras_on_right: bool = True
    zoom: bool = False
    swapped: bool = False


@dataclass(frozen=True)
class BuiltLayout:
    name: str
    background: int | None
    boxes: tuple[Box, Box, Box, Box]
    art_option: int = 0


@dataclass
class SuperSourceAdjustments:
    """Local choices. They are not sent until a layout is pushed."""

    layout: str | None = None
    roles: dict[str, int] = field(default_factory=dict)
    corner: str = DEFAULT_CORNER
    corner_size: float = DEFAULT_CORNER_SIZE
    corner_margin: float = DEFAULT_CORNER_MARGIN
    zoom_column: float = DEFAULT_ZOOM_COLUMN
    save_name: str = ""


PRESETS: tuple[Preset, ...] = (
    Preset("corner_wide", "Corner wide", "corner", "wide"),
    Preset("corner_person_1", "Corner person 1", "corner", "person1"),
    Preset("corner_person_2", "Corner person 2", "corner", "person2"),
    Preset("screen_left", "Screen left, cameras right", "stack", cameras_on_right=True),
    Preset("screen_right", "Screen right, cameras left", "stack", cameras_on_right=False),
    Preset("screen_left_zoom", "Screen left, cameras right, zoomed", "stack", cameras_on_right=True, zoom=True),
    Preset("screen_right_zoom", "Screen right, cameras left, zoomed", "stack", cameras_on_right=False, zoom=True),
    Preset("screen_left_swap", "Screen left, cameras right, swapped", "stack", cameras_on_right=True, swapped=True),
    Preset("screen_right_swap", "Screen right, cameras left, swapped", "stack", cameras_on_right=False, swapped=True),
    Preset(
        "screen_left_zoom_swap",
        "Screen left, cameras right, zoomed, swapped",
        "stack",
        cameras_on_right=True,
        zoom=True,
        swapped=True,
    ),
    Preset(
        "screen_right_zoom_swap",
        "Screen right, cameras left, zoomed, swapped",
        "stack",
        cameras_on_right=False,
        zoom=True,
        swapped=True,
    ),
    Preset("boxes_off", "Boxes off", "off"),
)

_PRESET_BY_NAME = {preset.name: preset for preset in PRESETS}
ROLES = ("screen", "person1", "person2", "wide")


def preset_names() -> list[str]:
    return [preset.name for preset in PRESETS]


MAX_LAYOUT_NAME = 40


def clean_layout_name(name: str) -> str:
    """A saved-layout name. Built-in names are reserved."""
    cleaned = " ".join(str(name).split())
    if not cleaned:
        raise ValueError("Enter a name in SuperSource save name first.")
    if len(cleaned) > MAX_LAYOUT_NAME:
        raise ValueError(f"Use a name of {MAX_LAYOUT_NAME} characters or fewer.")
    if cleaned in _PRESET_BY_NAME:
        raise ValueError(f"{cleaned} is a built-in layout. Choose another name.")
    return cleaned


def capture_layout(state: AtemState, name: str) -> BuiltLayout:
    """Snapshot the SuperSource the switcher is reporting right now."""
    cleaned = clean_layout_name(name)
    if not state.supersource_boxes:
        raise ValueError("The switcher has not reported a SuperSource layout yet.")
    boxes = []
    for index in range(4):
        info = state.supersource_boxes.get(index)
        boxes.append(_off() if info is None else _box_from_reported(info))
    option = 0 if state.supersource_art_option is None else int(state.supersource_art_option)
    return BuiltLayout(cleaned, state.supersource_art, tuple(boxes), option)


def layout_to_dict(built: BuiltLayout) -> dict:
    return {
        "name": built.name,
        "background": built.background,
        "art_option": built.art_option,
        "boxes": [
            {
                "enabled": box.enabled,
                "source": box.source,
                "x": box.x,
                "y": box.y,
                "size": box.size,
                "crop_top": box.crop_top,
                "crop_bottom": box.crop_bottom,
                "crop_left": box.crop_left,
                "crop_right": box.crop_right,
            }
            for box in built.boxes
        ],
    }


def layout_from_dict(data: dict) -> BuiltLayout:
    raw_boxes = data.get("boxes")
    if not isinstance(raw_boxes, list) or len(raw_boxes) != 4:
        raise ValueError("Saved layout is missing its four boxes.")
    boxes = tuple(_box_from_reported(item) for item in raw_boxes)
    background = data.get("background")
    if background is not None:
        background = int(background)
    return BuiltLayout(str(data["name"]), background, boxes, int(data.get("art_option") or 0))


def clamp_corner_size(value: float) -> float:
    low, high, _step = CORNER_SIZE_RANGE
    return min(high, max(low, round(float(value), 2)))


def clamp_corner_margin(value: float) -> float:
    low, high, _step = CORNER_MARGIN_RANGE
    return min(high, max(low, round(float(value), 1)))


def clamp_zoom_column(value: float) -> float:
    low, high, _step = ZOOM_COLUMN_RANGE
    return min(high, max(low, round(float(value), 2)))


def default_roles(state: AtemState) -> dict[str, int]:
    """HDMI order: person 1, person 2, wide, screen. Later inputs are ignored."""
    externals = [item.id for item in state.programmable_inputs() if item.internal_port == PORT_EXTERNAL]
    if not externals:
        externals = [1, 2, 3, 4]

    def nth(index: int) -> int:
        return externals[min(index, len(externals) - 1)]

    return {"person1": nth(0), "person2": nth(1), "wide": nth(2), "screen": nth(3)}


def build_preset(name: str, roles: dict[str, int], adjustments: SuperSourceAdjustments) -> BuiltLayout:
    preset = _PRESET_BY_NAME.get(name)
    if preset is None:
        raise ValueError(f"Unknown SuperSource layout {name}")
    screen = int(roles.get("screen", 0))
    person1 = int(roles.get("person1", 0))
    person2 = int(roles.get("person2", 0))
    wide = int(roles.get("wide", 0))
    if preset.kind == "off":
        return BuiltLayout(preset.name, 0, (_off(), _off(), _off(), _off()))
    if preset.kind == "corner":
        source = {"wide": wide, "person1": person1, "person2": person2}[preset.box_role]
        x, y, size = _place_corner(adjustments.corner_size, adjustments.corner_margin, adjustments.corner)
        return BuiltLayout(
            preset.name,
            screen,
            (Box(True, source, x, y, size), _off(), _off(), _off()),
        )
    top, bottom = (person2, person1) if preset.swapped else (person1, person2)
    return BuiltLayout(
        preset.name,
        0,
        _stack(screen, top, bottom, cameras_on_right=preset.cameras_on_right, zoom=preset.zoom, column=adjustments.zoom_column),
    )


def csbp_payload(index: int, box: Box, ssrc: int = 0) -> bytes:
    """Firmware 8 `CSBP`. One box, every field masked, 24 bytes."""
    buf = bytearray(24)
    struct.pack_into(">H", buf, 0, _BOX_MASK)
    buf[2] = ssrc & 0xFF
    buf[3] = index & 0xFF
    buf[4] = 1 if box.enabled else 0
    struct.pack_into(">H", buf, 6, box.source & 0xFFFF)
    struct.pack_into(">h", buf, 8, _wire(box.x, 100, signed=True))
    struct.pack_into(">h", buf, 10, _wire(box.y, 100, signed=True))
    struct.pack_into(">H", buf, 12, _wire(box.size, 1000, signed=False))
    buf[14] = 1 if box.cropped else 0
    struct.pack_into(">H", buf, 16, _wire(box.crop_top, 1000, signed=False))
    struct.pack_into(">H", buf, 18, _wire(box.crop_bottom, 1000, signed=False))
    struct.pack_into(">H", buf, 20, _wire(box.crop_left, 1000, signed=False))
    struct.pack_into(">H", buf, 22, _wire(box.crop_right, 1000, signed=False))
    return bytes(buf)


def cssc_payload(fill: int, ssrc: int = 0, art_option: int = 0) -> bytes:
    """Firmware 8 `CSSc`. Art fill, plus whether that art sits behind the boxes."""
    buf = bytearray(16)
    buf[0] = _ART_MASK
    buf[1] = ssrc & 0xFF
    struct.pack_into(">H", buf, 2, fill & 0xFFFF)
    buf[6] = art_option & 0xFF
    return bytes(buf)


def layout_matches(state: AtemState, built: BuiltLayout) -> bool:
    """True when the parsed boxes (and art fill, if known) are this layout."""
    if (
        built.background is not None
        and state.supersource_art is not None
        and state.supersource_art != built.background
    ):
        return False
    if len(state.supersource_boxes) < 4:
        return False
    for index, box in enumerate(built.boxes):
        reported = state.supersource_boxes.get(index)
        if reported is None or not _same_box(reported, box):
            return False
    return True


def matching_preset(
    state: AtemState,
    roles: dict[str, int],
    adjustments: SuperSourceAdjustments,
    saved: dict[str, BuiltLayout] | None = None,
) -> str | None:
    hits = []
    for preset in PRESETS:
        try:
            built = build_preset(preset.name, roles, adjustments)
        except ValueError:
            continue
        if layout_matches(state, built):
            hits.append(preset.name)
    for name, built in (saved or {}).items():
        if layout_matches(state, built):
            hits.append(name)
    if adjustments.layout in hits:
        return adjustments.layout
    return hits[0] if hits else None


def visible_edges(box: Box) -> tuple[float, float, float, float]:
    """Left, right, bottom, top in the -16..16 / -9..9 frame. Y is up."""
    left = box.x - 16 * box.size + box.crop_left
    right = box.x + 16 * box.size - box.crop_right
    bottom = box.y - 9 * box.size + box.crop_bottom
    top = box.y + 9 * box.size - box.crop_top
    return left, right, bottom, top


def _stack(
    screen: int,
    top: int,
    bottom: int,
    *,
    cameras_on_right: bool,
    zoom: bool,
    column: float,
) -> tuple[Box, Box, Box, Box]:
    if zoom:
        column = clamp_zoom_column(column)
        screen_size = 1.0 - column
        cam_size = screen_size / 2.0
        crop = max(0.0, (32.0 * cam_size - 32.0 * column) / 2.0)
    else:
        column = 1.0 / 3.0
        screen_size = 2.0 / 3.0
        cam_size = 1.0 / 3.0
        crop = 0.0
    if cameras_on_right:
        screen_x = -16.0 + 16.0 * screen_size
        cam_x = 16.0 - 16.0 * column
    else:
        screen_x = 16.0 - 16.0 * screen_size
        cam_x = -16.0 + 16.0 * column
    dy = 9.0 * screen_size / 2.0
    return (
        Box(True, screen, screen_x, 0.0, screen_size),
        Box(True, top, cam_x, dy, cam_size, crop_left=crop, crop_right=crop),
        Box(True, bottom, cam_x, -dy, cam_size, crop_left=crop, crop_right=crop),
        _off(),
    )


def _place_corner(size: float, margin: float, corner: str) -> tuple[float, float, float]:
    size = clamp_corner_size(size)
    margin = clamp_corner_margin(margin)
    half_w = 16.0 * size
    half_h = 9.0 * size
    limit = max(0.0, min(16.0 - half_w, 9.0 - half_h))
    margin = min(margin, limit)
    sign_x, sign_y = _CORNER_SIGN.get(corner, (1, -1))
    return sign_x * (16.0 - half_w - margin), sign_y * (9.0 - half_h - margin), size


def _off() -> Box:
    return Box(False, 0, 0.0, 0.0, 0.5)


def _box_from_reported(info: dict) -> Box:
    return Box(
        enabled=bool(info.get("enabled")),
        source=int(info.get("source", 0)),
        x=float(info.get("x", 0.0)),
        y=float(info.get("y", 0.0)),
        size=float(info.get("size", 0.5)),
        crop_top=float(info.get("crop_top", 0.0)),
        crop_bottom=float(info.get("crop_bottom", 0.0)),
        crop_left=float(info.get("crop_left", 0.0)),
        crop_right=float(info.get("crop_right", 0.0)),
    )


def _same_box(reported: dict, box: Box) -> bool:
    if bool(reported.get("enabled")) != box.enabled:
        return False
    if not box.enabled:
        return True
    if int(reported.get("source", -1)) != box.source:
        return False
    return (
        _wire(float(reported.get("x", 0.0)), 100, signed=True) == _wire(box.x, 100, signed=True)
        and _wire(float(reported.get("y", 0.0)), 100, signed=True) == _wire(box.y, 100, signed=True)
        and _wire(float(reported.get("size", 0.0)), 1000, signed=False) == _wire(box.size, 1000, signed=False)
        and _wire(float(reported.get("crop_left", 0.0)), 1000, signed=False) == _wire(box.crop_left, 1000, signed=False)
        and _wire(float(reported.get("crop_right", 0.0)), 1000, signed=False) == _wire(box.crop_right, 1000, signed=False)
        and _wire(float(reported.get("crop_top", 0.0)), 1000, signed=False) == _wire(box.crop_top, 1000, signed=False)
        and _wire(float(reported.get("crop_bottom", 0.0)), 1000, signed=False) == _wire(box.crop_bottom, 1000, signed=False)
    )


def _wire(value: float, scale: int, *, signed: bool) -> int:
    raw = int(round(float(value) * scale))
    if signed:
        return max(-32768, min(32767, raw))
    return max(0, min(65535, raw))
