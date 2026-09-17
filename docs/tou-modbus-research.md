# Experimental TOU Modbus Research

> **Development-only safety notice:** The public Sol-Ark V1.4 map used by this project documents read operations. It does not provide a supported writable TOU map. Do not use these procedures on an unattended system or expose TCP port 502 outside the trusted local network.

This work is isolated on the `dev/tou-modbus-research` branch. The released Home Assistant integration remains read-only.

## Research assumptions

- The master inverter is the configuration authority.
- The slave receives applicable settings through the Sol-Ark parallel link.
- All experimental Modbus requests target only the master inverter gateway.
- No community Deye/Sunsynk address is treated as a confirmed Sol-Ark address.
- Only one setting is changed at a time from the inverter screen during discovery.

## 1. Create the baseline snapshot

Temporarily disable the inverter 1 Home Assistant integration entry, or otherwise stop all polling of the master gateway channel, so the research session is its only Modbus client. Some TCP-to-RTU gateways can associate an RTU response with the wrong concurrent TCP request. From the repository root:

```powershell
py .\tools\solark_tou_research.py snapshot 192.0.2.241 `
  --start 0 --end 255 --chunk-size 8 --delay 2 --retries 3 `
  --output .\tou-before.json
```

Use the actual address of the **master** inverter gateway. Snapshot files contain raw register values and endpoint metadata but no credentials.

## 2. Change one setting from the master screen

Change exactly one low-risk TOU field by one small increment. Record:

- firmware versions;
- original displayed value;
- new displayed value;
- date and time;
- whether the slave screen inherited the change.

Do not change operating mode, grid-interconnection settings, battery voltage, battery current, or generator limits during initial discovery.

## 3. Create and compare the second snapshot

```powershell
py .\tools\solark_tou_research.py snapshot 192.0.2.241 `
  --start 0 --end 255 --chunk-size 8 --delay 2 --retries 3 `
  --output .\tou-after.json

py .\tools\solark_tou_research.py diff .\tou-before.json .\tou-after.json
```

Restore the setting from the master screen, take a third snapshot, and verify that the candidate register returns to its original value. Repeat the same experiment before classifying an address as confirmed.

## Guarded single-register write

Do not use `write-single` until an address and encoding have been confirmed through repeated screen-change comparisons. The command requires all of the following:

1. the expected current raw value;
2. the proposed raw value;
3. an address-specific confirmation phrase;
4. a process-scoped environment acknowledgement;
5. successful read-before-write comparison;
6. successful immediate read-back.

Example syntax only—these are deliberately placeholder values, not a known TOU register:

```powershell
$env:SOLARK_UNSAFE_WRITE_ACK = "I_ACCEPT_THE_RISK"
py .\tools\solark_tou_research.py write-single 192.0.2.241 `
  --address 999 --expected 123 --value 124 `
  --confirm "WRITE-MASTER-999-FROM-123-TO-124"
Remove-Item Env:\SOLARK_UNSAFE_WRITE_ACK
```

Immediately confirm the setting on both inverter screens. Restore the original value from the master screen unless the test plan explicitly requires retaining the new value.

## Confirmed TOU time registers

Field comparison on a parallel Sol-Ark 15K system confirmed the following master-inverter holding-register addresses:

| TOU period | PDU address | Example display | Raw value |
|---|---:|---:|---:|
| 1 | 250 | 00:00 | 0 |
| 2 | 251 | 04:00 | 400 |
| 3 | 252 | 08:00 | 800 |
| 4 | 253 | 12:00 | 1200 |
| 5 | 254 | 16:00 | 1600 |
| 6 | 255 | 20:00 | 2000 |

Times use decimal HHMM encoding: `raw = hour * 100 + minute`. Period 1 was independently verified at 00:00 (`0`), 00:30 (`30`), and 01:00 (`100`), including restoration to zero. In each screen-based test, inverter 2 inherited the master's setting through the parallel communications link.

An initial FC6 test of address 250 from `0` to `30` timed out and produced no change on either inverter or subsequent FC3 read-back. FC6 is therefore not considered supported for this field.

FC16 was then tested with a quantity of exactly one register. Writing address 250 from `0` to `30` succeeded, returned the expected FC16 response, and passed immediate FC3 read-back. The master displayed 00:30, the slave inherited 00:30, and the value persisted after closing and reopening the TOU screen. Restoration to 00:00 through the master screen returned address 250 to `0` on subsequent FC3 read-back.

### TOU time write-validation status

| Validation item | Result |
|---|---|
| Read master TOU time | Confirmed |
| Decimal HHMM encoding | Confirmed at 00:00, 00:30, and 01:00 |
| FC6 write | Not supported/ignored in field test |
| FC16 quantity-one write | Confirmed |
| Immediate FC3 read-back | Confirmed |
| Master display update | Confirmed |
| Slave inheritance | Confirmed |
| Persistence after screen navigation | Confirmed |
| Screen-based restoration and read-back | Confirmed |

## Evidence required before integration

A writable field will not be added to Home Assistant until we have recorded:

- Sol-Ark model and master firmware versions;
- register address and function code;
- raw encoding, units, range, and increment;
- at least two repeatable screen-change comparisons;
- successful write and read-back;
- master display confirmation;
- slave inheritance confirmation;
- behavior after inverter or communications restart;
- a safe restoration procedure.

TOU schedule controls should ultimately be applied as one validated configuration transaction with an explicit **Apply Schedule** action. They should not be continuously rewritten by an automation.

## Research checkpoint — 2026-09-17

Work is intentionally paused with normal Home Assistant monitoring re-enabled and TOU period 1 restored to 00:00.

### Confirmed findings

- The parallel-system master is the only endpoint that needs a configuration write.
- The slave inherits the master's TOU time through the Sol-Ark parallel communications link.
- PDU holding-register addresses 250–255 correspond to TOU periods 1–6.
- TOU times use decimal HHMM encoding (`hour * 100 + minute`).
- Address 250 was read-validated at 00:00 (`0`), 00:30 (`30`), and 01:00 (`100`).
- FC6 timed out and made no setting or register change.
- FC16 with starting address 250, quantity 1, and value 30 succeeded.
- The FC16 change was confirmed by immediate FC3 read-back, the master display, the slave display, and persistence after reopening the TOU screen.
- Restoring period 1 to 00:00 on the master returned address 250 to `0` on FC3 read-back.

### Safe system state at pause

- TOU period 1 is restored to 00:00.
- Normal Home Assistant monitoring is re-enabled.
- No experimental environment acknowledgement remains set.
- No writable controls have been added to the Home Assistant integration.
- All experimental code remains isolated on `dev/tou-modbus-research`.

### Next session

1. Switch to and update `dev/tou-modbus-research`.
2. Temporarily disable Home Assistant polling of the master gateway.
3. Take a fresh full baseline snapshot; do not rely on earlier local snapshots.
4. Record all six displayed TOU power limits and SOC limits.
5. Change only period 1 power by the smallest permitted increment and use before/after/restored snapshots to identify its register.
6. Repeat the read-only discovery process for period 1 SOC.
7. Map the other five fields from sequential values only after the first address and encoding are confirmed.
8. Map grid-charge and generator-charge permissions last because they may be packed bit fields.
9. Do not attempt another write until the candidate address, encoding, range, and screen-based restoration have been independently confirmed.

Local `tou-*.json` snapshots are research evidence and may contain private endpoint metadata. They are intentionally not committed. Preserve them locally if desired, but create a fresh baseline when work resumes.
