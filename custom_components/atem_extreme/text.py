"""Text: the name used when saving the switcher's current SuperSource."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .supersource import MAX_LAYOUT_NAME

_UNKNOWN = {"unknown", "unavailable", ""}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "text", AtemSuperSourceName)


class AtemSuperSourceName(AtemEntity, RestoreEntity, TextEntity):
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = MAX_LAYOUT_NAME

    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self.coordinator.ss.save_name

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state in _UNKNOWN:
            return
        self.coordinator.set_supersource_name(last.state)

    async def async_set_value(self, value: str) -> None:
        self.coordinator.set_supersource_name(value)
