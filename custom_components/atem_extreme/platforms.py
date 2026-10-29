"""Add catalog entities for one platform, including ones that show up later."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback

from .catalog import EntitySpec, build_specs
from .const import DOMAIN
from .coordinator import AtemCoordinator


def async_setup_platform_entities(
    hass: HomeAssistant,
    entry,
    async_add_entities: Callable,
    platform: str,
    factory: Callable[[AtemCoordinator, EntitySpec], object],
) -> None:
    coordinator: AtemCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _sync() -> None:
        fresh = []
        for spec in build_specs(coordinator.client.state):
            if spec.platform != platform or spec.key in known:
                continue
            known.add(spec.key)
            fresh.append(factory(coordinator, spec))
        if fresh:
            async_add_entities(fresh)

    _sync()
    entry.async_on_unload(coordinator.async_add_listener(_sync))
