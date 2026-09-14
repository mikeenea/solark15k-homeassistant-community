# Grafana dashboard import and configuration

## Supported dashboard set

The public release contains four supported dashboards:

| Dashboard | File | Purpose |
|---|---|---|
| Operational Console | `solark15k-operational-overview.json` | Live system state, instantaneous power, 24-hour flow, battery power, and SOC |
| Electrical Trends | `solark15k-charts.json` | Battery, MPPT, load, grid, voltage, current, frequency, and temperature history |
| Energy Accounting | `solark15k-energy-totals.json` | Rolling 30-day daily totals and rolling 12-month monthly totals |
| Parallel System Detail | `solark15k-system-detail.json` | Side-by-side operating detail for two parallel inverters |

The legacy `solark15k-engineering-detail.json` and `solark15k-inverter-overview.json` exports are unsupported historical snapshots. Do not import them for a new installation.

## Required software

Configure a Grafana InfluxDB data source that reads the historian bucket. Use a dedicated read-only token; never place the token in dashboard JSON or commit it to Git.

The Operational Console and Parallel System Detail require the Volkov Labs Business Charts plugin:

```text
volkovlabs-echarts-panel
```

For the Home Assistant Grafana add-on:

```yaml
plugins:
  - volkovlabs-echarts-panel
```

Restart Grafana after installing the plugin.

## Entity convention

The integration normally creates entities such as:

```text
sensor.sol_ark_15k_1_battery_voltage
sensor.sol_ark_15k_2_battery_voltage
```

Home Assistant's standard InfluxDB schema stores the entity ID tag without the `sensor.` prefix:

```text
sol_ark_15k_1_battery_voltage
```

The default dashboard entity prefix is:

```text
sol_ark_15k_
```

## Import

1. Open Grafana.
2. Select **Dashboards → New → Import**.
3. Upload one JSON file from `grafana/dashboards/`.
4. Select the InfluxDB data source that reads the target bucket.
5. Select **Import**.
6. When updating an existing dashboard with the same UID, select **Overwrite**.
7. Repeat for the other three supported dashboards.

## Dashboard variables

Open **Dashboard settings → Variables** to customize hidden installation variables.

All supported dashboards provide:

| Variable | Default | Meaning |
|---|---:|---|
| `bucket` | `solark` | InfluxDB bucket |
| `entity_prefix` | `sol_ark_15k_` | Entity ID prefix without `sensor.` |

The Operational Console additionally provides:

| Variable | Default | Meaning |
|---|---:|---|
| `battery_capacity_ah` | `4012` | Installed nominal battery-bank capacity |
| `shunt_soc_entity` | `garage_shunt_state_of_charge` | Optional external-shunt SOC entity |
| `shunt_ah_entity` | `garage_shunt_consumed_ah_absolute` | Optional external-shunt consumed-Ah entity |
| `site_timezone` | `America/New_York` | Local calendar boundary for daily PV peak |
| `solar_active_threshold_w` | `100` | Minimum PV power treated as active |
| `battery_active_threshold_w` | `100` | Minimum battery power treated as active |
| `inverter_max_power_w` | `15000` | Load, grid, and battery display scale |
| `pv_max_power_w` | `18000` | PV display scale |

If the optional shunt entities are not present, the Operational Console uses Sol-Ark SOC and calculates charge-needed Ah from configured capacity and SOC.

## Sign conventions

The Sol-Ark register convention used by the integration is:

```text
battery power positive = discharge
battery power negative = charge
```

Operational dashboards reverse that sign only for presentation:

```text
positive = charging
negative = discharging
```

Raw Home Assistant and InfluxDB values are not modified.

## Query behavior

Numeric panels filter `_field == "value"` where a single Home Assistant numeric field is expected. Historical charts use look-back, windowing, and carry-forward logic so a value remains visible when Home Assistant does not emit a new state event during every interval.

The Energy Accounting dashboard reads the project-derived `solark_energy_totals` measurement and supports inverter or combined-system selection.

## Public-use and design provenance

See [dashboard-design.md](dashboard-design.md) for the independent design system, third-party boundary, contribution rules, and non-affiliation statement.
