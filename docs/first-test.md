# First Test Procedure

## Purpose

This procedure validates one Sol-Ark 15K and one Ethernet/RS485 gateway path before any dual-inverter aggregation is enabled.

The project is read-only during commissioning. Do not configure Modbus write entities or send undocumented register writes.

## Before connecting the inverter

Confirm:

- the battery uses CAN communications, not RS485 battery communications;
- the inverter is configured with the applicable Lithium Batt mode required by the public Sol-Ark V1.4 protocol;
- the existing CAN/RS485 splitter remains in the Battery CAN Bus port;
- the RS485 monitoring lead is passive and contains only the required RS485 data/reference conductors;
- the gateway is configured for Modbus TCP to Modbus RTU conversion;
- serial format is 9600 baud, 8 data bits, no parity, 1 stop bit;
- the Modbus TCP listener is on port 502;
- the target unit/slave ID is 1.

## Step 1 — Ethernet reachability

From Windows PowerShell:

```powershell
Test-NetConnection XXX.XXX.XXX.XXX -Port 502
```

Expected:

```text
TcpTestSucceeded : True
```

This proves only that the TCP service is reachable. It does not prove the inverter is answering on RS485.

## Step 2 — Single-register read

Use the included read-only diagnostic:

```powershell
py .\tools\solark_single_register_test.py XXX.XXX.XXX.XXX 183
```

Register 183 is battery voltage and is a useful low-risk first target because it is easy to compare with the inverter display.

Expected successful pattern:

```text
Connecting to XXX.XXX.XXX.XXX:502
Reading holding register 183, slave 1, FC3, quantity 1
TX Modbus TCP: ...
RX Modbus TCP: ...
SUCCESS: register 183 raw value = ...
Decoded battery voltage = ... V
```

If the request times out, verify TCP reachability first. If TCP 502 is open but no Modbus response arrives, concentrate on gateway mode, serial settings, RS485 polarity, signal ground, and termination rather than Home Assistant.

### Field result — 2026-09-10

The temporary **Waveshare RS232/485/422 TO POE ETH (B)** initially timed out with nominal label-to-label A/B wiring. Swapping only the two RS485 data conductors while keeping signal ground unchanged produced a successful response.

Working field-test wiring:

```text
Splitter pin 1 / RS485 B -> Waveshare TA
Splitter pin 2 / RS485 A -> Waveshare TB
Splitter pin 3 / GND     -> Waveshare PE
```

Successful register 183 response:

```text
TX Modbus TCP: 00 01 00 00 00 06 01 03 00 B7 00 01
RX Modbus TCP: 00 01 00 00 00 05 01 03 02 15 FD
raw = 5629 (0x15FD)
interpreted = 56.29 V
```

This proves the PC -> Ethernet -> Waveshare -> RS485 -> Sol-Ark -> RS485 -> Waveshare -> Ethernet -> PC path is functioning for slave 1 / FC3 on the temporary single-channel gateway.

Do not assume this same A/B-to-terminal mapping applies to the permanent 2-CH gateway; validate each hardware model independently.

## Step 3 — Full commissioning probe

After a successful single-register read, run:

```powershell
py .\tools\solark_modbus_probe.py XXX.XXX.XXX.XXX
```

Then run the raw dump form:

```powershell
py .\tools\solark_modbus_probe.py XXX.XXX.XXX.XXX --dump
```

The main probe performs conservative reads over the useful commissioning ranges and decodes representative grid, inverter, load, battery, PV, temperature, relay, fault, and energy-counter values.

Compare the output to the Sol-Ark display before relying on it for long-term monitoring.

## Step 4 — Validate important live registers

At minimum compare:

```text
150 Grid L1-N voltage
151 Grid L2-N voltage
152 Grid L1-L2 voltage
169 Grid total power
175 Inverter total power
178 Load total power
182 Battery temperature
183 Battery voltage
184 Battery SOC
186 PV1 power
187 PV2 power
188 PV3 power
190 Battery power
191 Battery current
192 Load frequency
193 Inverter frequency
194 Grid relay state
195 Generator relay state
103-106 Fault words
```

Battery power/current sign conventions must be confirmed by observing known charge and discharge states.

## Step 5 — Validate lifetime counters

Check the low/high word behavior and scale for:

```text
72/73 Total battery charge
74/75 Total battery discharge
78/80 Total grid import
81/82 Total grid export
85/86 Total load
96/97 Total PV
```

Register 78/80 is deliberately non-contiguous in the public V1.4 map and therefore deserves explicit field validation.

## Step 6 — Home Assistant test package

Only after direct Modbus reads are working should the Home Assistant commissioning package be pointed at the live gateway.

File:

```text
homeassistant/packages/solark15k_test_package.yaml
```

Use the installation-specific gateway IP in Home Assistant, but keep generic/example IP addresses in the public repository where practical.

Validate Home Assistant configuration before restart.

## Step 7 — Historian verification

When Home Assistant entities have real numeric values, confirm that only the approved project namespaces are exported to the `solark` InfluxDB bucket.

Do not add unrelated Home Assistant entities just to create test data.

Then confirm Grafana sees the Sol-Ark measurements in the selected InfluxDB instance.

## Step 8 — Stability period

Run one inverter for at least 24 hours before moving to dual-inverter monitoring.

Observe:

- daytime PV production;
- battery charging;
- battery discharging;
- grid import/export if available;
- Home Assistant restart/reconnect behavior;
- any Modbus timeouts or unavailable periods;
- whether register values remain consistent with the inverter display.

## Step 9 — Second inverter

After Sol-Ark #1 passes, validate Sol-Ark #2 independently using the same process.

Do not create combined system totals until both inverter paths have been individually proven and the per-inverter/system-wide semantics of parallel-mode registers are understood.
