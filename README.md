# Sol-Ark 15K Home Assistant Modbus

A local, read-only Home Assistant integration for one Sol-Ark 15K inverter or two Sol-Ark 15K inverters operating in parallel, using native Modbus TCP through an Ethernet-to-RS485 gateway.

This project provides independent, local access to inverter telemetry through documented Sol-Ark Modbus interfaces, Home Assistant, InfluxDB, and Grafana. A standalone installation uses one isolated RS485 endpoint. A parallel installation uses two isolated endpoints, one per inverter.

> **Project status:** stable read-only monitoring for one inverter and field-validated monitoring for two parallel inverters, including automatic x2 system entities.

## Start here

For one inverter, use the concise [Single-Inverter Quick Start](docs/single-inverter.md). It includes Waveshare wiring and configuration, connection testing, HACS installation, Home Assistant setup, and optional dashboards.

Use the [deployment guide](docs/deployment-guide.md) for the complete one- or two-inverter sequence:

- **One inverter:** one gateway endpoint, one Home Assistant integration entry, and the inverter `1` dashboard selection.
- **Two parallel inverters:** two electrically independent RS485 endpoints and two Home Assistant integration entries. The integration automatically creates a `Sol-Ark 15K x2` device with combined system entities, while retaining inverter `1` and inverter `2` entities.

Field-validation history is recorded in [single-inverter-validation.md](docs/single-inverter-validation.md). Users do not need to repeat the development tests when their installation is operating normally. Parallel-system details are in [dual-inverter.md](docs/dual-inverter.md).

Each inverter uses its own TCP endpoint. Confirm the Modbus unit ID independently: field testing found unit ID `1` on inverter 1 and unit ID `2` on inverter 2.

### Quick installation outline

1. Configure the gateway for Modbus TCP to RTU, TCP 502, and 9600/8/N/1.
2. Validate each inverter independently with `tools/solark_modbus_probe.py`.
3. Install `custom_components/solark15k` manually or as a HACS custom repository.
4. Add one integration entry per inverter.
5. Configure InfluxDB export for `sensor.sol_ark_15k_1_*`, `sensor.sol_ark_15k_2_*`, and the automatically created `sensor.sol_ark_15k_x2_*` system entities.
6. Import the four supported Grafana dashboards and select the correct bucket/data source.

## What this project provides

- A native Home Assistant custom integration for read-only Sol-Ark 15K telemetry.
- Waveshare 2-CH RS485 TO POE ETH (B) setup guidance.
- Reuse of the RS485 side of a Sol-Ark/SolarAssistant CAN/RS485 splitter where applicable.
- A no-dependency Python Modbus TCP probe for commissioning.
- A working register reference derived from the public Sol-Ark Modbus RTU Protocol V1.4.
- Single-inverter commissioning before dual-inverter deployment.
- Automatic dual-inverter x2 entities: summed power/current/energy and arithmetic-mean corresponding voltages.
- Home Assistant dashboard examples.
- InfluxDB long-term retention design.
- Platform-neutral InfluxDB deployment guidance, plus a tested UGREEN NAS example.
- Grafana dashboard design for multi-year historical analysis.
- Fault-word monitoring and future fault decoding.
- Troubleshooting and validation procedures.
- A complete [single- and dual-inverter deployment guide](docs/deployment-guide.md).

## Included Grafana dashboards

The repository provides four supported, independently designed dashboards:

- **Operational Console** for current operating state and power flow;
- **Electrical Trends** for detailed voltage, current, power, frequency, temperature, battery, and MPPT history;
- **Energy Accounting** for daily and monthly energy totals;
- **Parallel System Detail** for side-by-side inverter operations.

Dashboard installation and configuration are documented in [docs/grafana-dashboard-import.md](docs/grafana-dashboard-import.md). Design provenance and public contribution rules are documented in [docs/dashboard-design.md](docs/dashboard-design.md).

## Target architecture

```text
Sol-Ark 15K #1
Battery/CAN port
      |
      v
Existing CAN/RS485 splitter
      |
      +---- CAN --------------------> Battery BMS
      |
      +---- RS485 ------------------> Waveshare CH1
                                        |
                                        | Modbus TCP
                                        v
                                  Home Assistant
                                        |
                                        +--> Recorder / HA statistics
                                        |
                                        +--> InfluxDB API :8086
                                                |
                                                v
                                  Persistent InfluxDB host
                                  InfluxDB OSS 2.x / Flux
                                         bucket: solark
                                                |
                                                v
                                             Grafana

Sol-Ark 15K #2
Battery/CAN port
      |
      v
Existing CAN/RS485 splitter
      |
      +---- CAN --------------------> Battery BMS
      |
      +---- RS485 ------------------> Waveshare CH2
```

