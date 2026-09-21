# Experimental TOU Modbus Research

> **Development-only safety notice:** The public Sol-Ark V1.4 map used by this project documents read operations. It does not provide a supported writable TOU map. Do not use these procedures on an unattended system or expose TCP port 502 outside the trusted local network.

This work is isolated on the `dev/tou-modbus-research` branch. The released Home Assistant integration remains read-only.

## Writable-control inventory

The user-supplied SolarAssistant entity screenshots have been translated into an independent Sol-Ark/Deye register-candidate and Home Assistant control matrix in [writable-controls-inventory.md](writable-controls-inventory.md). The screenshots are treated only as evidence that the control concepts exist; they are not evidence of register addresses and no SolarAssistant code, MQTT topics, or assets are used.

The inventory records confirmed, strong-candidate, candidate, unresolved, and blocked fields. It also defines a phased master-only implementation: the master receives every experimental write and the slave is expected to inherit applicable settings through the parallel communications channel.

## Research assumptions

- The master inverter is the configuration authority.
- The slave receives applicable settings through the Sol-Ark parallel link.
- All experimental Modbus requests target only the master inverter gateway.
- No community Deye/Sunsynk address is treated as a confirmed Sol-Ark address.
- Only one setting is changed at a time from the inverter screen during discovery.

## 1. Create the baseline snapshot

Temporarily disable the inverter 1 Home Assistant integration entry, or otherwise stop all polling of the master gateway channel, so the research session is its only Modbus client. Some TCP-to-RTU gateways can associate an RTU response with the wrong concurrent TCP request. From the repository root:

```powershell
py .\tools\solark_tou_research.py snapshot XXX.XXX.XXX.XXX `
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
py .\tools\solark_tou_research.py snapshot XXX.XXX.XXX.XXX `
  --start 0 --end 255 --chunk-size 8 --delay 2 --retries 3 `
  --output .\tou-after.json

py .\tools\solark_tou_research.py diff .\tou-before.json .\tou-after.json
```

Restore the setting from the master screen, take a third snapshot, and verify that the candidate register returns to its original value. Repeat the same experiment before classifying an address as confirmed.

## Guarded single-register write

Do not use `write-one-fc16` until an address and encoding have been confirmed through repeated screen-change comparisons. The command requires all of the following:

1. the expected current raw value;
2. the proposed raw value;
3. an address-specific confirmation phrase;
4. a process-scoped environment acknowledgement;
5. successful read-before-write comparison;
6. successful immediate read-back.

Example syntax for the confirmed FC16 quantity-one path. The address and values are deliberately non-operational placeholders:

```powershell
$env:SOLARK_UNSAFE_WRITE_ACK = "I_ACCEPT_THE_RISK"
py .\tools\solark_tou_research.py write-one-fc16 XXX.XXX.XXX.XXX `
  --address 999 --expected 123 --value 124 `
  --confirm "WRITE-FC16-MASTER-999-FROM-123-TO-124"
