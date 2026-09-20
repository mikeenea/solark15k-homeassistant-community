"""Immediate InfluxDB write path for Sol-Ark state changes.

Home Assistant's built-in InfluxDB integration queues every ``state_changed``
event before applying its entity filter. On installations with very high event
rates, a filtered Sol-Ark event can therefore wait in the global queue for a
long time even though the Home Assistant state itself is current.

This helper does not replace Home Assistant's InfluxDB integration. Instead it
reuses that integration's configured filter and event-to-Influx conversion, and
posts only matching Sol-Ark numeric state events directly to the same InfluxDB
2.x endpoint. The normal Home Assistant InfluxDB writer remains enabled; when
it later reaches the same event, InfluxDB receives the same series/timestamp and
simply updates the existing point.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .influx_line_protocol import event_json_to_line

_LOGGER = logging.getLogger(__name__)

INFLUX_DOMAIN = "influxdb"
INFLUX_API_VERSION = "api_version"
INFLUX_V2 = "2"
INFLUX_URL = "url"
INFLUX_TOKEN = "token"
INFLUX_ORGANIZATION = "organization"
INFLUX_BUCKET = "bucket"

# Coalesce the many sensor updates produced by one coordinator refresh into a
# single HTTP write without adding noticeable dashboard latency.
FLUSH_DELAY_SECONDS = 0.25
HTTP_TIMEOUT_SECONDS = 10


class SolArkInfluxFastPath:
    """Write this config entry's Sol-Ark states to InfluxDB without queue lag."""

    def __init__(self, hass: HomeAssistant, config_entry_id: str) -> None:
        self.hass = hass
        self.config_entry_id = config_entry_id
        self._entity_registry = er.async_get(hass)
        self._pending: dict[str, Event] = {}
        self._flush_handle = None
        self._unsub = None
        self._missing_influx_logged = False
        self._write_error_logged = False

    async def async_start(self) -> None:
        """Start listening for state changes owned by this Sol-Ark entry."""
        if self._unsub is None:
            self._unsub = self.hass.bus.async_listen(
                EVENT_STATE_CHANGED, self._async_state_changed
            )

    async def async_close(self) -> None:
        """Stop the listener and cancel a pending coalesced write."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        if self._flush_handle is not None:
            self._flush_handle.cancel()
            self._flush_handle = None
        self._pending.clear()

    @callback
    def _async_state_changed(self, event: Event) -> None:
        """Queue only state changes that belong to this Sol-Ark config entry."""
        entity_id = event.data.get("entity_id")
        if not isinstance(entity_id, str):
            return

        registry_entry = self._entity_registry.async_get(entity_id)
        if (
            registry_entry is None
            or registry_entry.config_entry_id != self.config_entry_id
        ):
            return

        self._pending[entity_id] = event
        if self._flush_handle is None:
            self._flush_handle = self.hass.loop.call_later(
                FLUSH_DELAY_SECONDS, self._schedule_flush
            )

    @callback
    def _schedule_flush(self) -> None:
        """Schedule the async write after the short coalescing window."""
        self._flush_handle = None
        self.hass.async_create_task(self._async_flush())

    def _get_influx_entry(self):
        """Return the loaded Home Assistant InfluxDB 2.x config entry."""
        for entry in self.hass.config_entries.async_entries(INFLUX_DOMAIN):
            if (
                entry.state is ConfigEntryState.LOADED
                and str(entry.data.get(INFLUX_API_VERSION)) == INFLUX_V2
            ):
                return entry
        return None

    async def _async_flush(self) -> None:
        """Convert matching HA events and write their numeric values immediately."""
        events = list(self._pending.values())
        self._pending.clear()
        if not events:
            return

        influx_entry = self._get_influx_entry()
        if influx_entry is None:
            if not self._missing_influx_logged:
                _LOGGER.debug(
                    "InfluxDB 2.x is not loaded; Sol-Ark direct Influx fast path is idle"
                )
                self._missing_influx_logged = True
            return

        runtime = getattr(influx_entry, "runtime_data", None)
        converter = getattr(runtime, "event_to_json", None)
        if converter is None:
            if not self._missing_influx_logged:
                _LOGGER.debug(
                    "InfluxDB runtime is not ready; Sol-Ark direct Influx fast path is idle"
                )
                self._missing_influx_logged = True
            return

        data = influx_entry.data
        base_url = str(data.get(INFLUX_URL) or "").rstrip("/")
        token = data.get(INFLUX_TOKEN)
        organization = data.get(INFLUX_ORGANIZATION)
        bucket = data.get(INFLUX_BUCKET)
        if not all((base_url, token, organization, bucket)):
            if not self._missing_influx_logged:
                _LOGGER.warning(
                    "InfluxDB 2.x connection data is incomplete; Sol-Ark fast path disabled"
                )
                self._missing_influx_logged = True
            return

        lines: list[str] = []
        for event in events:
            event_json = converter(event)
            if not event_json:
                # Respect the user's existing Home Assistant Influx include/exclude filter.
                continue

            line = event_json_to_line(event_json)
            if line is not None:
                lines.append(line)

        if not lines:
            return

        endpoint = f"{base_url}/api/v2/write?{urlencode({'org': organization, 'bucket': bucket, 'precision': 'ns'})}"
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json",
        }

        try:
            session = async_get_clientsession(self.hass)
            async with session.post(
                endpoint,
                data="\n".join(lines).encode("utf-8"),
                headers=headers,
                timeout=HTTP_TIMEOUT_SECONDS,
            ) as response:
                if response.status not in (200, 204):
                    body = (await response.text())[:300]
                    if not self._write_error_logged:
                        _LOGGER.warning(
                            "Sol-Ark direct Influx write failed with HTTP %s: %s",
                            response.status,
                            body,
                        )
                        self._write_error_logged = True
                    return
        except Exception as err:  # Network errors must never break HA sensor updates.
            if not self._write_error_logged:
                _LOGGER.warning("Sol-Ark direct Influx write failed: %s", err)
                self._write_error_logged = True
            return

        self._missing_influx_logged = False
        self._write_error_logged = False
        _LOGGER.debug("Direct Influx fast path wrote %s Sol-Ark states", len(lines))
