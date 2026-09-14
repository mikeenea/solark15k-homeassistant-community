"""Config flow for the Sol-Ark 15K Modbus integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

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
    DEFAULT_PORT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRIES,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    MAX_DETAIL_INTERVAL,
    MAX_ENERGY_INTERVAL,
    MAX_FAULT_INTERVAL,
    MAX_INTER_REQUEST_DELAY,
    MAX_LIVE_INTERVAL,
    MAX_REQUEST_SPACING,
    MAX_REQUEST_TIMEOUT,
    MIN_DETAIL_INTERVAL,
    MIN_ENERGY_INTERVAL,
    MIN_FAULT_INTERVAL,
    MIN_INTER_REQUEST_DELAY,
    MIN_LIVE_INTERVAL,
    MIN_REQUEST_SPACING,
    MIN_REQUEST_TIMEOUT,
)
from .modbus_client import SolArkModbusClient, SolArkModbusError


class SolArkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sol-Ark 15K."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure one Sol-Ark inverter endpoint."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            slave_id = int(user_input[CONF_SLAVE_ID])

            client = SolArkModbusClient(
                host=host,
                port=port,
                slave_id=slave_id,
                timeout=DEFAULT_REQUEST_TIMEOUT,
            )
            try:
                await client.async_read_holding(183, 1)
            except SolArkModbusError:
                errors["base"] = "cannot_connect"
            finally:
                await client.async_close()

            if not errors:
                await self.async_set_unique_id(f"{host}:{port}:{slave_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=str(user_input[CONF_NAME]).strip(),
                    data={
                        CONF_NAME: str(user_input[CONF_NAME]).strip(),
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SLAVE_ID: slave_id,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Sol-Ark 15K #1"): str,
                vol.Required(CONF_HOST, default="192.0.2.20"): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=247)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return SolArkOptionsFlow()


class SolArkOptionsFlow(OptionsFlowWithReload):
    """Allow polling behavior to be changed from the Home Assistant UI."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage polling options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LIVE_INTERVAL,
                    default=float(options.get(CONF_LIVE_INTERVAL, DEFAULT_LIVE_INTERVAL)),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_LIVE_INTERVAL, max=MAX_LIVE_INTERVAL),
                ),
                vol.Required(
                    CONF_FAULT_INTERVAL,
                    default=float(options.get(CONF_FAULT_INTERVAL, DEFAULT_FAULT_INTERVAL)),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_FAULT_INTERVAL, max=MAX_FAULT_INTERVAL),
                ),
                vol.Required(
                    CONF_DETAIL_INTERVAL,
                    default=float(options.get(CONF_DETAIL_INTERVAL, DEFAULT_DETAIL_INTERVAL)),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_DETAIL_INTERVAL, max=MAX_DETAIL_INTERVAL),
                ),
                vol.Required(
                    CONF_ENERGY_INTERVAL,
                    default=float(options.get(CONF_ENERGY_INTERVAL, DEFAULT_ENERGY_INTERVAL)),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_ENERGY_INTERVAL, max=MAX_ENERGY_INTERVAL),
                ),
                vol.Required(
                    CONF_MIN_REQUEST_SPACING,
                    default=float(
                        options.get(
                            CONF_MIN_REQUEST_SPACING,
                            DEFAULT_MIN_REQUEST_SPACING,
                        )
                    ),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_REQUEST_SPACING, max=MAX_REQUEST_SPACING),
                ),
                vol.Required(
                    CONF_INTER_REQUEST_DELAY,
                    default=float(
                        options.get(
                            CONF_INTER_REQUEST_DELAY,
                            DEFAULT_INTER_REQUEST_DELAY,
                        )
                    ),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(
                        min=MIN_INTER_REQUEST_DELAY,
                        max=MAX_INTER_REQUEST_DELAY,
                    ),
                ),
                vol.Required(
                    CONF_REQUEST_TIMEOUT,
                    default=float(
                        options.get(
                            CONF_REQUEST_TIMEOUT,
                            DEFAULT_REQUEST_TIMEOUT,
                        )
                    ),
                ): vol.All(
                    vol.Coerce(float),
                    vol.Range(min=MIN_REQUEST_TIMEOUT, max=MAX_REQUEST_TIMEOUT),
                ),
                vol.Required(
                    CONF_RETRIES,
                    default=int(options.get(CONF_RETRIES, DEFAULT_RETRIES)),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=5)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
