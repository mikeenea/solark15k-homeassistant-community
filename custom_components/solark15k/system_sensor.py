"""Combined x2 sensors for two parallel Sol-Ark 15K config entries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN

NumericValueFn = Callable[[dict[int, int]], int | float | None]

_X2_OWNER_KEY = "x2_sensor_owner"

SUM_KEYS: tuple[str, ...] = (
    "daily_pv_energy",
    "total_pv_energy",
    "pv1_current",
    "pv2_current",
    "pv3_current",
    "pv1_power",
    "pv2_power",
    "pv3_power",
    "pv_total_power",
    "daily_load_energy",
    "total_load_energy",
    "load_total_power",
    "daily_grid_import_energy",
    "daily_grid_export_energy",
    "total_grid_import_energy",
    "total_grid_export_energy",
    "grid_total_power",
    "grid_import_power",
    "grid_export_power",
    "generator_ac_coupled_power",
    "daily_battery_charge_energy",
    "daily_battery_discharge_energy",
    "total_battery_charge_energy",
    "total_battery_discharge_energy",
    "battery_power",
    "battery_charge_power",
    "battery_discharge_power",
    "battery_current",
)

MEAN_KEYS: tuple[str, ...] = (
    "pv1_voltage",
    "pv2_voltage",
    "pv3_voltage",
    "grid_l1_l2_voltage",
    "inverter_l1_l2_voltage",
    "generator_port_voltage",
    "generator_frequency",
    "load_frequency",
    "battery_voltage",
    "battery_soc",
)


@dataclass(frozen=True)
class X2SensorSpec:
    """Describe one combined x2 sensor."""

    description: SensorEntityDescription
    value_fn: NumericValueFn
    operation: str


def _s16(raw: int) -> int:
    return raw - 65536 if raw & 0x8000 else raw


def _sum_unsigned(addresses: tuple[int, ...], scale: float) -> NumericValueFn:
    def value(data: dict[int, int]) -> int | float | None:
        if any(address not in data for address in addresses):
            return None
        return sum(data[address] for address in addresses) * scale

    return value


def _sum_signed(addresses: tuple[int, ...], scale: float) -> NumericValueFn:
    def value(data: dict[int, int]) -> int | float | None:
        if any(address not in data for address in addresses):
            return None
        return sum(_s16(data[address]) for address in addresses) * scale

    return value


EXTRA_SPECS: tuple[X2SensorSpec, ...] = (
    X2SensorSpec(
        description=SensorEntityDescription(
            key="pv_total_current",
            name="PV total current",
            native_unit_of_measurement="A",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        value_fn=_sum_unsigned((110, 112, 114), 0.1),
        operation="sum",
    ),
    X2SensorSpec(
        description=SensorEntityDescription(
            key="load_total_current",
            name="Load total current",
            native_unit_of_measurement="A",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        value_fn=_sum_signed((179, 180), 0.01),
        operation="sum",
    ),
    X2SensorSpec(
        description=SensorEntityDescription(
            key="grid_total_current",
            name="Grid total current",
            native_unit_of_measurement="A",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        value_fn=_sum_signed((160, 161), 0.01),
        operation="sum",
    ),
)


def _build_specs(
    descriptions: Mapping[str, Any],
) -> tuple[X2SensorSpec, ...]:
    specs: list[X2SensorSpec] = []
    for key in SUM_KEYS:
        description = descriptions.get(key)
        if description is not None:
            specs.append(
                X2SensorSpec(description, description.value_fn, "sum")
            )
    for key in MEAN_KEYS:
        description = descriptions.get(key)
        if description is not None:
            specs.append(
                X2SensorSpec(description, description.value_fn, "mean")
            )
    specs.extend(EXTRA_SPECS)
    return tuple(specs)


async def async_setup_x2_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    descriptions: Mapping[str, Any],
) -> None:
    """Create one x2 device when exactly two inverter entries are active."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_X2_OWNER_KEY) is not None:
        return

    active_entries = [
        candidate
        for candidate in hass.config_entries.async_entries(DOMAIN)
        if getattr(candidate, "runtime_data", None) is not None
    ]
    if len(active_entries) != 2:
        return

    coordinators = tuple(
        candidate.runtime_data.coordinator for candidate in active_entries
    )
    domain_data[_X2_OWNER_KEY] = entry.entry_id

    @callback
    def clear_owner() -> None:
        if domain_data.get(_X2_OWNER_KEY) == entry.entry_id:
            domain_data.pop(_X2_OWNER_KEY, None)

    entry.async_on_unload(clear_owner)
    async_add_entities(
        SolArkX2Sensor(coordinators, spec) for spec in _build_specs(descriptions)
    )


class SolArkX2Sensor(SensorEntity):
    """A virtual sensor combining two physical inverter coordinators."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinators: tuple[Any, Any], spec: X2SensorSpec) -> None:
        self.coordinators = coordinators
        self.spec = spec
        self.entity_description = spec.description
        self._attr_unique_id = f"solark15k_x2_{spec.description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "x2")},
            name="Sol-Ark 15K x2",
            manufacturer="Sol-Ark",
            model="15K Parallel System",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates from both physical inverter coordinators."""
        await super().async_added_to_hass()
        for coordinator in self.coordinators:
            self.async_on_remove(
                coordinator.async_add_listener(self._handle_coordinator_update)
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Report available only when both inverter feeds are current."""
        return all(
            coordinator.last_update_success and coordinator.data is not None
            for coordinator in self.coordinators
        )

    @property
    def native_value(self) -> int | float | None:
        """Return the sum or arithmetic mean of both inverter values."""
        values: list[float] = []
        for coordinator in self.coordinators:
            if coordinator.data is None:
                return None
            value = self.spec.value_fn(coordinator.data)
            if value is None:
                return None
            values.append(float(value))

        result = sum(values)
        if self.spec.operation == "mean":
            result /= len(values)

        if all(value.is_integer() for value in values) and result.is_integer():
            return int(result)
        return result
