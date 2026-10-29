"""Shared Home Assistant entity base."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import EntitySpec
from .const import DOMAIN
from .coordinator import AtemCoordinator


class AtemEntity(CoordinatorEntity[AtemCoordinator]):
    """An entity bound to one catalog spec."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._attr_unique_id = f"{coordinator.entry_id}_{spec.key}"
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        if spec.entity_category:
            from homeassistant.helpers.entity import EntityCategory

            self._attr_entity_category = {
                "diagnostic": EntityCategory.DIAGNOSTIC,
                "config": EntityCategory.CONFIG,
            }[spec.entity_category]

    @property
    def available(self) -> bool:
        return self.coordinator.client.connected

    @property
    def device_info(self) -> DeviceInfo:
        state = self.coordinator.client.state
        model = state.product_name or "ATEM switcher"
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry_id)},
            manufacturer="Blackmagic Design",
            model=model,
            name=model,
            sw_version=state.protocol_version or None,
        )

    @property
    def extra_state_attributes(self) -> dict:
        from .values import extra_attributes

        return extra_attributes(self.coordinator.client.state, self._spec)
