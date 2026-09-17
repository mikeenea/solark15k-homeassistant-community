# Single-inverter deployment

This document is the concise path for one standalone Sol-Ark 15K. For full prerequisites, InfluxDB, Grafana, acceptance tests, and troubleshooting, use [deployment-guide.md](deployment-guide.md).

## Topology

```text
Sol-Ark 15K
  -> isolated RS485 A/B/GND
  -> Modbus TCP-to-RTU gateway
  -> Home Assistant Sol-Ark 15K Modbus entry
  -> optional InfluxDB
  -> optional Grafana
```

## Gateway configuration

```text
Protocol: Modbus TCP <-> Modbus RTU
TCP port: 502
Serial: 9600/8/N/1
Storage/autopolling: disabled
Slave ID: 1
```

Validate the endpoint before configuring Home Assistant:

```powershell
Test-NetConnection <gateway-ip> -Port 502
python tools/solark_modbus_probe.py <gateway-ip>
```

## Home Assistant

Install `custom_components/solark15k`, restart Home Assistant, and add **Sol-Ark 15K Modbus** with:

```text
Name: Sol-Ark 15K #1
Host: <gateway-ip>
Port: 502
Slave ID: 1
```

Expected entity namespace:

```text
sensor.sol_ark_15k_1_*
```

Do not run the YAML commissioning package and custom integration against the inverter simultaneously.

## InfluxDB and Grafana

Export only:

```text
sensor.sol_ark_15k_1_*
```

Import Operational Console, Electrical Trends, and Energy Accounting. Select inverter `1`. Parallel System Detail is optional and will show no data for inverter 2.

## Acceptance

Confirm battery voltage, SOC, PV, load, temperature, battery-current direction, and battery-power direction against the inverter display. Verify current timestamps in InfluxDB before troubleshooting Grafana.
