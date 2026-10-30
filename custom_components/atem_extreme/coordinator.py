"""Push coordinator. The switcher is not polled; meters are sampled down."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .atem.client import AtemClient
from .atem.state import AtemState
from .const import CONF_HOST, CONF_METER_HZ, CONF_PORT, DEFAULT_METER_HZ, DOMAIN
from .supersource import (
    SuperSourceAdjustments,
    build_preset,
    clamp_corner_margin,
    clamp_corner_size,
    clamp_zoom_column,
    default_roles,
    matching_preset,
)
from .talk import DEFAULT_TALK_THRESHOLD_DB, clamp_talk_threshold

_LOGGER = logging.getLogger(__name__)


class AtemCoordinator(DataUpdateCoordinator[AtemState]):
    """Holds the switcher client and fans state out to entities."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.entry = entry
        self.entry_id = entry.entry_id
        self.meter_hz = int(
            entry.options.get(CONF_METER_HZ, entry.data.get(CONF_METER_HZ, DEFAULT_METER_HZ))
        )
        self.meters: DataUpdateCoordinator[float] = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_meters",
            update_interval=None,
        )
        self.client = AtemClient(
            entry.data[CONF_HOST],
            int(entry.data[CONF_PORT]),
            on_state=self._on_state,
            on_connection=self._on_connection,
        )
        self._meter_unsub = None
        # Local only. Keyed by the strip address the level sensor uses.
        self.talk_thresholds: dict[tuple, float] = {}
        self.ss = SuperSourceAdjustments()

    def talk_threshold(self, address: tuple) -> float:
        return self.talk_thresholds.get(address, DEFAULT_TALK_THRESHOLD_DB)

    def set_talk_threshold(self, address: tuple, value: float) -> None:
        self.talk_thresholds[address] = clamp_talk_threshold(value)
        # Talking sensors listen to the meter coordinator, so a threshold
        # change updates them even when the switcher has not sent a new sample.
        self.meters.async_set_updated_data(self.hass.loop.time())

    def resolved_roles(self) -> dict[str, int]:
        defaults = default_roles(self.client.state)
        resolved: dict[str, int] = {}
        known = self.client.state.inputs
        for role, fallback in defaults.items():
            chosen = self.ss.roles.get(role)
            if chosen is None or (chosen not in known and chosen != 0):
                resolved[role] = fallback
            else:
                resolved[role] = chosen
        return resolved

    def set_supersource_role(self, role: str, source: int) -> None:
        self.ss.roles[role] = source
        self._refresh_local()

    def set_supersource_corner(self, corner: str) -> None:
        self.ss.corner = corner
        self._refresh_local()

    def set_supersource_number(self, field: str, value: float) -> None:
        if field == "corner_size":
            self.ss.corner_size = clamp_corner_size(value)
        elif field == "corner_margin":
            self.ss.corner_margin = clamp_corner_margin(value)
        elif field == "zoom_column":
            self.ss.zoom_column = clamp_zoom_column(value)
        else:
            raise ValueError(f"Unknown SuperSource setting {field}")
        self._refresh_local()

    def remember_supersource_layout(self, name: str) -> None:
        """Restore the last choice without sending it to the switcher."""
        self.ss.layout = name
        self._refresh_local()

    async def async_apply_supersource(self, layout: str | None = None) -> None:
        name = layout if layout is not None else self.ss.layout
        if not name:
            raise ValueError("Select a SuperSource layout first")
        built = build_preset(name, self.resolved_roles(), self.ss)
        await self.client.apply_supersource(built.background, built.boxes)
        self.ss.layout = name
        _LOGGER.info("Applied SuperSource layout %s on %s", name, self.client.host)
        self._refresh_local()

    def supersource_attributes(self) -> dict:
        roles = self.resolved_roles()
        state = self.client.state
        on_switcher = matching_preset(state, roles, self.ss)
        return {
            "on_switcher": on_switcher or ("custom" if state.supersource_boxes else "unknown"),
            "matches_switcher": on_switcher is not None and on_switcher == self.ss.layout,
            "changes_program": False,
            "screen": state.input_label(roles["screen"]),
            "person_1": state.input_label(roles["person1"]),
            "person_2": state.input_label(roles["person2"]),
            "wide": state.input_label(roles["wide"]),
            "corner": self.ss.corner,
            "corner_size": self.ss.corner_size,
            "corner_margin": self.ss.corner_margin,
            "zoom_column": self.ss.zoom_column,
            "untested_on_hardware": True,
        }

    def _refresh_local(self) -> None:
        self.async_set_updated_data(self.client.snapshot())

    async def async_start(self) -> None:
        await self.client.start()
        await self.client.wait_until_ready(12)
        self.async_set_updated_data(self.client.snapshot())
        interval = timedelta(seconds=1.0 / self.meter_hz)
        self._meter_unsub = async_track_time_interval(self.hass, self._publish_meters, interval)

    async def async_shutdown(self) -> None:
        if self._meter_unsub:
            self._meter_unsub()
            self._meter_unsub = None
        await self.client.stop()

    def _on_state(self, client: AtemClient) -> None:
        self.async_set_updated_data(client.snapshot())

    def _on_connection(self, connected: bool) -> None:
        _LOGGER.info("ATEM %s %s", self.client.host, "connected" if connected else "disconnected")
        # Notify even when the snapshot is unchanged so availability flips.
        self.async_set_updated_data(self.client.snapshot())

    async def _publish_meters(self, _now) -> None:
        if not self.client.connected:
            return
        # The payload is only a tick. Sensors read the live meter values so a
        # quiet input still resolves, and we never store 10 Hz history.
        self.meters.async_set_updated_data(self.hass.loop.time())
