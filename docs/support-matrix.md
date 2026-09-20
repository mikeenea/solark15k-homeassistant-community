# Support matrix

Version `1.0.0` is the stable, field-tested, read-only Sol-Ark 15K release. Items listed as optional do not affect Home Assistant monitoring.

| Component | Supported/validated scope |
|---|---|
| Inverter | Sol-Ark 15K hybrid inverter using the published string-inverter register family |
| Topology | One inverter; two parallel inverters with master/slave communications |
| Gateway | Waveshare Modbus TCP-to-RTU gateway; one isolated channel per inverter |
| Gateway arrangements | One dual-channel unit or two independently addressed single-channel units |
| Modbus function | FC3 read holding registers only |
| Unit IDs | Configurable `1..247`; field-tested pair uses inverter 1 = `1`, inverter 2 = `2` |
| Home Assistant | Home Assistant OS/Core 2026.9.2 field-tested; custom integration uses local polling |
| Host architecture | `amd64` field-tested; integration code is architecture-independent Python |
| InfluxDB | Optional InfluxDB 2.x historian; monitoring works without it |
| Grafana | Optional; Grafana 13.0.2 field-tested with four exported dashboards |
| Writes/settings | Not supported on the stable branch |

Firmware behavior can differ. New firmware/hardware combinations should be
reported with inverter model, firmware versions, gateway model, topology, and
sanitized probe output. Never post tokens or public-facing gateway addresses.
