"""Selects: program, preview, aux, transition style, Fairlight mix option."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .catalog import (
    EntitySpec,
    mix_option_labels,
    programmable_labels,
    transition_style_options,
)
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import async_write, read_value


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    async_setup_platform_entities(hass, entry, async_add_entities, "select", AtemSelect)


class AtemSelect(AtemEntity, SelectEntity):
    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)

    @property
    def options(self) -> list[str]:
        state = self.coordinator.client.state
        if self._spec.kind in {"program", "preview", "aux"}:
            return programmable_labels(state)
        if self._spec.kind == "transition_style":
            return transition_style_options()
        if self._spec.kind == "mix":
            return mix_option_labels()
        return []

    @property
    def current_option(self) -> str | None:
        value = read_value(self.coordinator.client.state, self._spec)
        if value is None:
            return None
        return str(value)

    async def async_select_option(self, option: str) -> None:
        try:
            await async_write(self.coordinator.client, self._spec, option)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(str(err)) from err
