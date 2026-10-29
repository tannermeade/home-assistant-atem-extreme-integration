"""Switches: fade to black, keyers, record, stream, audio follow."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import async_write, read_value


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "switch", AtemSwitch)


class AtemSwitch(AtemEntity, SwitchEntity):
    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)

    @property
    def is_on(self) -> bool:
        return bool(read_value(self.coordinator.client.state, self._spec))

    async def async_turn_on(self, **kwargs) -> None:
        await self._write(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._write(False)

    async def _write(self, value: bool) -> None:
        try:
            await async_write(self.coordinator.client, self._spec, value)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(str(err)) from err
