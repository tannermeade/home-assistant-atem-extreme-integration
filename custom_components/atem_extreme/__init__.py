"""ATEM Mini Extreme ISO integration.

Home Assistant imports stay inside the setup functions so the protocol
package can be unit-tested without Home Assistant installed.
"""

from __future__ import annotations

from .const import DOMAIN

PLATFORMS: list[str] = [
    "binary_sensor",
    "button",
    "number",
    "select",
    "sensor",
    "switch",
    "text",
]


async def async_setup_entry(hass, entry) -> bool:
    from homeassistant.exceptions import ConfigEntryNotReady

    from .atem.client import AtemConnectionError, SwitcherFullyBooked
    from .coordinator import AtemCoordinator

    coordinator = AtemCoordinator(hass, entry)
    try:
        await coordinator.async_start()
    except (AtemConnectionError, SwitcherFullyBooked, TimeoutError) as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(f"Cannot connect to ATEM: {err}") from err
    except Exception as err:  # noqa: BLE001
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(f"Cannot connect to ATEM: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass, entry) -> bool:
    from .coordinator import AtemCoordinator

    unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload:
        coordinator: AtemCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload


async def _reload(hass, entry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
