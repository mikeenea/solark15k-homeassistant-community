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

Stop other Modbus polling temporarily so the research session is the only client using the selected gateway channel. From the repository root:

```powershell
py .\tools\solark_tou_research.py snapshot 192.0.2.241 `
  --start 0 --end 255 --chunk-size 8 --delay 1 `
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
  --start 0 --end 255 --chunk-size 8 --delay 1 `
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