Remove-Item Env:\SOLARK_UNSAFE_WRITE_ACK
```

Immediately confirm the setting on both inverter screens. Restore the original value from the master screen unless the test plan explicitly requires retaining the new value.

## Deye protocol cross-reference

A Deye document titled *Modbus RTU Protocol*, revision V117 (2021-04-08), was reviewed as a research reference. The document is marked “All rights reserved,” so the complete PDF is not redistributed in this public repository. This section records only the relevant technical conclusions and our independent field-validation status.

The document applies to microinverters, string inverters, and storage inverters. The Sol-Ark 15K appears to use common/string-inverter measurement registers together with the energy-storage variable region for battery, generator, and TOU functions. Applicability must be established register by register because Sol-Ark firmware can extend ranges or change behavior.

The reference defines FC3 (0x03) for register reads and FC16 (0x10) for single- or multiple-register writes. This matches field testing: FC6 did not change TOU period 1, while FC16 quantity one succeeded and passed immediate FC3 read-back.

### Candidate TOU register family

| Function | Period 1 | Period 2 | Period 3 | Period 4 | Period 5 | Period 6 | Reference encoding |
|---|---:|---:|---:|---:|---:|---:|---|
| Time | 250 | 251 | 252 | 253 | 254 | 255 | Decimal HHMM; field-confirmed |
| Power | 256 | 257 | 258 | 259 | 260 | 261 | 1 W; candidate |
| Battery voltage | 262 | 263 | 264 | 265 | 266 | 267 | 0.01 V; candidate |
| Battery SOC | 268 | 269 | 270 | 271 | 272 | 273 | 1%; candidate |
| Charge/mode flags | 274 | 275 | 276 | 277 | 278 | 279 | Bitfield; candidate |

For registers 274–279, the reference identifies bit 0 as grid-charge enable and bit 1 as generator-charge enable. It also labels bits 2–4 as GM, BU, and CH modes, but those meanings remain unverified on Sol-Ark firmware. Register 248 appears to contain the overall TOU enable and Monday-through-Sunday enable bits; it must remain read-only until each active bit has been correlated with the master display.

### Candidate generator and current settings

| Address | Reference meaning | Reference scaling/range | Status |
|---:|---|---|---|
| 210 | Maximum battery charging current | 1 A; 0–185 A | Candidate; range likely model-specific |
| 211 | Maximum battery discharge current | 1 A; 0–185 A | Candidate; range likely model-specific |
| 223 | Maximum generator runtime | 0.1 hour | Candidate |
| 224 | Generator cooling time | 0.1 hour | Candidate |
| 225 | Generator charging start voltage | 0.01 V | Candidate |
| 226 | Generator charging start SOC | 1% | Candidate |
| 227 | Generator charging current to battery | 1 A; 0–185 A | Candidate for Generator Charge Current |
| 230 | Utility charging current to battery | 1 A; 0–185 A | Candidate |
| 292 | Generator peak-shaving power | 1 W; 0–16000 W | Candidate |

The documented 8,000 W TOU-power ceiling and 185 A current ceilings must not be imposed on the Sol-Ark 15K without field confirmation. They appear to describe an older or smaller Deye platform and conflict with capabilities exposed by newer Sol-Ark firmware and parallel systems.

### Evidence classification

- **Confirmed:** addresses 250–255, decimal HHMM encoding, FC3 reads, FC16 quantity-one write at address 250, master display update, slave inheritance, persistence, and restoration.
- **Strong candidates:** addresses 256–279 and generator setting address 227 because the table structure aligns with the Sol-Ark interface.
- **Unverified:** Sol-Ark-specific ranges, registers 248 and 274–279 bit semantics, restart persistence for programmatic writes, and all remaining writable settings.

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

## Field validation and development implementation — 2026-09-20

Four additional master settings were isolated with before, after, and restored snapshots. The slave inherited each saved master-screen change. Every restoration comparison returned no changed registers in the common snapshot range.

| Control | Address/field | Observed transition | Result |
|---|---:|---:|---|
| TOU Power Point 1 | 256 | 12000 to 11900 | Confirmed, direct watts |
| TOU Capacity Point 1 | 268 | 50 to 49 | Confirmed, direct percent |
| TOU Charge Point 1 | 274 bit 0 | 1 to 0 | Confirmed packed flag |
| Global Generator Charge | 231 | 1 to 0 | Confirmed Boolean |

The Sol-Ark presents one charge enable for each TOU period; it does not present separate grid and generator switches per period. Register 274 bit 0 is therefore identified as **TOU Charge Point 1**, not Grid Charge Point 1. Register 274 bit 1 remains unknown and blocked. Generator charging is enabled globally through register 231.

Development preview `1.1.0b1` exposes these four controls only on the unit-ID-1 master entry. Numeric controls use Home Assistant box mode. Writes use FC16 quantity one, read-before-write comparison, immediate FC3 read-back, coordinator publication only after verification, and read-modify-write for the packed charge flag. No writable controls are created on inverter 2 or the x2 device.

### Six-period expansion — 2026-09-21

Point 2 screen-change testing confirmed register 257 as TOU Power Point 2 (`12000` to `11900`) and register 269 as TOU Capacity Point 2 (`50` to `49`). Both settings were restored with no changed registers remaining. Together with the already-confirmed Point 1 addresses and the documented contiguous table, development preview `1.1.0b2` expands the editor to:

- Time Points 1-6 at registers 250-255 using decimal HHMM;
- Power Points 1-6 at registers 256-261 using direct watts;
- Capacity Points 1-6 at registers 268-273 using direct percent;
- Charge Points 1-6 at registers 274-279 using bit 0 with read-modify-write;
- global Generator Charge at register 231.

Point 1 and Point 2 establish the sequential layout. Points 3-6 follow that layout but have not each received repetitive individual screen-change testing. Users should allow several seconds for a verified write to appear on the master and then propagate over the parallel communications link to the slave. Do not issue successive changes while the prior value is still propagating.

Development preview `1.1.0b3` replaces the Home Assistant time-domain controls with number-domain boxes because the time service produced errors in field use and added unwanted 12-hour formatting. Enter native 24-hour decimal HHMM values directly: `0` for 00:00, `400` for 04:00, `830` for 08:30, `1200` for 12:00, and `1630` for 16:30. Invalid hour/minute combinations are rejected before the Modbus write.
