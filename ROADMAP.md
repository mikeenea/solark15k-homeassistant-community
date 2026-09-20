# Roadmap

## Phase 0 - Repository foundation

- [x] Apache-2.0 licensing
- [x] Project README
- [x] Architecture documentation
- [x] Hardware and wiring documentation
- [x] Waveshare commissioning guidance
- [x] Native Home Assistant first-test package
- [x] Standalone read-only Python Modbus probe
- [x] V1.4 implementation-oriented register table
- [x] Fault-bit reference
- [x] InfluxDB historian design
- [x] Grafana dashboard plan
- [x] Initial field-validation issue

## Phase 1 - Sol-Ark #1 field validation

- [x] Install and configure an isolated Waveshare endpoint
- [x] Verify splitter RS485 wiring
- [ ] Record and independently verify the final master-side termination arrangement
- [x] Confirm TCP 502 connectivity
- [x] Run Python probe
- [x] Capture raw register data
- [x] Compare core values with Sol-Ark display
- [x] Confirm battery temperature encoding
- [x] Confirm battery power sign
- [x] Confirm battery current sign
- [x] Confirm energy-counter word ordering
- [x] Run Home Assistant monitoring for 24+ hours

Tracking issue: #1

## Phase 2 - Sol-Ark #2 validation

- [x] Configure a second isolated Waveshare endpoint
- [x] Determine inverter #2 unit ID independently
- [x] Run standalone probe against inverter #2
- [x] Validate the same register set
- [x] Run 24+ hour stability test
- [x] Document field behavior, including inverter #2 unit ID 2

## Phase 3 - Parallel-inverter semantics

- [x] Classify register 169 grid power
- [ ] Classify register 172 CT total
- [x] Classify register 175 inverter output
- [x] Classify register 178 load power
- [x] Classify registers 190/191 battery power/current
- [x] Classify daily and lifetime energy counters used by the integration
- [x] Determine aggregation rules for supported system values
- [x] Build validated automatic x2 system sensors

## Phase 4 - Production Home Assistant package

- [x] Replace `Sol-Ark Test` naming with production per-inverter names
- [x] Add complete L1/L2 current and power sensors
- [x] Add entity availability handling tied to coordinator health
- [ ] Add decoded fault binary sensors
- [x] Add grid import/export sensors
- [x] Add battery charge/discharge sensors after sign validation
- [x] Add validated x2 system totals
- [x] Add Energy Dashboard-ready entities
- [ ] Add entity categories where appropriate
- [x] Document migration from test package

## Phase 5 - Long-term historian

- [x] Configure InfluxDB export include list, including x2 entities
- [x] Validate ingestion and timestamps
- [ ] Define raw retention window
- [ ] Define 1-minute downsample retention
- [ ] Define 15-minute/hourly/day summaries
- [ ] Implement database backup plan
- [ ] Add selected historical query sensors to Home Assistant

## Phase 6 - Grafana dashboards

- [x] System overview
- [x] Dual-inverter balance
- [x] PV/MPPT performance
- [x] Battery
- [x] Grid
- [ ] Generator/AC-coupled
- [ ] Fault/event timeline
- [x] Monthly/yearly energy
- [ ] Year-over-year comparison
- [x] Store dashboard JSON in repository

## Phase 7 - Event analytics

- [ ] Grid outage detection
- [ ] Outage duration tracking
- [ ] Battery SOC at outage start/end
- [ ] Generator runtime during outage
- [ ] Fault snapshot automation
- [ ] Fault/event history in InfluxDB
- [ ] Inverter imbalance diagnostics
- [ ] MPPT underperformance detection

## Phase 8 - Compatibility and quality

- [ ] Firmware compatibility table
- [ ] Community validation reports
- [x] Automated YAML/Python validation in CI
- [x] Automated Grafana JSON, layout, variable, and Business Charts JavaScript validation
- [x] Register decoding and aggregation unit tests
- [ ] Full register-map replay tests
- [ ] Optional Modbus response replay tests
- [x] Release/versioning policy
- [x] Public single-inverter deployment guide
- [x] Public dual-inverter deployment guide
- [x] Security, contribution, license, notice, and dashboard-provenance documentation
- [x] HACS custom-repository metadata
- [x] First tagged stable single-inverter release

## Release path to 1.0

- [x] `0.3.1`: automatic two-inverter x2 entities and startup-race correction
- [x] `0.4.0`: field-tested documentation, x2 historian/dashboard baseline, and dashboard CI
- [x] `0.9.0`: expanded integration tests and clean-install/upgrade release candidate
- [x] `1.0.0`: stable read-only one- and two-inverter release

## Explicitly out of scope for initial releases

- undocumented Modbus writes;
- remote inverter configuration changes;
- cloud-control replacement;
- exposing TCP 502 to the public Internet.

These may be reconsidered only if supported by authoritative documentation and accompanied by an explicit safety review.
