# Third-Party Notices and Attribution

This project is independently developed, but it relies on published protocol documentation, product documentation, open-source platform documentation, and implementation ideas from other projects. Those sources deserve explicit credit.

The guiding rule for this repository is simple: **when code, configuration, technical information, a pinout, protocol interpretation, workflow, or distinctive implementation idea is derived from someone else's work, identify the source and preserve any applicable license/notice requirements.**

A reference here is an attribution; it does not imply endorsement of this project by the referenced organization.

## Sol-Ark

This project references publicly available Modbus register information for Sol-Ark hybrid inverters, including the public **Sol-Ark Modbus RTU Protocol V1.4**.

Sol-Ark is the source for the project's protocol baseline, including register definitions, scaling information, serial settings, supported read behavior, termination guidance, and communications-port information used by the implementation.

The Sol-Ark protocol document, inverter manuals, product names, trademarks, and related materials remain the property of Sol-Ark or their respective owners. They are **not** licensed under the Apache License 2.0 used for this repository.

The project intentionally does **not** redistribute the Sol-Ark V1.4 PDF. Instead, it maintains an implementation-oriented register reference derived from the published protocol information.

The public V1.4 document states that Sol-Ark does not provide technical support for third-party Modbus devices or the Modbus map and that the inverter map is intended for read operations. This project's read-only-first design follows that published limitation.

## SolarAssistant

SolarAssistant is an independent product/project and is not affiliated with this repository.

SolarAssistant deserves specific credit for publicly documenting the practical **Sol-Ark 15K "2 in 1 BMS port"** arrangement used as a reference in this project: battery CAN communication and inverter RS485 monitoring can share the combined BMS/CAN connector through an appropriate splitter. Its documentation also identifies the RS485 conductors as pin 1 = RS485B, pin 2 = RS485A, and pin 3 = GND, and notes that parallel installations require a separate monitoring connection to each inverter.

Reference:

- SolarAssistant — Sol-Ark 15K-2P, "2 in 1 BMS port": https://solar-assistant.io/help/inverters/sol-ark/15K-2P/2-in-1-bms-port

The repository's splitter-reuse wiring approach was informed by that published documentation together with the Sol-Ark protocol documentation and field verification. SolarAssistant's observed rapid operational-telemetry behavior also served as a performance benchmark when designing this project's independently implemented tiered polling scheduler. No SolarAssistant source code, proprietary protocol implementation, or software assets are copied into this project.

SolarAssistant documentation, software, hardware, product names, images, and trademarks remain the property of their respective owners.

This repository does not redistribute SolarAssistant software or documentation.

## Waveshare

Waveshare International Limited is the source for hardware documentation used to configure the project's Ethernet/serial gateways, including serial-mode selection, RS485 terminal labeling, Ethernet/PoE behavior, web configuration, and Modbus gateway capabilities.

Primary project gateway:

- Waveshare 2-CH RS485 TO POE ETH (B) product page: https://www.waveshare.com/product/iot-communication/wired-comm-converter/2-ch-rs485-to-eth-b.htm
- Waveshare 2-CH RS485 TO POE ETH (B) wiki: https://www.waveshare.com/wiki/2-CH_RS485_TO_POE_ETH_(B)

Single-channel commissioning/test hardware may also use:

- Waveshare RS232/485/422 TO POE ETH (B) wiki: https://www.waveshare.com/wiki/RS232/485/422_TO_POE_ETH_(B)

Waveshare product names, documentation, images, and trademarks remain the property of Waveshare International Limited or their respective owners.

## Home Assistant

Home Assistant is an independent open-source project. This repository builds on Home Assistant's documented native Modbus and InfluxDB integration capabilities and follows Home Assistant entity/device conventions where applicable.

References:

- Home Assistant project: https://www.home-assistant.io/
- Modbus integration: https://www.home-assistant.io/integrations/modbus/
- InfluxDB integration: https://www.home-assistant.io/integrations/influxdb/

Home Assistant source code and documentation retain their own licenses. Configuration and original code written specifically for this repository are licensed as stated by this repository unless a file says otherwise.

## InfluxDB / InfluxData

InfluxDB is an independent time-series database product/project from InfluxData. This repository uses its documented bucket, token, retention, task, and Flux-query concepts for the long-term Sol-Ark historian.

References:

- InfluxData: https://www.influxdata.com/
- InfluxDB documentation: https://docs.influxdata.com/

InfluxDB software and documentation retain their respective licenses and ownership.

## Grafana

Grafana is an independent product/project. This repository uses Grafana as the visualization layer for Sol-Ark time-series data and follows Grafana's documented InfluxDB/Flux data-source model.

References:

- Grafana: https://grafana.com/
- Grafana documentation: https://grafana.com/docs/

Grafana software and documentation retain their respective licenses and ownership.

## Business Charts / Apache ECharts

The Operational Overview dashboard uses the Grafana **Business Charts** panel plugin (`volkovlabs-echarts-panel`) to render custom power gauges with Apache ECharts. The dashboard Function code stored in this repository is original project configuration written against the plugin's documented Charts Function interface; the repository does not vendor the plugin source code.

Business Charts was developed by Volkov Labs and is distributed under the Apache License 2.0. Grafana's plugin catalog currently publishes Business Charts under the same plugin ID and credits Volkov Labs for the original project.

References:

- Business Charts plugin: https://grafana.com/grafana/plugins/volkovlabs-echarts-panel/
- Business Charts documentation: https://grafana.com/docs/plugins/volkovlabs-echarts-panel/latest/
- Business Charts source: https://github.com/volkovlabs/business-charts
- Apache ECharts: https://echarts.apache.org/

Business Charts, Apache ECharts, their source code, documentation, names, and trademarks remain subject to their respective licenses and ownership.

## Standards and generic protocols

This project uses industry-standard technologies such as Modbus RTU, Modbus TCP, RS485, Ethernet, TCP/IP, and IEEE 802.3af PoE. References to those standards or protocols are descriptive and do not imply ownership by this repository.

## Source-code provenance policy

The current repository does not intentionally vendor or copy third-party source code. If third-party code is incorporated in the future, the contribution must:

1. identify the original author/project and source URL;
2. identify the applicable license;
3. preserve copyright/license notices required by that license;
4. clearly distinguish copied/adapted code from original project code;
5. update this file when the dependency or attribution is material to the repository.

The same principle applies to distinctive configuration patterns, pinouts, register interpretations, diagrams, or procedures derived from a specific external source: cite the source near the relevant documentation when practical, and include it here when it is material to the overall project.

## Licensing boundary

Unless a file says otherwise, original code, configuration, and documentation created for this repository are licensed under Apache License 2.0. Reference to a third-party protocol, product, trademark, documentation, or implementation idea does not change the ownership or license of the underlying third-party material.


## Dashboard design provenance

The Grafana dashboards are independently implemented in dashboard JSON, Flux, JavaScript, and Apache ECharts. They do not include SolarAssistant source code, frontend assets, CSS, icons, logos, screenshots, or proprietary software. Functional monitoring categories common to hybrid inverters are presented through this project's own operational-console layout, terminology, color system, calculations, and interaction model.

See `docs/dashboard-design.md` for the complete design and publication policy.
