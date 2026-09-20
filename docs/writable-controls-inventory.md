# SolarAssistant Control Inventory and Sol-Ark Write-Candidate Matrix

> **Development-only safety notice:** This document records research candidates for the `dev/tou-modbus-research` branch. It does not make any setting writable in the stable integration. The released integration remains read-only.

## Purpose and evidence boundary

The user supplied screenshots of writable SolarAssistant entities exposed for a Sol-Ark 15K. The screenshots establish that these control concepts can be presented through Home Assistant, but they do **not** establish the underlying register addresses or authorize reuse of SolarAssistant code, MQTT topics, or implementation details.

Candidate addresses below come from the independently reviewed Deye Modbus RTU Protocol V117 table and our own Sol-Ark field testing. Applicability must be confirmed on the Sol-Ark 15K one field at a time.

For a parallel system:

- write only to the master inverter endpoint;
- never create duplicate slave configuration controls;
- verify that the slave inherits each master change through the parallel communications link;
- keep ordinary polling stopped during controlled write testing;
- require read-before-write, immediate read-back, master-screen confirmation, slave-screen confirmation, and restoration.

## Evidence classifications

| Classification | Meaning |
|---|---|
| Confirmed | Address, encoding, FC16 quantity-one write, read-back, master display, slave inheritance, persistence, and restoration have been observed on the test system |
| Strong candidate | Deye table location and SolarAssistant control concept align, but no Sol-Ark write has been validated |
| Candidate | A plausible Deye register exists, but the Sol-Ark label, range, or semantics may differ |
| Unresolved | No sufficiently reliable address mapping has been established |
| Blocked | Do not expose until dedicated safety testing is complete |

## Screenshot-to-register inventory

### TOU schedule controls

| SolarAssistant control | Candidate register(s) | Encoding | Status | Proposed Home Assistant control |
|---|---:|---|---|---|
| Time point 1-6 | 250-255 | Decimal HHMM | **Confirmed** | Six `time` entities |
| Power point 1 | 256 | 1 W | **Confirmed** at 12000 and 11900 W, including restoration | Box-mode `number` entity |
| Power points 2-6 | 257-261 | 1 W | Strong candidate; not yet field-confirmed | None until individually confirmed |
| Capacity point 1 | 268 | 1% SOC | **Confirmed** at 50% and 49%, including restoration | Box-mode `number` entity, 0-100% |
| Capacity points 2-6 | 269-273 | 1% SOC | Strong candidate; not yet field-confirmed | None until individually confirmed |
| Charge point 1 | 274 bit 0 | Packed Boolean flag | **Confirmed**, including bit-preserving interpretation and restoration | `switch` entity |
| Charge points 2-6 | 275-279 bit 0 | Packed Boolean flag | Strong candidate; not yet field-confirmed | None until individually confirmed |
| Register 274 bit 1 and equivalent bits | 274-279 bit 1 | Unknown | **Blocked**; Sol-Ark has one charge-point control and separate global source controls | None |
| Additional period mode bits | 274-279 bits 2-4 | GM/BU/CH labels are not sufficiently defined | Blocked | None until semantics are proven |
| Overall TOU/day enable | 248 | Packed enable/day bitfield | Candidate and high-impact | Disabled-by-default switches only after validation |

### Battery controls

