# Single-Inverter Quick Start

This is the complete installation path for monitoring one Sol-Ark 15K from Home Assistant. InfluxDB and Grafana are optional.

## What you need

- one Sol-Ark 15K;
- a **Waveshare 2-CH RS485 TO POE ETH (B)** gateway, using channel 1;
- Ethernet/PoE and a trusted local network;
- an RS485 connection with A, B, and signal ground;
- Home Assistant;
- battery communications using CAN rather than the RS485 conductors used by this monitor.

The single-channel **Waveshare RS232/485/422 TO POE ETH (B)** may also be used. The two-channel model leaves channel 2 available if another inverter is added later.

## 1. Connect the Waveshare

```text
Sol-Ark RS485 A/B/GND
        |
        v
Waveshare channel 1
        |
        v
Ethernet / PoE LAN
        |
        v
Home Assistant
```

Connect RS485 A, RS485 B, and signal ground. Use a twisted pair for A/B, keep the communications cable separated from high-voltage conductors, and follow the termination guidance in [waveshare-setup.md](waveshare-setup.md).

RS485 A/B labels are not consistent across all equipment. If Ethernet and TCP port 502 work but Modbus does not respond, verify signal ground and try reversing only A and B. The field-tested single-channel unit used:

```text
Splitter pin 1 / RS485 B -> Waveshare TA
Splitter pin 2 / RS485 A -> Waveshare TB
Splitter pin 3 / GND     -> Waveshare PE
```

That polarity is confirmed only for the single-channel test model. Validate the terminal labels on the two-channel model rather than assuming they are identical.

## 2. Configure the Waveshare

Open the Waveshare configuration page and assign a static address or DHCP reservation appropriate for the local network. Wherever this guide shows `XXX.XXX.XXX.XXX`, enter the actual Waveshare address.

Configure channel 1 as follows:

```text
Operating mode: Modbus TCP to Modbus RTU
Network role: TCP server
TCP port: 502
Serial interface: RS485
Baud rate: 9600
Data bits: 8
Parity: None
Stop bits: 1
Flow control: None
Storage/autopolling: Disabled
Sol-Ark slave ID: 1
```

Save the configuration and reboot the gateway if the Waveshare interface requests it. Do not forward port 502 through the Internet.

The Sol-Ark Parallel-screen Modbus number is not the slave ID for this integration. Use slave ID `1`.

## 3. Test the gateway and inverter

From PowerShell in the repository directory:

```powershell
Test-NetConnection XXX.XXX.XXX.XXX -Port 502
```

`TcpTestSucceeded` should be `True`. Then test battery-voltage register 183:

```powershell
py .\tools\solark_single_register_test.py XXX.XXX.XXX.XXX 183
```

A successful response should decode to a plausible battery-bank voltage. Run the broader read-only probe if desired:

```powershell
py .\tools\solark_modbus_probe.py XXX.XXX.XXX.XXX
```

If TCP succeeds but Modbus times out, check 9600/8/N/1, Modbus TCP-to-RTU mode, slave ID 1, A/B polarity, signal ground, and termination.

## 4. Install through HACS

1. Open **HACS → Integrations**.
2. Open the menu and select **Custom repositories**.
3. Enter:

   ```text
   https://github.com/mikeenea/solark15k-homeassistant-community
   ```

4. Select category **Integration**.
5. Install **Sol-Ark 15K Modbus**.
6. Restart Home Assistant.

For a manual installation, copy `custom_components/solark15k` into `/config/custom_components/solark15k`, then restart Home Assistant.

## 5. Add the inverter to Home Assistant

1. Open **Settings → Devices & services → Add integration**.
2. Search for **Sol-Ark 15K Modbus**.
3. Enter:

   ```text
   Name: Sol-Ark 15K #1
   Host: XXX.XXX.XXX.XXX
   Port: 502
   Slave ID: 1
   ```

4. Submit the form. The integration verifies the connection by reading battery-voltage register 183.
5. Confirm the device and entities appear under `sensor.sol_ark_15k_1_*`.

Do not run the legacy YAML commissioning package and the custom integration against the same gateway at the same time.

## 6. Optional InfluxDB and Grafana dashboards

Export this namespace to the `solark` InfluxDB bucket:

```text
sensor.sol_ark_15k_1_*
```

Import these dashboards from `grafana/dashboards/`:

```text
solark15k-operational-overview.json
solark15k-charts.json
solark15k-energy-totals.json
```

Select inverter `1`. The Parallel System Detail dashboard is optional for a one-inverter installation and will show inverter 2 as unavailable.

The Operational Console and Parallel System Detail require the Volkov Labs Business Charts plugin. See [grafana-dashboard-import.md](grafana-dashboard-import.md) for complete import instructions.

## Troubleshooting

| Symptom | Check |
|---|---|
| Waveshare page unavailable | Ethernet, PoE, IP address and subnet |
| TCP port 502 closed | TCP-server mode and configured port |
| TCP works but Modbus times out | TCP-to-RTU mode, 9600/8/N/1, slave ID, A/B/GND and termination |
| Works after swapping A/B | Terminal-label convention differs |
| Intermittent responses | Multiple polling clients, noise, grounding, termination or request rate |
| Home Assistant cannot add the integration | Stop other Modbus clients and rerun the register-183 test |

For additional diagnostics, see [troubleshooting.md](troubleshooting.md). The extensive validation material in the repository documents project development; ordinary users do not need to repeat it when the integration is operating normally.
