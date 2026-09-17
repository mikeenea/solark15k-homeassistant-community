# Deployment guide: one or two Sol-Ark 15K inverters

This is the primary installation path for the repository. It covers one standalone Sol-Ark 15K and two Sol-Ark 15K inverters operating in parallel. Complete the common steps first, then follow the branch for your system.

> **Safety boundary:** This project is read-only. It uses Modbus function code 03 and does not implement register writes. Do not expose Modbus TCP port 502 to the public Internet.

## 1. Choose the deployment model

| Item | One inverter | Two parallel inverters |
|---|---|---|
| RS485 links | One isolated link | Two isolated links, one per inverter |
| Gateway endpoints | One IP/port | Two IP/port endpoints or two independently addressed channels |
| Modbus slave ID | `1` | `1` on both endpoints |
| Home Assistant entries | One | Two |
| Recommended entry names | `Sol-Ark 15K #1` | `Sol-Ark 15K #1` and `Sol-Ark 15K #2` |
| Entity namespaces | `sensor.sol_ark_15k_1_*` | `sensor.sol_ark_15k_1_*` and `sensor.sol_ark_15k_2_*` |
| Dashboard inverter selector | `1` | `1`, `2`, or `System` where supported |
| Parallel System Detail | Optional; inverter 2 shows no data | Recommended |

For two inverters, do not connect both RS485 links to one shared two-wire bus. The reference design keeps them electrically independent and gives each inverter its own Modbus TCP endpoint.

## 2. Prerequisites

You need:

- one or two Sol-Ark 15K inverters;
- battery communications using CAN, not the RS485 conductors needed by this monitor;
- a supported Ethernet-to-RS485 Modbus gateway;
- Home Assistant with access to the gateway network;
- optional InfluxDB 2.x and Grafana for the supplied dashboards;
- the Volkov Labs Business Charts plugin for the Operational Console and Parallel System Detail dashboards;
- Python 3 on a commissioning computer for the included probe.

Recommended gateway settings for every active RS485 channel:

```text
Mode: Modbus TCP <-> Modbus RTU
TCP role: server
TCP port: 502
Serial: 9600 baud, 8 data bits, no parity, 1 stop bit
Storage/autopolling: disabled
Sol-Ark slave ID: 1
```

Use DHCP reservations or static addresses appropriate for your network. Addresses in this repository such as `192.0.2.x` are documentation examples and must not be copied as production addresses.

## 3. Wire and validate the first inverter

1. Confirm the inverter battery connection uses CAN and the applicable Sol-Ark protocol prerequisites are satisfied.
2. Connect the splitter's RS485 output to one gateway channel using A, B, and signal ground as described in [wiring.md](wiring.md).
3. Configure that channel using the settings above.
4. Confirm the gateway address is reachable.
5. Confirm TCP port 502:

   ```powershell
   Test-NetConnection <gateway-ip> -Port 502
   ```

6. From the repository root, run:

   ```powershell
   python tools/solark_modbus_probe.py <gateway-ip>
   ```

7. Confirm battery voltage, SOC, PV, load, and temperature values are plausible.
8. If TCP succeeds but Modbus times out, verify A/B polarity, signal ground, serial settings, gateway mode, and termination before changing software.

Do not install the Home Assistant integration until the probe can read the inverter reliably.

## 4. Install the Home Assistant integration

### Option A: HACS custom repository

1. In HACS, open **Integrations**.
2. Select the menu and choose **Custom repositories**.
3. Add:

   ```text
   https://github.com/mikeenea/solark15k-homeassistant-community
   ```

4. Select category **Integration**.
5. Install **Sol-Ark 15K Modbus**.
6. Restart Home Assistant.

### Option B: manual installation

Copy:

```text
custom_components/solark15k
```

to:

```text
/config/custom_components/solark15k
```

Restart Home Assistant.

Do not run the legacy YAML commissioning package and the custom integration against the same inverter at the same time.

## 5. Configure one inverter

1. Open **Settings -> Devices & services -> Add integration**.
2. Search for **Sol-Ark 15K Modbus**.
3. Enter:

   ```text
   Name: Sol-Ark 15K #1
   Host: <gateway endpoint for inverter 1>
   Port: 502
   Slave ID: 1
   ```

4. The integration validates the connection by reading battery-voltage register 183.
5. Confirm the resulting device exposes entities beginning with:

   ```text
   sensor.sol_ark_15k_1_
   ```

6. Leave the default polling intervals in place for initial validation.
7. Compare live Home Assistant values with the inverter display for at least one charging period and one discharging period.

