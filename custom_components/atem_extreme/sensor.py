"""Sensors: Fairlight meters and read-only status."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import read_value

_METER_KINDS = {"level", "classic_level", "master_level"}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "sensor", AtemSensor)


class AtemSensor(AtemEntity, SensorEntity):
    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.unit == "dB":
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 1
        elif spec.unit == "bit/s":
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._spec.kind in _METER_KINDS:
            self.async_on_remove(
                self.coordinator.meters.async_add_listener(self._handle_coordinator_update)
            )

    @property
    def native_value(self):
        return read_value(self.coordinator.client.state, self._spec)
