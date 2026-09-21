"""Development-only numeric configuration controls for Sol-Ark 15K."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SolArkConfigEntry
from .const import DOMAIN, MASTER_SLAVE_ID
from .control import async_write_verified_register, cached_register
from .coordinator import SolArkDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class SolArkNumberDescription(NumberEntityDescription):
    """Describe one validated writable numeric register."""

    address: int


NUMBERS: tuple[SolArkNumberDescription, ...] = tuple(
    SolArkNumberDescription(
        key=f"tou_power_point_{point}",
        name=f"TOU power point {point}",
        address=255 + point,
        native_min_value=0,
        native_max_value=15000,
        native_step=100,
        native_unit_of_measurement="W",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )
    for point in range(1, 7)
) + tuple(
    SolArkNumberDescription(
        key=f"tou_capacity_point_{point}",
        name=f"TOU capacity point {point}",
        address=267 + point,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    )
    for point in range(1, 7)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolArkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add controls only to the unit-ID-1 master device."""
    if entry.runtime_data.client.slave_id != MASTER_SLAVE_ID:
        return
    async_add_entities(
        SolArkNumber(entry, description) for description in NUMBERS
    )


class SolArkNumber(CoordinatorEntity[SolArkDataUpdateCoordinator], NumberEntity):
    """Box-mode number backed by one verified master register."""

    _attr_has_entity_name = True
    entity_description: SolArkNumberDescription

    def __init__(
        self, entry: SolArkConfigEntry, description: SolArkNumberDescription
    ) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Sol-Ark",
            model="15K Hybrid Inverter",
        )

    @property
    def native_value(self) -> float | None:
        """Return the latest value read from the inverter."""
        return cached_register(self.entry, self.entity_description.address)

    async def async_set_native_value(self, value: float) -> None:
        """Validate and write one integer setting."""
        if not float(value).is_integer():
            raise HomeAssistantError("This Sol-Ark setting requires a whole number")
        requested = int(value)
        current = cached_register(self.entry, self.entity_description.address)
        if current is None:
            raise HomeAssistantError(
                "The setting has not been read from the inverter yet; wait for a refresh"
            )
        await async_write_verified_register(
            self.entry,
            address=self.entity_description.address,
            value=requested,
            expected=current,
            control_name=self.entity_description.name or self.entity_description.key,
        )
