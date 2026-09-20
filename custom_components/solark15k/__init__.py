"""Sol-Ark 15K Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_DETAIL_INTERVAL,
    CONF_ENERGY_INTERVAL,
    CONF_FAULT_INTERVAL,
    CONF_INTER_REQUEST_DELAY,
    CONF_LIVE_INTERVAL,
    CONF_MIN_REQUEST_SPACING,
    CONF_REQUEST_TIMEOUT,
    CONF_RETRIES,
    CONF_SLAVE_ID,
    DEFAULT_DETAIL_INTERVAL,
    DEFAULT_ENERGY_INTERVAL,
    DEFAULT_FAULT_INTERVAL,
    DEFAULT_INTER_REQUEST_DELAY,
    DEFAULT_LIVE_INTERVAL,
    DEFAULT_MIN_REQUEST_SPACING,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRIES,
    DEFAULT_SLAVE_ID,
    MASTER_SLAVE_ID,
    PLATFORMS,
)
from .coordinator import SolArkDataUpdateCoordinator
from .influx_fastpath import SolArkInfluxFastPath
from .modbus_client import SolArkModbusClient, SolArkModbusError


@dataclass
class SolArkRuntimeData:
    """Runtime objects for one configured inverter."""

    client: SolArkModbusClient
    coordinator: SolArkDataUpdateCoordinator
    influx_fastpath: SolArkInfluxFastPath


type SolArkConfigEntry = ConfigEntry[SolArkRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SolArkConfigEntry) -> bool:
    """Set up a Sol-Ark 15K config entry."""
    timeout = float(entry.options.get(CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT))
    retry_delay = float(
        entry.options.get(CONF_INTER_REQUEST_DELAY, DEFAULT_INTER_REQUEST_DELAY)
    )
    retries = int(entry.options.get(CONF_RETRIES, DEFAULT_RETRIES))
    minimum_request_spacing = float(
        entry.options.get(CONF_MIN_REQUEST_SPACING, DEFAULT_MIN_REQUEST_SPACING)
    )
    live_interval = float(
        entry.options.get(CONF_LIVE_INTERVAL, DEFAULT_LIVE_INTERVAL)
    )
    fault_interval = float(
        entry.options.get(CONF_FAULT_INTERVAL, DEFAULT_FAULT_INTERVAL)
    )
    detail_interval = float(
        entry.options.get(CONF_DETAIL_INTERVAL, DEFAULT_DETAIL_INTERVAL)
    )
    energy_interval = float(
        entry.options.get(CONF_ENERGY_INTERVAL, DEFAULT_ENERGY_INTERVAL)
    )

    client = SolArkModbusClient(
        host=entry.data[CONF_HOST],
        port=int(entry.data[CONF_PORT]),
        slave_id=int(entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)),
        timeout=timeout,
    )

    # Fast setup test: prove the TCP/RTU path with one known live register rather
    # than blocking Home Assistant startup for a complete scan.
    try:
        battery_voltage = await client.async_read_holding(183, 1)
    except SolArkModbusError as err:
        await client.async_close()
        raise ConfigEntryNotReady(
            f"Unable to read Sol-Ark register 183 at {entry.data[CONF_HOST]}: "
            f"{err}"
        ) from err

    coordinator = SolArkDataUpdateCoordinator(
        hass,
        client,
        retry_delay=retry_delay,
        retries=retries,
        minimum_request_spacing=minimum_request_spacing,
        live_interval=live_interval,
        fault_interval=fault_interval,
        detail_interval=detail_interval,
        energy_interval=energy_interval,
        include_settings=client.slave_id == MASTER_SLAVE_ID,
        name=entry.title,
    )
    coordinator.seed_registers({183: battery_voltage[0]})

    # Home Assistant's normal InfluxDB writer queues every state_changed event
    # before applying its include filter. The fast path reuses the existing
    # InfluxDB filter/configuration and immediately writes only this config
    # entry's matching numeric sensor events to InfluxDB 2.x.
    influx_fastpath = SolArkInfluxFastPath(hass, entry.entry_id)
    await influx_fastpath.async_start()

    entry.runtime_data = SolArkRuntimeData(
        client=client,
        coordinator=coordinator,
        influx_fastpath=influx_fastpath,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SolArkConfigEntry) -> bool:
    """Unload a Sol-Ark 15K config entry."""
    await entry.runtime_data.coordinator.async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.influx_fastpath.async_close()
        await entry.runtime_data.client.async_close()
    else:
        await entry.runtime_data.coordinator.async_start()
    return unload_ok
