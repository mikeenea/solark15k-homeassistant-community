"""Data coordinator for Sol-Ark 15K Modbus telemetry."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .modbus_client import SolArkModbusClient, SolArkModbusError
from .polling import PollGroup, build_poll_groups

_LOGGER = logging.getLogger(__name__)


class SolArkDataUpdateCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Coordinate tiered Modbus reads for one Sol-Ark inverter."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SolArkModbusClient,
        *,
        retry_delay: float,
        retries: int,
        minimum_request_spacing: float,
        live_interval: float,
        fault_interval: float,
        detail_interval: float,
        energy_interval: float,
        name: str,
        include_settings: bool = False,
    ) -> None:
        self.client = client
        self.retry_delay = retry_delay
        self.retries = retries
        self.minimum_request_spacing = minimum_request_spacing
        self.phase_offset = live_interval / 2.0 if name.strip().endswith("#2") else 0.0
        self.poll_groups = build_poll_groups(
            live_interval,
            fault_interval,
            detail_interval,
            energy_interval,
            include_settings=include_settings,
        )

        self._registers: dict[int, int] = {}
        self._poll_task: asyncio.Task[None] | None = None
        self._next_due: dict[str, float] = {}
        self._last_request_started: float | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=None,
            always_update=False,
        )

    def seed_registers(self, registers: dict[int, int]) -> None:
        """Seed known values obtained during config-entry setup."""
        self._registers.update(registers)
        self.async_set_updated_data(dict(self._registers))

    def publish_register(self, address: int, value: int) -> None:
        """Publish a verified setting immediately after a successful write."""
        self._registers[address] = value
        self.async_set_updated_data(dict(self._registers))

    async def async_start(self) -> None:
        """Start the independent tiered polling scheduler."""
        if self._poll_task is not None and not self._poll_task.done():
            return
        self._poll_task = self.hass.async_create_background_task(
            self._async_poll_loop(),
            f"{self.name} tiered Modbus polling",
        )

    async def async_stop(self) -> None:
        """Stop the polling scheduler."""
        task = self._poll_task
        self._poll_task = None
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def _async_wait_for_request_slot(self) -> None:
        """Keep a minimum quiet gap between normal Modbus requests."""
        if self._last_request_started is None:
            return

        now = asyncio.get_running_loop().time()
        remaining = self.minimum_request_spacing - (now - self._last_request_started)
        if remaining > 0:
            await asyncio.sleep(remaining)

    async def _async_read_group(self, group: PollGroup) -> list[int]:
        """Read one scheduled group with conservative retry behavior."""
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            await self._async_wait_for_request_slot()
            self._last_request_started = asyncio.get_running_loop().time()

            try:
                values = await self.client.async_read_holding(group.start, group.count)
                if attempt:
                    _LOGGER.info(
                        "Recovered polling group %s registers %s..%s on attempt %s",
                        group.name,
                        group.start,
                        group.start + group.count - 1,
                        attempt + 1,
                    )
                return values
            except SolArkModbusError as err:
                last_error = err
                if attempt < self.retries:
                    _LOGGER.warning(
                        "Polling group %s registers %s..%s failed on attempt %s/%s: %s; "
                        "waiting %.1f seconds before retry",
                        group.name,
                        group.start,
                        group.start + group.count - 1,
                        attempt + 1,
                        self.retries + 1,
                        err,
                        self.retry_delay,
                    )
                    await asyncio.sleep(self.retry_delay)

        raise UpdateFailed(
            f"Polling group {group.name} registers {group.start}.."
            f"{group.start + group.count - 1} failed after "
            f"{self.retries + 1} attempts: {last_error}",
            retry_after=self.retry_delay,
        )

    def _publish_group(self, group: PollGroup, values: list[int]) -> None:
        """Merge and immediately publish one successful block."""
        self._registers.update(
            {group.start + offset: value for offset, value in enumerate(values)}
        )
        self.async_set_updated_data(dict(self._registers))
        _LOGGER.debug(
            "Published polling group %s registers %s..%s",
            group.name,
            group.start,
            group.start + group.count - 1,
        )

    def _next_aligned_due(self, now: float, interval: float) -> float:
        """Return the next interval boundary using this inverter's phase."""
        if interval <= 0:
            return now
        phase = self.phase_offset % interval
        wait = (phase - (now % interval)) % interval
        if wait < 0.001:
            wait = interval
        return now + wait

    async def _async_poll_loop(self) -> None:
        """Run one serialized scheduler for all polling tiers."""
        loop = asyncio.get_running_loop()
        now = loop.time()
        self._next_due = {
            group.name: now + self.phase_offset for group in self.poll_groups
        }

        while True:
            now = loop.time()
            due = [
                group
                for group in self.poll_groups
                if self._next_due.get(group.name, now) <= now
            ]

            if not due:
                sleep_for = min(self._next_due.values()) - now
                await asyncio.sleep(max(sleep_for, 0.01))
                continue

            group = min(
                due,
                key=lambda item: (
                    item.priority,
                    self._next_due.get(item.name, now),
                ),
            )

            try:
                values = await self._async_read_group(group)
            except UpdateFailed as err:
                _LOGGER.warning("%s", err)
            else:
                self._publish_group(group, values)

            self._next_due[group.name] = self._next_aligned_due(
                loop.time(), group.interval
            )

    async def _async_update_data(self) -> dict[int, int]:
        """Refresh the live block when Home Assistant requests a manual refresh."""
        live_group = self.poll_groups[0]
        values = await self._async_read_group(live_group)
        self._registers.update(
            {
                live_group.start + offset: value
                for offset, value in enumerate(values)
            }
        )
        return dict(self._registers)
