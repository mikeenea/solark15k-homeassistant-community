# 1.0.0 release acceptance checklist

This checklist records acceptance of the stable public read-only `1.0.0` package.
Regular users do not need to repeat register research or development testing. They only
need to complete the applicable clean-install or upgrade checks below.

## Automated release gates

Every pull request and push to `main` must pass:

- Python compilation;
- dependency-free unit tests for signed register decoding, 32-bit counters,
  x2 sum/mean/availability rules, and InfluxDB line-protocol serialization;
- JSON and YAML parsing;
- all four supported Grafana dashboard structural checks;
- HACS/release metadata checks;
- read-only stable-branch enforcement; and
- register-map validation.

## Clean install: one inverter

1. Install or update the integration through HACS.
2. Restart Home Assistant once after installation.
3. Add one integration entry using the Waveshare address, TCP port `502`, and
   the unit ID proven by the included read-only probe.
4. Confirm the device exposes current battery voltage, load power, PV power,
   and daily energy values.
5. Confirm no `Sol-Ark 15K x2` device is created.
6. If InfluxDB is enabled, confirm one `sol_ark_15k_1_*` numeric entity is
   receiving current points before importing dashboards.

## Clean install: two parallel inverters

1. Complete the one-inverter procedure for inverter 1.
2. Add inverter 2 as a separate integration entry using its own gateway
   endpoint or isolated dual-channel endpoint and its independently tested unit
   ID. The field-tested pair uses unit ID `1` for inverter 1 and `2` for
   inverter 2; do not assume every installation is identical.
3. Confirm both physical devices update independently.
4. Confirm exactly one `Sol-Ark 15K x2` device appears and exposes combined
   power/energy/current values plus arithmetic-mean voltage/SOC values.
5. Temporarily disconnect one feed and confirm x2 values become unavailable
   rather than reporting a misleading partial system total.
6. If InfluxDB is enabled, confirm `sol_ark_15k_1_*`,
   `sol_ark_15k_2_*`, and `sol_ark_15k_x2_*` series receive current points.

## Upgrade from 0.4.x

1. Create a Home Assistant backup.
2. Update the integration through HACS and restart Home Assistant once.
3. Do not delete or recreate existing config entries.
4. Confirm existing per-inverter entity IDs and history remain present.
5. For two-inverter systems, confirm the existing x2 device returns after both
   entries finish loading.
6. Reimport a dashboard only when its JSON changed; importing does not alter
   InfluxDB data.

## Release acceptance record

Record the following in the GitHub release or validation issue:

| Item | Required result |
|---|---|
| CI validation | All checks pass |
| One-inverter startup | Entry loads and live sensors update |
| Two-inverter startup | Both entries and one x2 device load |
| Reload/unload | No duplicate x2 device or entities |
| InfluxDB optional path | Numeric events write; missing InfluxDB does not block setup |
| Dashboard imports | Four supported dashboards import without structural errors |
| Stable branch safety | No Modbus write implementation |

Any failed required result blocks a stable release or maintenance update until it
is corrected or explicitly documented as outside the supported release boundary.
