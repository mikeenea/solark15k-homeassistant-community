# Home Assistant Custom Integration

## Status

The repository includes a read-only Home Assistant custom integration at:

```text
custom_components/solark15k/
```

It replaces the commissioning YAML package after the Modbus path has been field validated.

## Key design points

- One coordinator owns all Modbus requests for each configured inverter.
- Individual Home Assistant sensor entities do not independently poll the inverter.
- The TCP session is kept open between successful requests.
- FC3 holding-register reads only; no Modbus write functions are implemented.
- Operational registers are polled separately from slower fault, electrical-detail, and energy registers.
- Every successful register block is merged into the coordinator cache and published to Home Assistant immediately; entities do not wait for a complete register sweep.
- A minimum request-spacing control prevents background reads from creating a burst of back-to-back Modbus traffic.
- Failed requests use a separate conservative retry quiet time.
- Polling parameters are changeable from the Home Assistant integration **Configure** screen; source-code edits are not required.
- Each configured inverter appears as its own Home Assistant device.
- When Home Assistant's built-in InfluxDB 2.x integration is loaded and its existing include/exclude filter accepts a Sol-Ark entity, the integration uses an immediate Influx fast path so unrelated Home Assistant event traffic cannot hold the Sol-Ark point in the normal global Influx event queue for many minutes.

## Tiered polling added in version 0.2.0

The original commissioning scheduler treated the entire register map as one slow sweep. Version `0.2.0` replaces that behavior with prioritized polling intended to provide responsive operational telemetry without polling slow-changing counters at the same rate.

| Tier | Registers | Purpose | Default interval |
|---|---|---|---:|
| Live | 166..196 | generator/AC-coupled power, grid power, inverter power, load power/current, battery temperature/voltage/SOC/power/current, PV watts, frequencies, relays | 5 seconds |
| Fault | 103..106 | fault words | 15 seconds |
| Detail | 107..114 and 150..165 | battery capacity, PV voltage/current, AC voltages and currents | 60 seconds |
| Energy | 60..102 | daily/lifetime energy counters and heat-sink temperature | 300 seconds |

The live range `166..196` is read as one 31-register FC3 request so the primary operational values arrive together. The slower energy range is split into smaller background requests (`60..75`, `76..91`, and `92..102`) so live reads can remain prioritized.

The scheduler serializes all Modbus traffic. Under healthy conditions the default minimum gap between requests is **1 second**. A slow background group can therefore occupy unused slots between 5-second live reads without creating simultaneous Modbus requests.

## Default polling options

| Option | Default |
|---|---:|
| Live telemetry interval | 5 seconds |
| Fault interval | 15 seconds |
| Electrical detail interval | 60 seconds |
| Energy counter interval | 300 seconds |
| Minimum gap between normal Modbus requests | 1 second |
| Retry quiet time after a failed request | 15 seconds |
| Request timeout | 5 seconds |
| Retries | 2 |

The 15-second value is retained as the **retry quiet time**, not the normal polling delay. The production scheduler no longer waits 15 seconds between every successful request.

The 5-second live interval is the initial production target. The Home Assistant options flow permits a live interval down to 2 seconds for later field testing, but the default should be validated for stability before shortening it.

## Install or update

Copy this directory from the repository:

```text
custom_components/solark15k
```

into the Home Assistant configuration directory so the final path is:

```text
/config/custom_components/solark15k
```

When updating from an older version, replace the complete directory so new files such as `polling.py` and `influx_fastpath.py` are included.

Restart Home Assistant after copying the files.

Then open:

```text
Settings -> Devices & services -> Add integration
```

Search for:

```text
Sol-Ark 15K Modbus
```

For one inverter, add one integration entry using the gateway endpoint assigned to that inverter, TCP port `502`, and Modbus slave ID `1`.

For two parallel inverters, add the integration twice. Use a different gateway endpoint and name for each entry, but retain slave ID `1` for both:

```text
Sol-Ark 15K #1 -> inverter 1 gateway endpoint -> slave 1
Sol-Ark 15K #2 -> inverter 2 gateway endpoint -> slave 1
```

Each entry creates its own Home Assistant device. With the recommended names, the normal entity namespaces are:

```text
sensor.sol_ark_15k_1_*
sensor.sol_ark_15k_2_*
```

See [deployment-guide.md](deployment-guide.md) for the complete branching procedure.

During setup the integration performs one read-only check of holding register `183` (battery voltage). If that succeeds, the integration creates a Home Assistant device and starts the tiered scheduler.

## Change polling intervals

Open:

```text
Settings -> Devices & services -> Sol-Ark 15K Modbus -> Configure
```

The Configure screen exposes the live, fault, detail, and energy intervals as well as minimum request spacing, retry quiet time, request timeout, and retry count. Saving the options reloads the integration.

For initial version `0.2.0` validation, leave the defaults at 5 / 15 / 60 / 300 seconds and the minimum request spacing at 1 second. If the live 31-register request produces retries or timeouts, increase the live interval or minimum request spacing before reducing any timing values.

## Immediate InfluxDB fast path

Home Assistant's built-in InfluxDB integration receives every Home Assistant `state_changed` event and applies its entity filter inside its worker queue. On a system with very high event traffic, a Sol-Ark state can therefore already be current in Home Assistant while its normal InfluxDB write is delayed behind unrelated events.

Version `0.1.1` added an automatic fast path for this case. It does **not** replace or reconfigure the Home Assistant InfluxDB integration and it does not store separate InfluxDB credentials. Instead, it:

1. watches state changes belonging to the configured `solark15k` config entry;
2. reuses the loaded Home Assistant InfluxDB integration's own event converter, so the existing include/exclude filter, measurement naming, tags, and event timestamp remain authoritative;
3. coalesces the Sol-Ark state changes from one coordinator update for 0.25 seconds; and
4. posts the numeric `value` fields directly to the same InfluxDB 2.x URL, organization, and bucket.

If the Home Assistant InfluxDB filter does not include a Sol-Ark entity, the fast path does not write it. If InfluxDB is not configured or is not API version 2, the fast path stays idle and normal Home Assistant operation is unchanged.

The normal Home Assistant InfluxDB writer remains active. When it eventually processes the same Sol-Ark event, it uses the same measurement/tags/event timestamp, so InfluxDB updates the existing point rather than creating a second time-series sample at a different timestamp.

With debug logging enabled for `homeassistant.components.influxdb` and `custom_components.solark15k.influx_fastpath`, a successful immediate write is reported as:

```text
Direct Influx fast path wrote N Sol-Ark states
```

## Coexistence with other Sol-Ark monitoring

Field testing showed occasional missed Modbus replies while the previous Sol-Ark monitoring connection was active. With that competing monitor disconnected, the persistent Modbus path was reliable during commissioning. The tiered scheduler should initially be validated with the competing monitor disconnected.

## Removal of the YAML commissioning package

Do not run the native YAML Modbus test package and this custom integration against the same inverter at the same time. Both would become Modbus masters and could create unnecessary contention.

Once the custom integration is installed and confirmed working, disable or remove the active `solark15k_test_package.yaml` package from the Home Assistant configuration before long-term operation.
