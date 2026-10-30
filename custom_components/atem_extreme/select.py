"""Selects: program, preview, aux, transition style, Fairlight mix, SuperSource."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.restore_state import RestoreEntity

from .catalog import (
    EntitySpec,
    label_to_source,
    mix_option_labels,
    programmable_labels,
    source_to_label,
    transition_style_options,
)
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .supersource import CORNERS
from .values import async_write, read_value

_UNKNOWN = {"unknown", "unavailable", ""}


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    def factory(coordinator: AtemCoordinator, spec: EntitySpec):
        if spec.kind in {"ss_layout", "ss_role", "ss_corner"}:
            return AtemSuperSourceSelect(coordinator, spec)
        return AtemSelect(coordinator, spec)

    async_setup_platform_entities(hass, entry, async_add_entities, "select", factory)


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


class AtemSuperSourceSelect(AtemEntity, RestoreEntity, SelectEntity):
    """Layout push, or a local role/corner that waits for the next push."""

    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)

    @property
    def available(self) -> bool:
        if self._spec.kind == "ss_corner":
            return True
        return self.coordinator.client.connected

    @property
    def options(self) -> list[str]:
        if self._spec.kind == "ss_layout":
            return self.coordinator.layout_names()
        if self._spec.kind == "ss_corner":
            return list(CORNERS)
        labels = programmable_labels(self.coordinator.client.state)
        current = self.current_option
        if current and current not in labels:
            return [current, *labels]
        return labels

    @property
    def current_option(self) -> str | None:
        kind = self._spec.kind
        if kind == "ss_layout":
            return self.coordinator.ss.layout
        if kind == "ss_corner":
            return self.coordinator.ss.corner
        role = self._spec.address[0]
        source = self.coordinator.resolved_roles()[role]
        return source_to_label(self.coordinator.client.state, source) or f"Source {source}"

    @property
    def extra_state_attributes(self) -> dict:
        if self._spec.kind != "ss_layout":
            return {}
        return self.coordinator.supersource_attributes()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state in _UNKNOWN:
            return
        kind = self._spec.kind
        if kind == "ss_layout" and last.state in self.coordinator.layout_names():
            self.coordinator.remember_supersource_layout(last.state)
        elif kind == "ss_corner" and last.state in CORNERS:
            self.coordinator.set_supersource_corner(last.state)
        elif kind == "ss_role":
            source = label_to_source(self.coordinator.client.state, last.state)
            if source is not None:
                self.coordinator.set_supersource_role(self._spec.address[0], source)

    async def async_select_option(self, option: str) -> None:
        try:
            kind = self._spec.kind
            if kind == "ss_layout":
                await self.coordinator.async_apply_supersource(option)
            elif kind == "ss_corner":
                if option not in CORNERS:
                    raise ValueError(f"Unknown corner {option}")
                self.coordinator.set_supersource_corner(option)
            elif kind == "ss_role":
                source = label_to_source(self.coordinator.client.state, option)
                if source is None:
                    raise ValueError(f"Unknown input {option}")
                self.coordinator.set_supersource_role(self._spec.address[0], source)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(str(err)) from err