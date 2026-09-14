# Contributing

Thank you for helping validate and improve the Sol-Ark 15K Home Assistant Modbus project.

## Project principles

1. **Read-only first.** Do not add undocumented Modbus writes.
2. **Evidence over assumptions.** Register changes should be supported by documentation or repeatable field observations.
3. **Preserve raw data.** When a decoded value is uncertain, keep the raw register reading available.
4. **One variable at a time.** Troubleshooting and commissioning changes should be isolated.
5. **Parallel systems require validation.** Do not assume a register is per-inverter or system-wide without evidence.
6. **Credit the source.** If a change is based on someone else's code, documentation, pinout, protocol interpretation, diagram, workflow, or distinctive implementation idea, identify the source and preserve any required license notices.

## Before opening an issue

Please review:

- `docs/first-test.md`
- `docs/troubleshooting.md`
- `modbus/solark15k_v1_4_register_map.csv`
- `THIRD_PARTY_NOTICES.md`

## Register-report template

Include the following information:

```text
Inverter model: Sol-Ark 15K
Firmware version:
Standalone or parallel:
Parallel role:
Parallel Modbus SN:
Waveshare model:
Waveshare channel/IP:
Register address:
Raw value:
Decoded value:
Expected value:
Comparison source (LCD, meter, other):
Documentation/source URL if applicable:
Operating state:
  PV:
  Load:
  Battery charge/discharge:
  Grid import/export:
Notes:
```

## Communication-problem template

```text
Waveshare IP reachable: yes/no
TCP 502 reachable: yes/no
Serial settings: 9600/8/N/1 confirmed yes/no
Protocol mode: Modbus TCP <-> RTU confirmed yes/no
Storage/autopolling disabled: yes/no
Slave ID: 1
A/B continuity checked: yes/no
Ground continuity checked: yes/no
Termination method:
Battery communication: CAN/RS485
BMS Lithium Batt mode:
Python probe output/error:
Home Assistant log excerpt:
```

## Pull requests

For code or configuration changes:

- explain the problem being solved;
- identify the affected register(s);
- include test evidence;
- identify external sources that materially informed the change;
- preserve third-party copyright/license notices when required;
- avoid unrelated formatting changes;
- update documentation when behavior changes;
- update `THIRD_PARTY_NOTICES.md` when a new material source or dependency is introduced;
- do not include secrets, passwords, private IP credentials, or API tokens.

### Attribution/provenance checklist

If your change uses or adapts someone else's work, include enough information for a reviewer to trace it:

```text
Source project/author:
Source URL:
License (if code/content is copied or adapted):
What was used or adapted:
Where attribution is recorded in this repository:
```

Do not present externally derived work as original. When practical, cite technical sources directly in the file or documentation section where the derived information is used, in addition to the repository-level notice.

## Home Assistant YAML changes

When changing YAML:

- preserve unique IDs;
- use correct device/state classes;
- avoid silently converting unavailable inputs to zero for critical system totals;
- document sign conventions;
- document any firmware-sensitive scaling;
- run Home Assistant configuration validation before merging when possible.

## Python probe changes

The commissioning probe intentionally uses only the Python standard library. Keep it dependency-free unless there is a compelling reason to change that design.

Do not add write-function support to the commissioning probe.

If code from another Modbus implementation is used or adapted, cite the source and verify license compatibility before merging.

## InfluxDB/Grafana contributions

Do not commit:

- database credentials;
- tokens;
- passwords;
- private URLs containing secrets;
- personally identifying site information.

Dashboard JSON and query examples should use generic datasource references where possible.

If a dashboard/query is materially adapted from a published example, include a source link and applicable license/credit information.

## Third-party material

Do not commit third-party manuals or PDFs unless redistribution rights are clear. Prefer links, citations in documentation, and implementation-oriented tables created for this project.

See `THIRD_PARTY_NOTICES.md` for current project credits and source-attribution policy.

## Licensing

By contributing original material to this repository, you agree that it may be distributed under the repository's Apache License 2.0 unless explicitly stated otherwise.