The two inverter RS485 links remain electrically independent. Each Waveshare channel is treated as a separate Modbus TCP gateway.

InfluxDB may run on a dedicated Linux host, VM, Docker host, supported NAS, or the Home Assistant host. Choose a location with persistent storage, backups, stable networking, and enough resources for the desired retention period. Grafana may run on the same host or elsewhere.

## Protocol baseline

The project currently uses the public **Sol-Ark Modbus RTU Protocol V1.4** as its primary register reference. For the 15K, the document specifies:

- read operations only;
- Modbus function code 03 for holding-register reads;
- 9600 baud;
- 8 data bits;
- no parity;
- 1 stop bit;
- fixed slave ID `0x01` for this map;
- signal ground connected between inverter and master;
- 120-ohm termination at the master side;
- CAN-based battery communications can coexist with this read protocol when the inverter is configured appropriately;
- RS485-based battery communications cannot be used simultaneously with this protocol.

The Parallel-screen **Modbus SN is not the slave ID for this map**. Each independently connected inverter is polled as slave ID 1.

## Important safety and support notice

This repository is an independent community project. It is **not affiliated with, endorsed by, or supported by Sol-Ark**.

The Sol-Ark V1.4 document states that Sol-Ark does not provide technical support for third-party Modbus devices or the Modbus map and that the map is intended for read operations. This repository therefore begins with a strict read-only design.

Do not add register writes unless the applicable Sol-Ark documentation explicitly supports them and the risks are understood.

## Hardware

### Recommended gateway — Waveshare 2-CH RS485 TO POE ETH (B)