For a single-inverter installation, continue to section 7.

## 6. Add a second parallel inverter

Complete this section only after inverter 1 is stable.

1. Wire inverter 2 to a separate RS485 gateway channel or separate gateway.
2. Assign it a different network endpoint from inverter 1.
3. Use the same serial settings and slave ID `1`.
4. Run the Python probe directly against inverter 2's endpoint.
5. Add **Sol-Ark 15K Modbus** a second time in Home Assistant:

   ```text
   Name: Sol-Ark 15K #2
   Host: <gateway endpoint for inverter 2>
   Port: 502
   Slave ID: 1
   ```

6. Confirm entities beginning with:

   ```text
   sensor.sol_ark_15k_2_
   ```

7. Validate both devices independently before using combined values.
8. Review [dual-inverter.md](dual-inverter.md) before summing any register. Some values may be per-inverter, duplicated system values, or master-only values depending on firmware and parallel configuration.

The Parallel-screen Modbus serial number does not replace slave ID `1` in this design. The two inverters are distinguished by their separate TCP endpoints.

## 7. Configure InfluxDB

The supplied Grafana dashboards expect the standard Home Assistant InfluxDB schema and numeric field name `value`.

1. Create an InfluxDB 2.x bucket, normally named `solark`.
2. Create a Home Assistant write token and a separate Grafana read-only token.
3. Configure the Home Assistant InfluxDB integration.
4. Restrict export to the Sol-Ark namespaces:

   ```yaml
   influxdb:
     include:
       entity_globs:
         - sensor.sol_ark_15k_1_*
         - sensor.sol_ark_15k_2_*
   ```

   For one inverter, the inverter 2 glob may be omitted.

5. Confirm recent points exist before importing dashboards.
6. Never commit tokens, passwords, internal certificates, or production database exports.

See [influxdb.md](influxdb.md) for retention and historian design.

## 8. Configure Grafana

1. Create an InfluxDB data source using Flux and the read-only token.
2. Install the Business Charts plugin:

   ```text
   volkovlabs-echarts-panel
   ```

3. Import the JSON files from `grafana/dashboards/`.
4. Select the InfluxDB data source during import.
5. If updating an existing dashboard, choose **Overwrite**.
6. Confirm hidden variables:

   ```text
   bucket = solark
   entity_prefix = sol_ark_15k_
   ```

### Dashboard use with one inverter

- Select inverter `1` on dashboards that provide an inverter selector.
- Operational Console and Electrical Trends are fully applicable.
- Energy Accounting uses inverter `1`; `System` is equivalent until a second inverter is present.
- Parallel System Detail may be omitted because its inverter 2 column will show no data.

### Dashboard use with two inverters

- Use `1` or `2` for per-inverter inspection.
- Use `System` where the dashboard provides a validated combined view.
- Use Parallel System Detail to compare the two inverters and identify imbalance.
- The MPPT comparison charts automatically display inverter 2 when its entities begin reaching InfluxDB.

See [grafana-dashboard-import.md](grafana-dashboard-import.md) for all dashboard variables, optional shunt entities, sign conventions, and update procedures.

## 9. Acceptance checks

### Required for either deployment

- gateway reachable and TCP 502 open;
- Python probe succeeds repeatedly;
- Home Assistant device remains available;
- battery voltage and SOC plausible;
- PV and load respond to operating changes;
- battery current and power direction verified;
- temperatures plausible;
- InfluxDB receives current timestamps;
- Grafana loads without query errors;
- no credentials appear in exported dashboard JSON or Git history.

### Additional checks for two inverters

- each integration entry points to a different endpoint;
- disabling one endpoint affects only the corresponding Home Assistant device;
- inverter 1 and inverter 2 values are independently plausible;
- MPPT and temperature differences are reasonable;
- combined values are not double-counting duplicated registers;
- loss of one inverter is visible rather than silently converted to zero.

## 10. Updating

Pull or download the new repository version, replace the complete `custom_components/solark15k` directory, restart Home Assistant, and overwrite the Grafana dashboards with the current JSON exports. Review [CHANGELOG.md](../CHANGELOG.md) before updating.

## 11. Troubleshooting path

Use this order:

```text
Ethernet/IP
-> TCP 502
-> gateway mode and serial settings
-> RS485 A/B/GND and termination
-> Python probe
-> Home Assistant integration
-> InfluxDB points
-> Grafana queries and variables
```

Detailed symptoms and corrective actions are in [troubleshooting.md](troubleshooting.md).
