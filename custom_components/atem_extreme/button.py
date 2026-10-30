"""Buttons: cut, auto, fade to black, downstream keyer auto, take input."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import async_write


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "button", AtemButton)


class AtemButton(AtemEntity, ButtonEntity):
    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)

    async def async_press(self) -> None:
        try:
            if self._spec.kind == "ss_apply":
                await self.coordinator.async_apply_supersource()
            else:
                await async_write(self.coordinator.client, self._spec, True)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(str(err)) from err
