"""Development-only TOU time controls for Sol-Ark 15K."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
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
class SolArkTimeDescription(TimeEntityDescription):
    """Describe one validated TOU time register."""

    address: int


TIMES: tuple[SolArkTimeDescription, ...] = tuple(
    SolArkTimeDescription(
        key=f"tou_time_point_{point}",
        name=f"TOU time point {point}",
        address=249 + point,
        entity_category=EntityCategory.CONFIG,
    )
    for point in range(1, 7)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolArkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add time controls only to the unit-ID-1 master device."""
    if entry.runtime_data.client.slave_id != MASTER_SLAVE_ID:
        return
    async_add_entities(SolArkTime(entry, description) for description in TIMES)


class SolArkTime(CoordinatorEntity[SolArkDataUpdateCoordinator], TimeEntity):
    """TOU time backed by one decimal-HHMM master register."""

    _attr_has_entity_name = True
    entity_description: SolArkTimeDescription

    def __init__(
        self, entry: SolArkConfigEntry, description: SolArkTimeDescription
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
    def native_value(self) -> time | None:
        """Decode decimal HHMM from the latest inverter read."""
        raw = cached_register(self.entry, self.entity_description.address)
        if raw is None:
            return None
        hour, minute = divmod(raw, 100)
        if hour > 23 or minute > 59:
            return None
        return time(hour=hour, minute=minute)

    async def async_set_value(self, value: time) -> None:
        """Encode and write one TOU time."""
        if value.second or value.microsecond:
            raise HomeAssistantError("TOU times must use whole minutes")
        current = cached_register(self.entry, self.entity_description.address)
        if current is None:
            raise HomeAssistantError(
                "The setting has not been read from the inverter yet; wait for a refresh"
            )
        requested = value.hour * 100 + value.minute
        await async_write_verified_register(
            self.entry,
            address=self.entity_description.address,
            value=requested,
            expected=current,
            control_name=self.entity_description.name or self.entity_description.key,
        )