| SolarAssistant control | Candidate register(s) | Encoding | Status | Proposed Home Assistant control |
|---|---:|---|---|---|
| Battery type: Lithium | 200 | 0=lead/four-stage, 1=lithium | Candidate; changing battery type is high-impact | Blocked `select` |
| Lithium protocol subtype | 325 | Vendor/protocol enumeration | Candidate; exact Sol-Ark values unknown | Blocked `select` |
| Equalization charge voltage | 201 | 0.01 V | Strong candidate | Bounded `number` after validation |
| Absorption charge voltage | 202 | 0.01 V | Strong candidate | Bounded `number` after validation |
| Float charge voltage | 203 | 0.01 V | Strong candidate | Bounded `number` after validation |
| Max charge current | 210; newer limit candidate 320 | 1 A | Candidate; screenshot shows 275 A, exceeding the older Deye 185 A table limit | Blocked until correct Sol-Ark register/range is proven |
| Max discharge current | 211; newer limit candidate 321 | 1 A | Candidate; screenshot shows 275 A, exceeding the older Deye 185 A table limit | Blocked until correct Sol-Ark register/range is proven |
| Stop/start/low battery SOC family | 217-219 | 1% | Candidate only; SolarAssistant labels do not map cleanly | Blocked pending screen-change correlation |
| Battery voltage stop/start/low family | 220-222 | 0.01 V | Candidate only | Blocked pending screen-change correlation |

### Generator and auxiliary-port controls

| SolarAssistant control | Candidate register(s) | Encoding | Status | Proposed Home Assistant control |
|---|---:|---|---|---|
| Force generator on | 234 | Boolean; depends on auxiliary-port mode | Candidate and operationally high-impact | Momentary action or guarded switch after validation |
| Auxiliary port | 235 | 0=generator input, 1=smart load, 2=microinverter input in Deye reference | Strong candidate; Sol-Ark enumeration must be confirmed | Guarded `select` |
| Generator charge enabled | 231 | Boolean | **Confirmed**, including slave inheritance and restoration | `switch` entity |
| Generator connected to grid input | 291 | Boolean | Strong candidate | Guarded `switch` |
| Generator peak shaving enabled | 280 bits 4-7 | Packed field | Strong candidate; must preserve unrelated bits | Guarded `switch` |
| Generator peak shaving power | 292 | 1 W | Strong candidate; Deye range 0-16000 W | Bounded `number` |
| Generator start voltage | 225 | 0.01 V | Strong candidate | Bounded `number` |
| Generator start capacity | 226 | 1% SOC | Strong candidate | Bounded `number` |
| Max generator charge current | 227 | 1 A | Strong candidate; Sol-Ark range must be confirmed | Bounded `number` |
| Generator stop voltage | Unresolved | - | Screenshot proves the concept, not its address | None until correlated |
| Generator stop capacity | Unresolved | - | Screenshot proves the concept, not its address | None until correlated |
| Generator maximum runtime | 223 | 0.1 hour | Candidate; not visible in supplied screenshots | Optional later `number` |
| Generator cooling time | 224 | 0.1 hour | Candidate; not visible in supplied screenshots | Optional later `number` |

### Grid, export, and auxiliary-PV controls

| SolarAssistant control | Candidate register(s) | Encoding | Status | Proposed Home Assistant control |
|---|---:|---|---|---|
| Grid charge enabled | 232 | Boolean | Strong candidate | Guarded `switch` |
| Max grid charge current | 230 | 1 A | Strong candidate; Sol-Ark range must be confirmed | Bounded `number` |
| Grid frequency high | 289 | 0.01 Hz | Strong candidate | Blocked protection-setting `number` |
| Grid frequency low | 290 | 0.01 Hz | Strong candidate | Blocked protection-setting `number` |
| Grid voltage high | 287 | 0.1 V | Strong candidate | Blocked protection-setting `number` |
| Grid voltage low | 288 | 0.1 V | Strong candidate | Blocked protection-setting `number` |
| Grid peak shaving enabled | 280 bits 8-11 | Packed field | Strong candidate; bit-preserving write required | Guarded `switch` |
| Grid peak shaving power | 293 | 1 W | Strong candidate; Deye range 0-16000 W | Bounded `number` |
| Grid trickle feed | 206 | Deye label: zero-export minimum acting power | Candidate | `number` only after correlation |
| Max sell power | 245 | 1 W total power | Strong candidate; older Deye table shows 8000 W ceiling | Bounded `number` after Sol-Ark range confirmation |
| Solar export when battery full | 247 | Enumeration/Boolean | Strong candidate | Guarded `switch` |
| Auxiliary PV export cutoff | 280 bits 0-3 | Packed field | Candidate | Guarded `switch` after validation |
| Auxiliary load output on grid always on | 280 bit 12 | Packed Boolean flag | Strong candidate | Guarded `switch` after validation |
| Max solar power | Unresolved | - | Screenshot shows 18000 W; no reliable Deye mapping identified | None until correlated |
| Output percentage/limit | Unresolved | - | Screenshot label is truncated and does not match register 295 safely | None until identified |
| Remote switch | Unresolved | - | No reliable address mapping identified | Blocked |

