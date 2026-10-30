"""Binary sensors: tally, transitions, and per-strip talking."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .talk import is_talking
from .values import read_value, strip_level

_TALK_KINDS = {"talking", "classic_talking"}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "binary_sensor", AtemBinarySensor)


class AtemBinarySensor(AtemEntity, BinarySensorEntity):
    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)
        if spec.kind in _TALK_KINDS:
            self._attr_device_class = BinarySensorDeviceClass.SOUND

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._spec.kind in _TALK_KINDS:
            self.async_on_remove(
                self.coordinator.meters.async_add_listener(self._handle_coordinator_update)
            )

    @property
    def is_on(self) -> bool:
        if self._spec.kind in _TALK_KINDS:
            return is_talking(self._level(), self.coordinator.talk_threshold(self._spec.address))
        return bool(read_value(self.coordinator.client.state, self._spec))

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes
        if self._spec.kind not in _TALK_KINDS:
            return attrs
        merged = dict(attrs)
        merged["level_db"] = self._level()
        merged["threshold_db"] = self.coordinator.talk_threshold(self._spec.address)
        return merged

    def _level(self) -> float | None:
        return strip_level(self.coordinator.client.state, self._spec)
