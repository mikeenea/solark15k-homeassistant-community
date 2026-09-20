"""Shared support for development-only Sol-Ark configuration entities."""

from __future__ import annotations

import logging

from homeassistant.exceptions import HomeAssistantError

from . import SolArkConfigEntry
from .modbus_client import SolArkModbusError

_LOGGER = logging.getLogger(__name__)


def cached_register(entry: SolArkConfigEntry, address: int) -> int | None:
    """Return a configuration value from the coordinator cache."""
    data = entry.runtime_data.coordinator.data
    if data is None:
        return None
    return data.get(address)


async def async_write_verified_register(
    entry: SolArkConfigEntry,
    *,
    address: int,
    value: int,
    expected: int,
    control_name: str,
) -> None:
    """Write one master register with FC16 and publish verified read-back."""
    try:
        actual = await entry.runtime_data.client.async_write_holding_one(
            address, value, expected=expected
        )
    except SolArkModbusError as err:
        raise HomeAssistantError(
            f"Unable to set {control_name}: {err}. Refresh the entity and try again."
        ) from err

    entry.runtime_data.coordinator.publish_register(address, actual)
    _LOGGER.warning(
        "Sol-Ark master setting changed: %s register %s from %s to %s; "
        "confirm the inverter display and parallel-slave inheritance",
        control_name,
        address,
        expected,
        actual,
    )
