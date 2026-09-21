# Changelog

## 1.1.0b3 - HHMM box correction

- Replace the six Home Assistant time entities with direct-entry number boxes.
- Store and display the inverter's native decimal HHMM values without conversion.
- Reject invalid HHMM entries such as 1260 or 2400 before any Modbus write.

## 1.1.0b2 - Complete six-period TOU preview

- Add all six decimal-HHMM TOU time entities.
- Expand box-mode power and capacity inputs from Point 1 to Points 1-6.
- Expand the packed-bit TOU charge switch from Point 1 to Points 1-6.
- Poll the complete settings range at the slower detail interval.
- Record Power Point 2 and Capacity Point 2 field validation.

## 1.1.0b1 - TOU development preview

- Merge the stable 1.0.0 integration into the TOU research branch.
- Add master-only, verified FC16 writes with read-before-write and read-back.
- Add box-mode TOU Power Point 1 and Capacity Point 1 number entities.
- Add TOU Charge Point 1 and global Generator Charge switches.
- Keep all controls off the inverter 2 and x2 devices.

All notable project changes will be documented here.

Single-inverter monitoring and the field-validated two-inverter read path are stable. Built-in x2 aggregation is available when exactly two entries are active.

## [1.0.0] - 2026-09-20

### Added

- Stable read-only monitoring support for one Sol-Ark 15K inverter or two Sol-Ark 15K inverters operating in parallel.
- Automatic x2 system entities for validated combined power, current, energy, voltage, frequency, and state-of-charge measurements.
- Four supported Grafana dashboards: Operational Console, Electrical Trends, Energy Accounting, and Parallel System Detail.
- Public installation, Waveshare commissioning, Home Assistant, InfluxDB, Grafana, troubleshooting, and single-/dual-inverter deployment documentation.

### Validated

- Field operation with one inverter and with two parallel inverters using isolated Waveshare Modbus TCP-to-RTU endpoints.
- Configurable Modbus unit IDs, including the field-tested inverter 1 / unit 1 and inverter 2 / unit 2 arrangement.
- Signed battery power/current handling, 32-bit energy counters, x2 aggregation rules, InfluxDB ingestion, HACS installation, and dashboard imports.
- Automated compilation, unit, metadata, release-boundary, documentation-link, register-map, YAML/JSON, and Grafana-dashboard checks.

### Changed

- Promoted the 0.9.0 release candidate to the stable 1.0.0 release.
- Finalized whole-system power, grid-status, disconnected-grid, and steady-frequency dashboard behavior.
- Updated public documentation to distinguish the validated 1.0.0 scope from future enhancements.

### Safety boundary

- The stable integration remains strictly read-only and contains no Modbus write implementation.
- Experimental TOU research remains isolated from the stable branch and is not included in this release.

## [0.9.0] - 2026-09-19

### Added

- Dependency-free regression tests for signed 16-bit decoding, battery power/current sign orientation, low-word-first 32-bit energy counters, x2 sums, arithmetic means, missing-source behavior, x2 creation rules, and InfluxDB line-protocol serialization.
- A release-contract test covering HACS metadata, required package files, the four supported dashboards, version alignment, and the stable read-only boundary.
- Canonical Home Assistant `strings.json` metadata alongside the English translation.
- A clean-install and upgrade release-candidate checklist for one-inverter and two-inverter systems.
- A field-tested support matrix covering topology, gateway arrangements, unit IDs, Home Assistant, InfluxDB, and Grafana.

### Changed

- Centralized register decoding and x2 aggregation calculations so the production entities and regression tests use the same implementation.
- Centralized numeric InfluxDB line-protocol generation and made malformed, Boolean, non-numeric, and non-finite values fail closed.

### Release boundary

- `0.9.0` is the release candidate for the stable read-only `1.0.0` package.
- Modbus writes and remote inverter configuration remain excluded from the stable branch.

## [0.4.0] - 2026-09-19

### Added

- Automated validation for all four supported Grafana dashboard exports, including JSON parsing, unique panel IDs, grid-layout overlap detection, variable references, and Business Charts JavaScript syntax.
- Public documentation for both supported parallel gateway arrangements: one dual-channel Waveshare or two independently addressed single-channel Waveshare gateways.
- Required `sensor.sol_ark_15k_x2_*` InfluxDB export guidance throughout the primary deployment path.

### Changed

- Corrected remaining documentation that assumed both parallel inverters use Modbus unit ID 1. Unit ID must be tested per endpoint; the field-tested pair uses unit ID 1 for inverter 1 and unit ID 2 for inverter 2.
- Updated the roadmap to reflect completed single-inverter, dual-inverter, x2, historian, dashboard, and release work.
- Optimized the Operational Console System view and Electrical Trends Whole-System Power panel to use verified x2 series directly.

### Release boundary

- Monitoring remains strictly read-only.
- TOU and other Modbus write research remain isolated from the stable release branch.
- Advanced event analytics, automated register writes, and support for other inverter models remain outside the 0.4.0 scope.

## [0.3.1] - 2026-09-18

### Fixed

- Removed a startup race that could prevent the x2 device from being created when both inverter entries initialized concurrently.
- Registered each inverter coordinator explicitly and created the x2 entities as soon as the second coordinator registered.

## [0.3.0] - 2026-09-18

### Added

- Automatic `Sol-Ark 15K x2` virtual device when exactly two inverter entries are active.
- Combined `sensor.sol_ark_15k_x2_*` entities for PV, load, grid, generator, and battery measurements.
- Arithmetic-mean x2 sensors for corresponding MPPT voltages and other shared voltages, frequencies, battery voltage, and battery state of charge.
- Summed x2 current, power, and energy sensors, including calculated total PV, load, and grid current.

### Changed

- Preserved all individual inverter entities while removing the need for user-authored Home Assistant aggregation templates.
- Kept single-inverter installations unchanged; x2 entities are created only with exactly two active entries.


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

- Development-only TOU register snapshot, comparison, and guarded single-register research utility.
- Field-validated TOU time registers 250–255, decimal HHMM encoding, and master-only FC16 quantity-one writes with parallel-slave inheritance.
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
0.9.0 -> expanded tests and clean-install/upgrade release candidate
1.0.0 -> stable read-only dual-Sol-Ark 15K release
```
