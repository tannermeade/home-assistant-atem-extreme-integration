"""Numbers: transition rates, Fairlight faders, and local talking thresholds."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .catalog import EntitySpec
from .coordinator import AtemCoordinator
from .entity import AtemEntity
from .platforms import async_setup_platform_entities
from .values import async_write, read_value


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities) -> None:
    def factory(coordinator: AtemCoordinator, spec: EntitySpec):
        if spec.kind == "talk_threshold":
            return AtemTalkThreshold(coordinator, spec)
        if spec.kind == "ss_tweak":
            return AtemSuperSourceNumber(coordinator, spec)
        return AtemNumber(coordinator, spec)

    async_setup_platform_entities(hass, entry, async_add_entities, "number", factory)


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


class AtemTalkThreshold(AtemEntity, RestoreNumber):
    """Per-strip dB threshold. Not written to the switcher."""

    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)
        self._attr_native_min_value = spec.min_value if spec.min_value is not None else -100
        self._attr_native_max_value = spec.max_value if spec.max_value is not None else 6
        self._attr_native_step = spec.step if spec.step is not None else 0.5
        self._attr_native_unit_of_measurement = "dB"

    @property
    def available(self) -> bool:
        # Local setting. It stays adjustable if the switcher drops offline.
        return True

    @property
    def native_value(self) -> float:
        return self.coordinator.talk_threshold(self._spec.address)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self.coordinator.set_talk_threshold(self._spec.address, float(last.native_value))

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_talk_threshold(self._spec.address, value)
        # The number service does not write state. Without this, the slider
        # is redrawn from the previous state and snaps back to -40.
        self.async_write_ha_state()


class AtemSuperSourceNumber(AtemEntity, RestoreNumber):
    """Corner size, margin, or zoom column. Stored here until a layout is pushed."""

    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AtemCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)
        self._attr_native_min_value = spec.min_value if spec.min_value is not None else 0
        self._attr_native_max_value = spec.max_value if spec.max_value is not None else 1
        self._attr_native_step = spec.step if spec.step is not None else 0.01

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        field = self._spec.address[0]
        return float(getattr(self.coordinator.ss, field))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self.coordinator.set_supersource_number(self._spec.address[0], float(last.native_value))

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_supersource_number(self._spec.address[0], value)
        self.async_write_ha_state()
