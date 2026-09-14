# Waveshare Gateway Setup

## Target device

This project targets the **Waveshare 2-CH RS485 TO POE ETH (B)** gateway for the permanent two-inverter installation.

The reference design uses one RS485 channel per Sol-Ark 15K inverter.

Official Waveshare references:

- Product page: https://www.waveshare.com/product/iot-communication/wired-comm-converter/2-ch-rs485-to-eth-b.htm
- Wiki: https://www.waveshare.com/wiki/2-CH_RS485_TO_POE_ETH_(B)

Waveshare is credited as the source for gateway capabilities, serial-mode/terminal information, Ethernet/PoE behavior, and Modbus-gateway configuration details used by this guide. See `../THIRD_PARTY_NOTICES.md`.

## Temporary single-channel commissioning gateway

A **Waveshare RS232/485/422 TO POE ETH (B)** can be used to commission and validate one Sol-Ark at a time before the permanent dual-channel gateway is installed.

Official reference:

- https://www.waveshare.com/wiki/RS232/485/422_TO_POE_ETH_(B)

For RS485 mode on that unit, Waveshare labels the relevant terminals:

```text
TA = RS485 A / RS422 TX+
TB = RS485 B / RS422 TX-
PE = signal ground on the illustrated terminal block
```

### Field-verified polarity on the single-channel test unit

During commissioning on 2026-09-10, the nominal label-to-label connection below did **not** produce a Modbus response:

```text
Splitter pin 1 / RS485 B -> TB
Splitter pin 2 / RS485 A -> TA
Splitter pin 3 / GND     -> PE
```

Swapping only the two RS485 data conductors produced a valid Modbus TCP response from Sol-Ark register 183:

```text
Splitter pin 1 / RS485 B -> TA
Splitter pin 2 / RS485 A -> TB
Splitter pin 3 / GND     -> PE
```

The successful read returned raw value `5629` (`0x15FD`), which decodes to **56.29 V** using the V1.4 register scaling.

This is an installation-specific field result for the **single-channel RS232/485/422 TO POE ETH (B)** test unit. RS485 A/B naming is not consistent across all vendors, so do not generalize this swapped mapping to the permanent 2-CH gateway without validating that hardware independently.

Leave the RS422 receive terminals unused when operating in RS485 mode. If the unit is powered by PoE, its separate DC power input is not needed.

This single-channel unit is suitable for validating the complete path for Sol-Ark #1, then can be moved to Sol-Ark #2 for a second independent test. It does not replace the permanent dual-channel topology if simultaneous monitoring of both inverters is required.

## Recommended initial network plan

Example only:

```text
Channel 1 / Sol-Ark #1: 192.0.2.241:502
Channel 2 / Sol-Ark #2: 192.0.2.242:502
```

Use addresses appropriate for your LAN and preferably reserve them in DHCP or configure static addresses outside the DHCP pool.

## Serial settings

Configure the active RS485 channel for:

```text
Baud rate: 9600
Data bits: 8
Parity: None
Stop bits: 1
```

These values come from the public Sol-Ark Modbus RTU Protocol V1.4.

## Protocol mode

For native Home Assistant Modbus, use:

```text
Modbus TCP <--> Modbus RTU
TCP port 502
```

Do not use transparent serial-over-TCP mode for the primary configuration unless testing demonstrates a specific need.

## Storage/polling mode

Use the Waveshare in **non-storage** Modbus gateway mode.

The gateway should translate requests from Home Assistant; it should not independently poll and cache the inverter while Home Assistant is also polling.

Conceptually:

```text
Home Assistant request
        |
        v
Waveshare translates TCP -> RTU
        |
        v
Sol-Ark responds
        |
        v
Waveshare translates RTU -> TCP
        |
        v
Home Assistant receives response
```

## Channel-by-channel commissioning

### Channel 1

1. Connect only Sol-Ark #1.
2. Configure CH1 IP address, or the single-channel gateway IP during temporary testing.
3. Configure 9600/8/N/1.
4. Select Modbus TCP ↔ RTU.
5. Confirm port 502.
6. Disable storage/autopolling behavior.
7. Save/reboot the gateway if required.
8. Test TCP reachability.
9. Run the Python Modbus probe.

### Channel 2

Do not configure or connect CH2 until CH1 has proven stable.

Then repeat the same settings with a different IP address on the permanent two-channel gateway. If using the temporary single-channel gateway, move it to Sol-Ark #2 only after the Sol-Ark #1 test is complete.

## TCP reachability test

From Windows PowerShell:

```powershell
Test-NetConnection 192.0.2.241 -Port 502
```

Expected result:

```text
TcpTestSucceeded : True
```

This confirms only that the Ethernet/TCP service is reachable. It does **not** confirm that the Sol-Ark is answering Modbus.

## Modbus endpoint model

The public Sol-Ark V1.4 map defines the inverter slave ID as `1`.

Therefore:

```text
CH1 endpoint: 192.0.2.241:502, slave 1
CH2 endpoint: 192.0.2.242:502, slave 1
```

Do not substitute the inverter's Parallel-screen Modbus SN as the slave ID for this map.

## Timeout settings

Recommended initial values in Home Assistant:

```text
timeout: 5 seconds
message wait: ~100 ms
scan interval: 10 seconds for live values
```

The objective during commissioning is stability, not maximum sample rate.

## Termination

The public Sol-Ark V1.4 protocol specifies a 120-ohm terminator at the master end and states the inverter is internally terminated.

Before adding a resistor, verify whether the exact Waveshare hardware revision has built-in/selectable termination.

For a short first bench/commissioning test with the single-channel RS232/485/422 unit, begin by confirming wiring, polarity, protocol mode, and serial settings before adding external termination solely as a troubleshooting step. Record the final tested condition.

Record the final condition in the installation notes:

```text
CH1 termination: internal Waveshare / external 120 ohm / other
CH2 termination: internal Waveshare / external 120 ohm / other
```

## Network isolation

Recommended controls:

- no public Internet port forwarding to TCP 502;
- restrict gateway management access to trusted networks;
- keep configuration credentials private;
- use firewall rules between VLANs if Home Assistant is separated from infrastructure devices;
- document both gateway addresses.

## Validation checklist

Before moving to Home Assistant, confirm:

- [ ] CH1 responds to ping or is otherwise reachable.
- [ ] TCP 502 is open.
- [ ] RS485 A/B/GND are connected.
- [ ] serial format is 9600/8/N/1.
- [ ] protocol mode is Modbus TCP ↔ RTU.
- [ ] storage/autopolling mode is disabled.
- [ ] correct termination is present or the short-link test condition is documented.
- [ ] Sol-Ark BMS Lithium Batt mode is `00`.
- [ ] battery communication is CAN, not RS485.
- [ ] Python probe can read registers.

Do not proceed to dual-inverter aggregation until both inverters independently pass this checklist.
