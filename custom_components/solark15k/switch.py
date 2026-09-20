"""Development-only Boolean configuration controls for Sol-Ark 15K."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
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
class SolArkSwitchDescription(SwitchEntityDescription):
    """Describe one validated writable Boolean field."""

    address: int
    mask: int | None = None


SWITCHES: tuple[SolArkSwitchDescription, ...] = (
    SolArkSwitchDescription(
        key="tou_charge_point_1",
        name="TOU charge point 1",
        address=274,
        mask=0x0001,
        entity_category=EntityCategory.CONFIG,
    ),
    SolArkSwitchDescription(
        key="generator_charge",
        name="Generator charge",
        address=231,
        entity_category=EntityCategory.CONFIG,
    ),
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
        SolArkSwitch(entry, description) for description in SWITCHES
    )


class SolArkSwitch(CoordinatorEntity[SolArkDataUpdateCoordinator], SwitchEntity):
    """Verified switch backed by a full or packed master register."""

    _attr_has_entity_name = True
    entity_description: SolArkSwitchDescription

    def __init__(
        self, entry: SolArkConfigEntry, description: SolArkSwitchDescription
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
    def is_on(self) -> bool | None:
        """Return the latest Boolean state read from the inverter."""
        raw = cached_register(self.entry, self.entity_description.address)
        if raw is None:
            return None
        if self.entity_description.mask is None:
            return raw == 1
        return bool(raw & self.entity_description.mask)

    async def _async_set(self, enabled: bool) -> None:
        """Write a Boolean while preserving unrelated packed bits."""
        current = cached_register(self.entry, self.entity_description.address)
        if current is None:
            raise HomeAssistantError(
                "The setting has not been read from the inverter yet; wait for a refresh"
            )
        mask = self.entity_description.mask
        if mask is None:
            requested = 1 if enabled else 0
        elif enabled:
            requested = current | mask
        else:
            requested = current & ~mask
        await async_write_verified_register(
            self.entry,
            address=self.entity_description.address,
            value=requested,
            expected=current,
            control_name=self.entity_description.name or self.entity_description.key,
        )

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the setting."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the setting."""
        await self._async_set(False)
