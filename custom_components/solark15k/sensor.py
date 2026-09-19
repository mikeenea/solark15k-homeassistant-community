"""Sensor platform for Sol-Ark 15K Modbus telemetry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SolArkConfigEntry
from .calculations import signed_16, unsigned_32
from .const import DOMAIN
from .coordinator import SolArkDataUpdateCoordinator
from .system_sensor import async_setup_x2_sensors

ValueFn = Callable[[dict[int, int]], int | float | None]


def _u(address: int, scale: float = 1.0, offset: float = 0.0) -> ValueFn:
    def value(data: dict[int, int]) -> int | float | None:
        if address not in data:
            return None
        raw = data[address]
        result = raw * scale + offset
        return int(result) if scale == 1.0 and offset == 0.0 else result

    return value


def _s(address: int, scale: float = 1.0) -> ValueFn:
    def value(data: dict[int, int]) -> int | float | None:
        if address not in data:
            return None
        result = signed_16(data[address]) * scale
        return int(result) if scale == 1.0 else result

    return value


def _u32(low: int, high: int, scale: float = 1.0) -> ValueFn:
    def value(data: dict[int, int]) -> int | float | None:
        if low not in data or high not in data:
            return None
        result = unsigned_32(data[low], data[high]) * scale
        return int(result) if scale == 1.0 else result

    return value


def _sum(addresses: tuple[int, ...]) -> ValueFn:
    def value(data: dict[int, int]) -> int | None:
        if any(address not in data for address in addresses):
            return None
        return sum(data[address] for address in addresses)

    return value


def _positive_signed(address: int) -> ValueFn:
    def value(data: dict[int, int]) -> int | None:
        if address not in data:
            return None
        return max(signed_16(data[address]), 0)

    return value


def _negative_signed(address: int) -> ValueFn:
    def value(data: dict[int, int]) -> int | None:
        if address not in data:
            return None
        return max(-signed_16(data[address]), 0)

    return value


def _low_nibble(address: int) -> ValueFn:
    def value(data: dict[int, int]) -> int | None:
        if address not in data:
            return None
        return data[address] & 0x000F

    return value


@dataclass(frozen=True, kw_only=True)
class SolArkSensorDescription(SensorEntityDescription):
    """Describe a Sol-Ark sensor derived from coordinator register data."""

    value_fn: ValueFn


SENSORS: tuple[SolArkSensorDescription, ...] = (
    SolArkSensorDescription(
        key="grid_frequency",
        name="Grid frequency",
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_u(79, 0.01),
    ),
    SolArkSensorDescription(
        key="daily_battery_charge_energy",
        name="Daily battery charge energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_u(70, 0.1),
    ),
    SolArkSensorDescription(
        key="daily_battery_discharge_energy",
        name="Daily battery discharge energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_u(71, 0.1),
    ),
    SolArkSensorDescription(
        key="total_battery_charge_energy",
        name="Total battery charge energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_u32(72, 73, 0.1),
    ),
    SolArkSensorDescription(
        key="total_battery_discharge_energy",
        name="Total battery discharge energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_u32(74, 75, 0.1),
    ),
    SolArkSensorDescription(
        key="daily_grid_import_energy",
        name="Daily grid import energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_u(76, 0.1),
    ),
    SolArkSensorDescription(
        key="daily_grid_export_energy",
        name="Daily grid export energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_u(77, 0.1),
    ),
    SolArkSensorDescription(
        key="total_grid_import_energy",
        name="Total grid import energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_u32(78, 80, 0.1),
    ),
    SolArkSensorDescription(
        key="total_grid_export_energy",
        name="Total grid export energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_u32(81, 82, 0.1),
    ),
    SolArkSensorDescription(
        key="daily_load_energy",
        name="Daily load energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_u(84, 0.1),
    ),
    SolArkSensorDescription(
        key="total_load_energy",
        name="Total load energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_u32(85, 86, 0.1),
    ),
    SolArkSensorDescription(
        key="heat_sink_temperature",
        name="Heat sink temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_u(91, 0.1, -100.0),
    ),
    SolArkSensorDescription(
        key="total_pv_energy",
        name="Total PV energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_u32(96, 97, 0.1),
    ),
    SolArkSensorDescription(key="fault_word_1", name="Fault word 1", value_fn=_u(103)),
    SolArkSensorDescription(key="fault_word_2", name="Fault word 2", value_fn=_u(104)),
    SolArkSensorDescription(key="fault_word_3", name="Fault word 3", value_fn=_u(105)),
    SolArkSensorDescription(key="fault_word_4", name="Fault word 4", value_fn=_u(106)),
    SolArkSensorDescription(
        key="corrected_battery_capacity",
        name="Corrected battery capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_u(107),
    ),
    SolArkSensorDescription(
        key="daily_pv_energy",
        name="Daily PV energy",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_u(108, 0.1),
    ),
    SolArkSensorDescription(
        key="pv1_voltage", name="PV1 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(109, 0.1),
    ),
    SolArkSensorDescription(
        key="pv1_current", name="PV1 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(110, 0.1),
    ),
    SolArkSensorDescription(
        key="pv2_voltage", name="PV2 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(111, 0.1),
    ),
    SolArkSensorDescription(
        key="pv2_current", name="PV2 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(112, 0.1),
    ),
    SolArkSensorDescription(
        key="pv3_voltage", name="PV3 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(113, 0.1),
    ),
    SolArkSensorDescription(
        key="pv3_current", name="PV3 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(114, 0.1),
    ),
    SolArkSensorDescription(
        key="grid_l1_n_voltage", name="Grid L1-N voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(150, 0.1),
    ),
    SolArkSensorDescription(
        key="grid_l2_n_voltage", name="Grid L2-N voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(151, 0.1),
    ),
    SolArkSensorDescription(
        key="grid_l1_l2_voltage", name="Grid L1-L2 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(152, 0.1),
    ),
    SolArkSensorDescription(
        key="inverter_l1_n_voltage", name="Inverter L1-N voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(154, 0.1),
    ),
    SolArkSensorDescription(
        key="inverter_l2_n_voltage", name="Inverter L2-N voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(155, 0.1),
    ),
    SolArkSensorDescription(
        key="inverter_l1_l2_voltage", name="Inverter L1-L2 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(156, 0.1),
    ),
    SolArkSensorDescription(
        key="load_l1_voltage", name="Load L1 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(157, 0.1),
    ),
    SolArkSensorDescription(
        key="load_l2_voltage", name="Load L2 voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(158, 0.1),
    ),
    SolArkSensorDescription(
        key="grid_l1_current", name="Grid L1 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(160, 0.01),
    ),
    SolArkSensorDescription(
        key="grid_l2_current", name="Grid L2 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(161, 0.01),
    ),
    SolArkSensorDescription(
        key="inverter_l1_current", name="Inverter L1 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(164, 0.01),
    ),
    SolArkSensorDescription(
        key="inverter_l2_current", name="Inverter L2 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(165, 0.01),
    ),
    SolArkSensorDescription(
        key="generator_ac_coupled_power", name="Generator / AC-coupled power",
        native_unit_of_measurement="W", device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT, value_fn=_s(166),
    ),
    SolArkSensorDescription(
        key="grid_l1_power", name="Grid L1 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(167),
    ),
    SolArkSensorDescription(
        key="grid_l2_power", name="Grid L2 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(168),
    ),
    SolArkSensorDescription(
        key="grid_total_power", name="Grid total power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(169),
    ),
    SolArkSensorDescription(
        key="grid_import_power", name="Grid import power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_positive_signed(169),
    ),
    SolArkSensorDescription(
        key="grid_export_power", name="Grid export power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_negative_signed(169),
    ),
    SolArkSensorDescription(
        key="inverter_l1_power", name="Inverter L1 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(173),
    ),
    SolArkSensorDescription(
        key="inverter_l2_power", name="Inverter L2 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(174),
    ),
    SolArkSensorDescription(
        key="inverter_total_power", name="Inverter total power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(175),
    ),
    SolArkSensorDescription(
        key="load_l1_power", name="Load L1 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(176),
    ),
    SolArkSensorDescription(
        key="load_l2_power", name="Load L2 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(177),
    ),
    SolArkSensorDescription(
        key="load_total_power", name="Load total power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(178),
    ),
    SolArkSensorDescription(
        key="load_l1_current", name="Load L1 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(179, 0.01),
    ),
    SolArkSensorDescription(
        key="load_l2_current", name="Load L2 current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(180, 0.01),
    ),
    SolArkSensorDescription(
        key="generator_port_voltage", name="Generator port voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(181, 0.1),
    ),
    SolArkSensorDescription(
        key="battery_temperature", name="Battery temperature", native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, value_fn=_u(182, 0.1, -100.0),
    ),
    SolArkSensorDescription(
        key="battery_voltage", name="Battery voltage", native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_u(183, 0.01),
    ),
    SolArkSensorDescription(
        key="battery_soc", name="Battery state of charge", native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_u(184),
    ),
    SolArkSensorDescription(
        key="pv1_power", name="PV1 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_u(186),
    ),
    SolArkSensorDescription(
        key="pv2_power", name="PV2 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_u(187),
    ),
    SolArkSensorDescription(
        key="pv3_power", name="PV3 power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_u(188),
    ),
    SolArkSensorDescription(
        key="pv_total_power", name="PV total power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_sum((186, 187, 188)),
    ),
    SolArkSensorDescription(
        key="battery_power", name="Battery power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_s(190),
    ),
    SolArkSensorDescription(
        key="battery_discharge_power", name="Battery discharge power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_positive_signed(190),
    ),
    SolArkSensorDescription(
        key="battery_charge_power", name="Battery charge power", native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER, state_class=SensorStateClass.MEASUREMENT,
        value_fn=_negative_signed(190),
    ),
    SolArkSensorDescription(
        key="battery_current", name="Battery current", native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_s(191, 0.01),
    ),
    SolArkSensorDescription(
        key="load_frequency", name="Load frequency", native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_u(192, 0.01),
    ),
    SolArkSensorDescription(
        key="inverter_frequency", name="Inverter frequency", native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_u(193, 0.01),
    ),
    SolArkSensorDescription(key="grid_relay_raw", name="Grid relay raw", value_fn=_u(194)),
    SolArkSensorDescription(key="generator_relay_raw", name="Generator relay raw", value_fn=_u(195)),
    SolArkSensorDescription(
        key="generator_relay_low_nibble", name="Generator relay low nibble", value_fn=_low_nibble(195)
    ),
    SolArkSensorDescription(
        key="generator_frequency", name="Generator frequency", native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY, state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2, value_fn=_u(196, 0.01),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolArkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Sol-Ark sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        SolArkSensor(coordinator, entry, description) for description in SENSORS
    )
    await async_setup_x2_sensors(
        hass,
        entry,
        async_add_entities,
        {description.key: description for description in SENSORS},
    )


class SolArkSensor(CoordinatorEntity[SolArkDataUpdateCoordinator], SensorEntity):
    """One sensor backed by the shared Sol-Ark coordinator cache."""

    _attr_has_entity_name = True
    entity_description: SolArkSensorDescription

    def __init__(
        self,
        coordinator: SolArkDataUpdateCoordinator,
        entry: SolArkConfigEntry,
        description: SolArkSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Sol-Ark",
            model="15K Hybrid Inverter",
        )

    @property
    def native_value(self) -> int | float | None:
        """Return the value derived from the latest shared register cache."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