[![Waveshare 2-CH RS485 TO POE ETH (B)](https://www.waveshare.com/wiki/Special:Redirect/file/2-CH%20RS485%20TO%20ETH%20%28B%29.jpg)](https://www.waveshare.com/product/iot-communication/wired-comm-converter/2-ch-rs485-to-eth-b.htm)

> **Use the PoE model:** select **2-CH RS485 TO POE ETH (B)**, not the non-PoE **2-CH RS485 TO ETH (B)** variant.

Why this gateway fits the project:

- two isolated RS485 channels that can operate independently;
- PoE-powered Ethernet on the PoE variant, IEEE 802.3af compliant;
- Modbus TCP ↔ Modbus RTU gateway support;
- web-based configuration;
- DIN-rail-capable industrial enclosure;
- one RS485 channel can be dedicated to each Sol-Ark 15K.

For a two-inverter installation:

```text
Waveshare CH1 -> Sol-Ark #1 RS485
Waveshare CH2 -> Sol-Ark #2 RS485
```

Official Waveshare sources:

- [Waveshare product page — 2-CH RS485 TO ETH (B) / 2-CH RS485 TO POE ETH (B)](https://www.waveshare.com/product/iot-communication/wired-comm-converter/2-ch-rs485-to-eth-b.htm)
- [Waveshare Wiki — 2-CH RS485 TO POE ETH (B)](https://www.waveshare.com/wiki/2-CH_RS485_TO_POE_ETH_(B))
- [Waveshare Wiki image source](https://www.waveshare.com/wiki/File:2-CH_RS485_TO_ETH_(B).jpg)

The official Waveshare page covers both the standard Ethernet and PoE variants. This project specifically targets the **PoE** version.

### Temporary single-inverter test gateway

A **Waveshare RS232/485/422 TO POE ETH (B)** may be used to validate one Sol-Ark at a time during commissioning. In RS485 mode, the project's test wiring uses Waveshare's documented `TA` (RS485 A), `TB` (RS485 B), and signal-ground terminal. See [`docs/waveshare-setup.md`](docs/waveshare-setup.md) for the exact test wiring and the official Waveshare source link.

See [`docs/hardware.md`](docs/hardware.md), [`docs/wiring.md`](docs/wiring.md), and [`docs/waveshare-setup.md`](docs/waveshare-setup.md).

## Recommended commissioning sequence

Do not begin by connecting both inverters.

1. Confirm the battery is using CAN communications rather than RS485 battery communications.
2. Connect only Sol-Ark #1 to Waveshare channel 1, or to the temporary single-channel Waveshare test gateway.
3. Configure the Waveshare for Modbus TCP ↔ RTU, TCP port 502, and 9600/8/N/1 serial settings.
4. Verify TCP reachability.
5. Run the included Python probe.
6. Compare live values with the Sol-Ark display.
7. Install and configure the Home Assistant custom integration.
8. Validate signed values and temperature scaling.
9. Run for a stability period.
10. Repeat on Sol-Ark #2 / Waveshare channel 2, or move the temporary single-channel test gateway to Sol-Ark #2.
11. After both entries are active, confirm the automatically created `Sol-Ark 15K x2` device and its combined entities.

See [`docs/first-test.md`](docs/first-test.md).

## Repository layout

```text
.
├── README.md
├── LICENSE
├── NOTICE
├── THIRD_PARTY_NOTICES.md
├── docs/
│   ├── architecture.md
│   ├── deployment-guide.md
│   ├── single-inverter.md
│   ├── hardware.md
│   ├── wiring.md
│   ├── waveshare-setup.md
│   ├── first-test.md
│   ├── home-assistant.md
│   ├── dual-inverter.md
│   ├── influxdb.md
│   ├── nas-influxdb.md
│   ├── grafana.md
│   └── troubleshooting.md
├── custom_components/
│   └── solark15k/
│       ├── manifest.json
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       └── system_sensor.py
├── grafana/
│   └── dashboards/
│       ├── solark15k-operational-overview.json
│       ├── solark15k-charts.json
│       ├── solark15k-energy-totals.json
│       └── solark15k-system-detail.json
├── docker/
│   └── influxdb-compose.yml
├── homeassistant/
│   ├── packages/
│   │   └── solark15k_test_package.yaml
│   └── dashboards/
│       └── solark15k_test_dashboard.yaml
├── modbus/
│   └── solark15k_v1_4_register_map.csv
└── tools/
    └── solark_modbus_probe.py
```

## Long-term data plan

Home Assistant should not be asked to retain every high-frequency state change for many years in its normal Recorder database. The intended architecture is:

- Home Assistant Recorder for normal HA operation and short-term history;
- Home Assistant long-term statistics for native energy/statistical history;
- InfluxDB OSS 2.x on a persistent host for high-resolution time-series retention;
- Grafana for advanced historical visualization and analysis.

The `solark` bucket is deliberately restricted to entities created by this integration and project-defined formulas derived from those entities. It is not a general Home Assistant historian.

The planned retention model keeps high-resolution data for a shorter period while retaining downsampled one-minute, fifteen-minute, hourly, and daily data for years.

The supplied Docker example is pinned to `influxdb:2.8.0`. Do not use a generic `latest` tag. Any move to InfluxDB 3 should be deliberate and include data migration, Grafana query conversion, compatibility testing, and rollback planning.

See the platform-neutral [`docs/influxdb.md`](docs/influxdb.md), the optional tested [`docs/nas-influxdb.md`](docs/nas-influxdb.md) UGREEN example, and [`docs/grafana.md`](docs/grafana.md).

## Current field-validation priorities

Before the project is considered production-ready, validate these against live 15K data:

- battery power sign convention;
- battery current sign convention;
- battery temperature encoding on current firmware;
- grid/load/battery values in a parallel two-inverter system;
- which measurements are per-inverter versus already system-wide;
- long-term energy counter word ordering;
- fault-word behavior during real events.

## Credits and source attribution

This project depends on published technical information and implementation ideas from other projects and vendors. Material sources are credited in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), and source links are also placed near derived technical information when practical.

In particular, the repository currently credits:

- **Sol-Ark** for the public Modbus protocol/register documentation that forms the protocol baseline;
- **SolarAssistant** for its published Sol-Ark 15K "2 in 1 BMS port" guidance and RS485 pinout reference that informed the splitter-reuse approach;
- **Waveshare** for gateway hardware, terminal, PoE, and Modbus-gateway documentation;
- **Home Assistant** for the native Modbus/InfluxDB platform and documented integration conventions;
- **InfluxData/InfluxDB** and **Grafana** for the historian/query/visualization technologies used by the project.

If future work adapts third-party code, configuration, a distinctive implementation idea, pinout, diagram, or procedure, the project policy is to identify the source and preserve any applicable license or notice requirements.

## Contributing

Issues and pull requests are welcome. For any proposed register change, include:

- inverter model;
- firmware version if known;
- register address;
- raw value;
- interpreted value;
- comparison source, such as the inverter display;
- whether the inverter is standalone or parallel;
- source/documentation URL when external work materially informs the change.

Avoid submitting undocumented write-register functionality. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the attribution/provenance requirements.

## License

Original code, configuration, and documentation in this repository are licensed under the **Apache License 2.0**. Third-party documentation, trademarks, and product names remain the property of their respective owners. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
