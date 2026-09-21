# Support matrix

Version `1.1.0rc1` is the field-tested release candidate for read-only monitoring
and explicitly enabled master-inverter configuration controls. Read only remains
the default. Items listed as optional do not affect Home Assistant monitoring.

| Component | Supported/validated scope |
|---|---|
| Inverter | Sol-Ark 15K hybrid inverter using the published string-inverter register family |
| Topology | One inverter; two parallel inverters with master/slave communications |
| Gateway | Waveshare Modbus TCP-to-RTU gateway; one isolated channel per inverter |
| Gateway arrangements | One dual-channel unit or two independently addressed single-channel units |
| Modbus functions | FC3 holding-register reads; guarded FC16 quantity-one writes when Read/write is explicitly enabled |
| Unit IDs | Configurable `1..247`; field-tested pair uses inverter 1 = `1`, inverter 2 = `2` |
| Home Assistant | Home Assistant OS/Core 2026.9.2 field-tested; custom integration uses local polling |
| Host architecture | `amd64` field-tested; integration code is architecture-independent Python |
| InfluxDB | Optional InfluxDB 2.x historian; monitoring works without it |
| Grafana | Optional; Grafana 13.0.2 field-tested with four exported dashboards |
| Access modes | Read only (default); Read/write (explicit opt-in) |
| Writable device | Unit-ID-1 standalone/master only; no controls on unit-ID-2 slave or x2 device |
| Writable settings | Six TOU time/power/capacity/charge points; Generator Charge; Generator Start Capacity; Generator Charge Current; fallback Battery Absorption and Float voltage |
| Write safeguards | Read-before-write, expected-value comparison, immediate read-back, packed-bit preservation, serialized gateway access |
| Closed-loop batteries | BMS may overwrite absorption/float registers; those controls are intended as open-loop fallback settings |

Firmware behavior can differ. New firmware/hardware combinations should be
reported with inverter model, firmware versions, gateway model, topology, and
sanitized probe output. Never post tokens or public-facing gateway addresses.
