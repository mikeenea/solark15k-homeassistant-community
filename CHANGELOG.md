# Changelog

All notable project changes will be documented here.

Single-inverter monitoring is stable. Parallel-inverter aggregation remains in field validation.

## [0.2.2] - 2026-09-17

### Added

- Complete single-inverter quick start covering Waveshare installation, gateway configuration, connectivity testing, HACS installation, Home Assistant configuration, optional InfluxDB/Grafana setup, and concise troubleshooting.
- Traceable single-inverter field-validation record based on completed live-system testing.

### Changed

- Promoted the documented release boundary to stable single-inverter monitoring.
- Standardized user-facing gateway examples on `XXX.XXX.XXX.XXX`.
- Clarified that Parallel System Detail and inverter 2 data are optional for single-inverter users.
- Kept all experimental TOU write work isolated from the stable read-only release.

## [0.2.1] - 2026-09-17

### Added

- Public deployment guide with explicit one-inverter and two-parallel-inverter paths.
- Concise standalone-inverter installation guide.
- HACS custom-repository metadata.
- Dashboard configuration guidance for standalone and parallel systems.
- Independent four-dashboard public design system and configurable Grafana variables.
- Dashboard design provenance and publication policy.
- Public import documentation for Operational Console, Electrical Trends, Energy Accounting, and Parallel System Detail.

- Expanded project README and architecture.
- Apache-2.0 licensing boundary and third-party notices.
- Hardware selection and cabling guidance.
- Sol-Ark/SolarAssistant splitter wiring documentation.
- Waveshare 2-channel gateway setup procedure.
- First-inverter commissioning procedure.
- Native Home Assistant Modbus guidance.
- Dual-inverter validation methodology.
- InfluxDB multi-year historian design.
- Grafana dashboard architecture.
- Detailed troubleshooting guide.
- Sol-Ark V1.4 implementation-oriented register CSV.
- Fault-bit reference for documented V1.4 fault bits.
- Dependency-free Python Modbus TCP commissioning probe.
- Initial Home Assistant test package and commissioning dashboard.
- GitHub Actions validation for Python, YAML, and register CSV.
- Repository security and contribution guidelines.
- Project roadmap.
- Field-validation issue for Sol-Ark #1 / Waveshare CH1.

### Known validation items

- Battery power sign convention requires live validation.
- Battery current sign convention requires live validation.
- Battery temperature encoding should be confirmed against current firmware.
- Parallel-inverter register semantics require field classification before aggregation.
- Lifetime energy 32-bit word handling should be compared to inverter totals during commissioning.

### Changed

- Made the InfluxDB architecture platform-neutral; the UGREEN NAS is now documented as an optional field-tested example rather than a requirement.
- Corrected the integration documentation URL.
- Standardized documentation on the production `sol_ark_15k_1_*` and `sol_ark_15k_2_*` namespaces.
- Converted the installation checklist from site-specific status reporting to a reusable public checklist.

## Versioning plan

The repository and Home Assistant integration versions are aligned beginning with the first GitHub pre-release:

```text
0.2.1 -> first public pre-release; single-inverter monitoring and dual-inverter-ready dashboards
0.2.2 -> stable single-inverter monitoring release
0.3.0 -> parallel aggregation validated
0.4.0 -> InfluxDB/Grafana baseline complete
1.0.0 -> stable read-only dual-Sol-Ark 15K release
```
