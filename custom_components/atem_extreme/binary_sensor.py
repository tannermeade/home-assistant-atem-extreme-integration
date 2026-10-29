"""Binary sensors: tally, transitions, downstream-keyer animation."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import read_value


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "binary_sensor", AtemBinarySensor)


class AtemBinarySensor(AtemEntity, BinarySensorEntity):
    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)

    @property
    def is_on(self) -> bool:
        return bool(read_value(self.coordinator.client.state, self._spec))
