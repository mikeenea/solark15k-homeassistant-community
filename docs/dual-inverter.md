# Dual-Inverter Deployment

## Purpose

This document covers expansion from a proven single-inverter Modbus connection to two parallel Sol-Ark 15K inverters.

The key rule is simple: **validate each inverter independently before creating system-level combined sensors**.

## Physical topology

```text
Sol-Ark #1 splitter RS485 -> Waveshare CH1 -> IP A:502 -> HA entry Sol-Ark 15K #1
Sol-Ark #2 splitter RS485 -> Waveshare CH2 -> IP B:502 -> HA entry Sol-Ark 15K #2
```

Each inverter remains on its own RS485 channel.

Add the custom integration twice. Each entry uses its own TCP endpoint and the Modbus unit ID confirmed for that inverter. With the recommended entry names, Home Assistant creates the production namespaces:

```text
sensor.sol_ark_15k_1_*
sensor.sol_ark_15k_2_*
```

## Slave addressing

The public V1.4 map documents unit ID `0x01`, but field testing on a parallel Sol-Ark 15K pair demonstrated that the second inverter responded on unit ID `2`. Determine the unit ID by an FC3 read of register 183 rather than assuming both units use ID 1.

Field-confirmed arrangement:

```text
Inverter 1 gateway endpoint -> unit ID 1
Inverter 2 gateway endpoint -> unit ID 2
```

The separate Waveshare endpoints still provide electrical and troubleshooting isolation. The Home Assistant integration accepts a unit ID from 1 through 247 for each entry.

### Parallel unit-ID field validation - 2026-09-18

An FC3 request for register 183 to the second inverter timed out with unit ID 1. The same endpoint, wiring, splitter, serial configuration, and register returned successfully with unit ID 2:

```text
Request unit: 2
Register: 183
Raw response: 5461 (0x1555)
Decoded battery voltage: 54.61 V
```

This confirms that unit ID can follow the inverter's parallel addressing on at least some Sol-Ark 15K firmware.

## Built-in x2 system device

When exactly two Sol-Ark integration entries are active, version 0.3.0 and later automatically creates a virtual Home Assistant device named **Sol-Ark 15K x2**. Its entities use this namespace:

```text
sensor.sol_ark_15k_x2_*
```

No template package is required. The original inverter 1 and inverter 2 entities remain available for comparison and diagnostics.

### Aggregation rules

| Measurement family | x2 calculation |
|---|---|
| PV, load, grid, generator, and battery power | Sum |
| PV, load, grid, and battery current | Sum |
| Daily and lifetime energy counters | Sum |
| MPPT 1, MPPT 2, and MPPT 3 voltage | Arithmetic mean of the two matching inverter values |
| Grid and inverter 240 V voltage | Arithmetic mean |
| Generator voltage and frequency | Arithmetic mean |
| Load frequency | Arithmetic mean |
| Battery voltage and state of charge | Arithmetic mean |

MPPT voltages are averaged only between matching inputs: MPPT 1 with MPPT 1, MPPT 2 with MPPT 2, and MPPT 3 with MPPT 3. Generator energy is not created because the current register map does not expose a validated generator-energy counter.

The x2 entities become unavailable if either inverter feed is unavailable. This avoids silently treating a failed inverter connection as zero. A one-inverter installation receives no x2 device and behaves exactly as before.

## Field-validation basis

The aggregation rules were selected after live validation of two parallel Sol-Ark 15K inverters, with independent Modbus connections and comparison against Home Assistant, inverter screens, and system behavior. The master continues to coordinate operating settings with the slave through the inverters' parallel communications link; telemetry is still collected independently from both Modbus endpoints.

## Failover considerations

If one inverter or one Waveshare channel goes offline, retain individual entities so Home Assistant clearly shows which source failed.

Potential diagnostic entities:

```text
binary_sensor.sol_ark_15k_1_modbus_online
binary_sensor.sol_ark_15k_2_modbus_online
binary_sensor.sol_ark_15k_parallel_data_consistent
```

These can be added after the first field deployment.

## Historical data tags

When exporting to InfluxDB, preserve inverter identity. Do not store only the combined value.

Recommended conceptual tags:

```text
inverter=1
inverter=2
system=combined
```

This enables future analysis of load sharing, PV production differences, temperature imbalance, and inverter-specific faults.

## Dashboard behavior

Export `sol_ark_15k_1_*`, `sol_ark_15k_2_*`, and `sol_ark_15k_x2_*` to InfluxDB. The Operational Console System view and Electrical Trends Whole-System Power panel use x2 entities directly. Electrical Trends retains inverter 1 and inverter 2 overlays for diagnostics, and Parallel System Detail presents system, inverter 1, inverter 2, and delta columns.

The x2 series begins accumulating history only after the second integration entry is active and the x2 namespace is accepted by the Home Assistant InfluxDB filter. Existing individual-inverter history is not retroactively copied into x2 series.

Energy Accounting provides a `System` selection. Validate that the energy entities represent the intended per-inverter quantities before relying on combined totals. Do not sum registers classified as duplicated system values.

See [deployment-guide.md](deployment-guide.md) for the complete installation sequence.