### Operating-pattern controls

| SolarAssistant control | Candidate register(s) | Encoding | Status | Proposed Home Assistant control |
|---|---:|---|---|---|
| Energy pattern: Battery first / Load first | 243 | 0=battery priority, 1=load priority in Deye reference | Strong candidate | Guarded `select` |
| Limit/export control mode | 244 | Enumeration | Candidate; semantics vary by platform | Blocked `select` |
| Grid standard, type, and nominal frequency | 284-286 | Enumerations | Candidate but safety/regulatory critical | Permanently blocked from initial implementation |

## Recommended implementation phases

### Phase W1 - confirmed schedule foundation

Implement development-only, master-only controls only for fields confirmed through field testing. Each write must:

1. verify the expected current value;
2. validate HHMM input;
3. use FC16;
4. perform immediate FC3 read-back;
5. refresh all six time registers;
6. report that the slave must be visually confirmed;
7. provide an explicit restore operation.

### Phase W2 - TOU power and SOC

Point 1 at registers 256 and 268 is confirmed and exposed. Confirm points 2-6 independently before exposing the remaining inputs.

### Phase W3 - packed charge flags

Register 274 bit 0 is confirmed as the single TOU Charge Point 1 control. Writes must use read-modify-write and preserve every unrelated bit. Do not represent bit 1 as a generator-charge point; global generator charging is independently controlled by register 231.

### Phase W4 - generator controls

Validate registers 225-227, 231, 234, 235, 291, and 292. Resolve generator stop voltage and stop SOC independently rather than guessing that they use adjacent Deye registers.

### Phase W5 - battery and export limits

Validate charging voltages, current limits, energy pattern, sell/export settings, and register 280 packed flags. Current limits require special attention because the SolarAssistant screenshot values exceed the older Deye document's published ceiling.

### Phase W6 - protection settings

Grid voltage/frequency thresholds, battery type/protocol, grid standard, and remote operation remain blocked until all lower-risk groups are complete. These controls should require an explicit advanced-mode acknowledgement if they are ever implemented.

## Proposed Home Assistant architecture

Writable controls should not be added to the released read-only coordinator directly. The development design should use a separate, opt-in configuration platform:

- one configuration device bound to the **master** entry;
- no configuration entities on the slave entry or x2 device;
- `time`, `number`, `switch`, and `select` entities for validated fields;
- a single explicit **Apply schedule** action rather than continuous writes;
- a **Refresh from inverter** action;
- optimistic state disabled;
- write serialization with normal polling paused during the transaction;
- expected-value checks and complete read-back;
- event/audit logging without credentials or public endpoint details;
- safe failure that leaves the released monitoring path operational.

## Immediate next validation sequence

1. Record master firmware versions and all displayed TOU values.
2. Stop ordinary polling of the master endpoint.
3. Take a fresh snapshot through at least register 330.
4. Change only TOU period 1 power by the smallest permitted increment.
5. Take after/restored snapshots and confirm register 256.
6. Repeat for capacity point 1 to confirm register 268.
7. Toggle only grid-charge point 1 and determine the exact bit change at register 274.
8. Toggle only generator-charge point 1 and determine the exact bit change at register 274.
9. Confirm slave inheritance after every master-screen change.
10. Restore every setting before moving to the next field.

Do not test battery type, current limits, grid protection, forced generator operation, or auxiliary-port mode during this first sequence.
