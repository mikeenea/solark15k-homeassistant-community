# Single-Inverter Field-Validation Record

This record documents the field work supporting the stable single-inverter monitoring release. It is project history, not an installation checklist for ordinary users.

## Validated configuration

```text
Inverter: Sol-Ark 15K
Transport: isolated RS485 through a Waveshare Ethernet/PoE gateway
Protocol: Modbus TCP to Modbus RTU
Serial: 9600 baud, 8 data bits, no parity, 1 stop bit
TCP port: 502
Slave ID: 1
Home Assistant integration: Sol-Ark 15K Modbus
Historian: InfluxDB 2.x
Visualization: Grafana
```

The gateway address is intentionally omitted from the public record.

## Completed field validation

- Direct register 183 reads returned plausible live battery voltage.
- The custom integration established and maintained local Modbus polling.
- Home Assistant entities populated under the inverter 1 namespace.
- Battery voltage and state of charge were compared with live system values.
- Battery power and battery-current directions were verified and reflected in dashboard sign conventions.
- Charging is displayed as negative raw battery current/power where applicable, while user-facing directional panels present charging to the right in green and discharging in red.
- Load, PV, grid, voltage, current, frequency, temperature, MPPT, relay, and energy telemetry were exercised with live data.
- Grid voltage and exchange correctly report zero when the grid is disconnected; low-level disconnected-input noise is not treated as real grid service.
- InfluxDB received live Sol-Ark measurements and retained imported historical energy totals.
- Operational Console, Electrical Trends, and Energy Accounting were validated with the monitored inverter.
- Dashboard query timeouts and empty-series behavior were corrected during field use.
- Daily and monthly energy ledgers were validated with live and backfilled history.
- Home Assistant, InfluxDB, Grafana, integration, and dashboard update cycles were exercised during development.
- The public release remains read-only and contains no inverter configuration-write controls.

## Supported release boundary

The stable single-inverter release supports one configured inverter and the inverter `1` dashboard selection. InfluxDB and Grafana are optional. Parallel System Detail and inverter 2 series are optional and may show no data until a second monitored endpoint exists.

Parallel-inverter aggregation remains a separate validation milestone because some registers may be per-inverter, master-only, duplicated, or system-wide depending on firmware and operating mode.

Experimental TOU register research is isolated on `dev/tou-modbus-research` and is not included in the stable read-only release.
