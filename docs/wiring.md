# Wiring Guide

## Scope

This guide covers the reference installation where each Sol-Ark 15K already has a CAN/RS485 splitter connected to the inverter's **Battery CAN Bus** port and the battery uses CAN communications.

The objective is to remove the failed SolarAssistant USB/RS485 interface while leaving the battery CAN path undisturbed.

## Sol-Ark 15K communication context

The public Sol-Ark V1.4 protocol describes the 15K Battery CAN Bus RJ45 as a combined connector carrying CAN and RS485 signals. The document also states that CAN-based battery communications may coexist with this read protocol when the inverter is configured appropriately.

For this project, the preferred path is the **RS485 output of the already-proven splitter**, not a new connection to a different inverter port.

## Existing arrangement

```text
Sol-Ark 15K Battery/CAN port
          |
          v
       Splitter
       /      \
      /        \
Battery CAN   RS485 monitoring
    |               |
 Battery       USB/RS485 cable
                     |
              SolarAssistant
```

## New arrangement

```text
Sol-Ark 15K Battery/CAN port
          |
          v
       Splitter
       /      \
      /        \
Battery CAN   RS485 monitoring
    |               |
 Battery       passive RJ45 lead
                     |
                     v
                Waveshare
                     |
                     v
                  Ethernet
                     |
                     v
              Home Assistant
```

## Splitter RS485 jack pinout

For the SolarAssistant-style Sol-Ark 15K splitter used by this project, the RS485 female RJ45 output is treated as:

| RJ45 pin | Signal | Nominal gateway connection |
|---:|---|---|
| 1 | RS485 B | B- |
| 2 | RS485 A | A+ |
| 3 | GND | signal ground |

This is the **splitter-output pinout** used by the existing monitoring cable path. Do not confuse it with the raw pin table for the inverter's combined Battery CAN Bus connector.

### Source credit

The practical 15K "2 in 1 BMS port" arrangement and the pin-1/pin-2/pin-3 RS485 mapping used as a reference here are publicly documented by **SolarAssistant**. Their documentation also explains simultaneous battery CAN plus inverter RS485 monitoring through the combined BMS port and the use of a splitter.

Source:

- SolarAssistant — Sol-Ark 15K-2P, "2 in 1 BMS port": https://solar-assistant.io/help/inverters/sol-ark/15K-2P/2-in-1-bms-port

This project combines that published practical wiring information with the Sol-Ark Modbus protocol documentation and installation-specific continuity/field checks. See `../THIRD_PARTY_NOTICES.md` for the repository attribution policy.

## Passive cable construction

Use a normal straight-through Cat5e/Cat6 patch cable:

1. Plug the RJ45 male end into the splitter's RS485 female jack.
2. Cut the other end off.
3. Strip the jacket carefully.
4. Identify conductors by continuity to RJ45 pins 1, 2, and 3.
5. Terminate those conductors at the Waveshare.

For a standard T568B patch cord, the usual colors are:

| RJ45 pin | Typical T568B conductor |
|---:|---|
| 1 | White/Orange |
| 2 | Orange |
| 3 | White/Green |

**Always verify with a multimeter.** Do not rely solely on color.

## Permanent dual-channel reference wiring

The permanent **Waveshare 2-CH RS485 TO POE ETH (B)** should initially be wired label-to-label and validated independently:

```text
Sol-Ark #1 splitter                Waveshare CH1
RS485 female RJ45

Pin 1  B  -----------------------> B-
Pin 2  A  -----------------------> A+
Pin 3  GND ----------------------> GND
```

```text
Sol-Ark #2 splitter                Waveshare CH2
RS485 female RJ45

Pin 1  B  -----------------------> B-
Pin 2  A  -----------------------> A+
Pin 3  GND ----------------------> GND
```

Do not assume the temporary single-channel gateway's field-verified polarity behavior will be identical on the permanent two-channel device.

## Temporary single-channel test wiring — field verified

For the **Waveshare RS232/485/422 TO POE ETH (B)** used during commissioning, label-to-label wiring timed out. Swapping only the two data conductors produced a valid Modbus response on 2026-09-10.

Field-verified working connection:

```text
Sol-Ark splitter                    Waveshare RS232/485/422 TO POE ETH (B)

Pin 1  RS485 B  -----------------> TA
Pin 2  RS485 A  -----------------> TB
Pin 3  GND      -----------------> PE  (signal ground)
```

With that connection, a single-register FC3 read of register 183 returned raw `5629` (`0x15FD`), decoding to 56.29 V battery voltage.

This is a **device-specific field result**, not a redefinition of the splitter pinout. RS485 A/B labeling varies across manufacturers and implementations.

## Ground is required

Do not omit the signal ground. The public Sol-Ark V1.4 protocol explicitly states that ground must be connected between inverter and master because communication may otherwise be disrupted by external noise.

This signal-reference conductor is part of the communications link. Follow the Waveshare documentation for its terminal naming and isolation arrangement.

## Termination

The Sol-Ark V1.4 document states that:

- the inverter already has internal termination;
- a 120-ohm termination resistor should be used at the master side.

Before adding a resistor:

1. determine whether the Waveshare channel has built-in/selectable 120-ohm termination;
2. avoid adding an additional resistor if the channel is already terminated;
3. power equipment off before making resistance measurements.

## Continuity-test procedure

Before connecting the Waveshare:

1. Unplug both ends of the passive patch lead.
2. Set the meter to continuity mode.
3. Identify RJ45 pin 1 at the plug.
4. Find the corresponding cut conductor and label it `B`.
5. Repeat for pin 2 and label it `A`.
6. Repeat for pin 3 and label it `GND`.
7. Confirm there is no continuity between A and B.
8. Confirm there is no continuity between A and GND.
9. Confirm there is no continuity between B and GND.

## First power-up wiring rule

Connect only **one inverter/channel** during initial commissioning.

Recommended order:

```text
1. Sol-Ark #1 splitter CAN -> battery stays connected
2. Sol-Ark #1 splitter RS485 -> test gateway / Waveshare CH1
3. Second inverter left disconnected from monitoring
4. Configure and validate Sol-Ark #1
5. Only after #1 passes, validate Sol-Ark #2 independently
```

## A/B polarity troubleshooting

RS485 A/B labeling is not perfectly consistent across manufacturers. If TCP connectivity works but Modbus requests time out:

1. verify 9600/8/N/1 and the Modbus TCP-to-RTU gateway mode;
2. verify the signal-ground conductor;
3. continuity-check all three conductors;
4. try swapping only A and B while leaving signal ground unchanged;
5. record the working polarity for the exact gateway model/revision.

The project's temporary single-channel Waveshare required this A/B swap during field commissioning. Do not automatically carry that mapping over to different gateway hardware.

## Do not connect

Do not connect:

- the USB plug from the former SolarAssistant cable to the Waveshare;
- CAN-H or CAN-L to the Waveshare RS485 terminals;
- protective earth in place of the required RS485 signal reference unless the equipment documentation explicitly calls for that arrangement;
- the two inverter RS485 links together during the reference commissioning process.

## Recordkeeping

Record the gateway model and the **tested** polarity rather than relying only on A/B names. For the temporary field-test gateway, the working result was:

```text
Splitter pin 1 / B -> TA
Splitter pin 2 / A -> TB
Splitter pin 3 / GND -> PE
```

For the permanent dual-channel gateway, record each channel after independent validation.

Also record whether the Waveshare internal termination was enabled or an external resistor was installed.
