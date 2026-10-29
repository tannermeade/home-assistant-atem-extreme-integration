"""Numbers: transition rates and Fairlight faders."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import async_write, read_value


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "number", AtemNumber)


class AtemNumber(AtemEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)
        self._attr_native_min_value = spec.min_value if spec.min_value is not None else 0
        self._attr_native_max_value = spec.max_value if spec.max_value is not None else 100
        self._attr_native_step = spec.step if spec.step is not None else 1
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.unit == "dB":
            self._attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float | None:
        value = read_value(self.coordinator.client.state, self._spec)
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        try:
            await async_write(self.coordinator.client, self._spec, value)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(str(err)) from err
