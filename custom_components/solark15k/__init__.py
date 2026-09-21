"""Sol-Ark 15K Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

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
    DOMAIN,
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


def _remove_obsolete_tou_time_entities(
    hass: HomeAssistant, entry: SolArkConfigEntry
) -> None:
    """Remove beta-2 time entities replaced by beta-3 HHMM number boxes."""
    registry = er.async_get(hass)
    unique_prefix = f"{entry.entry_id}_tou_time_point_"
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.entity_id.startswith("time.")
            and entity.platform == DOMAIN
            and entity.unique_id.startswith(unique_prefix)
        ):
            registry.async_remove(entity.entity_id)


def _migrate_control_entity_ids(
    hass: HomeAssistant, entry: SolArkConfigEntry
) -> None:
    """Normalize beta configuration entity IDs without touching custom IDs."""
    registry = er.async_get(hass)
    tou_prefix = f"{entry.entry_id}_tou_"
    generator_unique_id = f"{entry.entry_id}_generator_charge"
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform != DOMAIN or not (
            entity.unique_id.startswith(tou_prefix)
            or entity.unique_id == generator_unique_id
        ):
            continue

        new_entity_id = entity.entity_id.removesuffix("_hhmm")
        for entity_domain in ("number", "switch"):
            duplicate_prefix = f"{entity_domain}.solar_sol_ark_"
            if new_entity_id.startswith(duplicate_prefix):
                new_entity_id = (
                    f"{entity_domain}.sol_ark_"
                    f"{new_entity_id[len(duplicate_prefix):]}"
                )
                break

        if new_entity_id != entity.entity_id and registry.async_get(new_entity_id) is None:
            registry.async_update_entity(
                entity.entity_id, new_entity_id=new_entity_id
            )


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
    _remove_obsolete_tou_time_entities(hass, entry)
    _migrate_control_entity_ids(hass, entry)
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
