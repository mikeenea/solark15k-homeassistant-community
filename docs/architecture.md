# System Architecture

## Objective

The project provides local monitoring of one or more Sol-Ark 15K hybrid inverters from Home Assistant without requiring SolarAssistant, a Sol-Ark cloud service, or an inverter Wi-Fi dongle in the data path.

The design converts the inverter's RS485 Modbus RTU interface to standard Ethernet-accessible Modbus TCP using a dedicated Waveshare gateway. Home Assistant then reads the inverter through its native Modbus integration.

The project is intentionally **read-only** during initial development and field validation.

## Reference two-inverter architecture

```text
                        Ethernet / PoE LAN
                               |
                               v
                    +-----------------------+
                    | Isolated gateway      |
                    | endpoints 1 and 2     |
                    +-----------+-----------+
                                |
                 +--------------+--------------+
                 |                             |
          RS485 Channel 1               RS485 Channel 2
                 |                             |
                 v                             v
        Sol-Ark 15K #1                Sol-Ark 15K #2
        Battery/CAN splitter          Battery/CAN splitter
                 |                             |
          +------+-----+                +------+-----+
          |            |                |            |
        RS485          CAN             RS485          CAN
          |            |                |            |
       gateway      battery          gateway       battery
                      BMS                            BMS
```

Each inverter gets its own isolated RS485 channel. This avoids placing two inverters on a shared serial bus and allows each Sol-Ark endpoint and unit ID to be validated independently.

## Data flow

```text
Sol-Ark registers
      |
      | Modbus RTU / RS485
      v
Waveshare gateway
      |
      | Modbus TCP / Ethernet
      v
Home Assistant native Modbus
      |
      +--> live entities
      +--> templates / derived sensors
      +--> Recorder / long-term statistics
      +--> InfluxDB
              |
              +--> Grafana
              +--> long-term queries
              +--> selected historical sensors back into HA
```

## Design principles

### 1. Read-only first

The Sol-Ark public V1.4 document describes read operations for this map. This repository therefore does not expose register-write controls during the initial implementation.

### 2. One serial channel per inverter

A two-channel gateway or two single-channel gateways are preferred to a multidrop RS485 bus. Benefits include:

- independent troubleshooting;
- no shared-bus collisions between inverter interfaces;
- simpler addressing;
- easier packet capture and validation;
- lower risk that one inverter or cable fault degrades the other channel.

### 3. Validate before aggregating

Parallel inverters may expose a mix of per-inverter and system-level values. The design does not assume that load, grid, battery, or energy counters should simply be added together.

The validation process is:

1. display inverter #1 value;
2. display inverter #2 value;
3. compare both to the system display and external measurements;
4. determine whether the value is per-inverter, duplicated, master-only, or system-wide;
5. only then create a combined template sensor.

### 4. Separate operational history from long-term analytics

Home Assistant Recorder remains the operational database. InfluxDB is used as the high-resolution historian.

The historian host is intentionally platform-neutral. InfluxDB may run on a dedicated server, VM, Docker host, supported NAS, Home Assistant host, or another private system with persistent storage. The data model and dashboards do not depend on the host vendor.

Recommended roles:

| Layer | Role |
|---|---|
| Home Assistant Recorder | Recent entity history and normal HA behavior |
| HA long-term statistics | Native hourly/daily/monthly statistics and Energy Dashboard |
| InfluxDB | High-resolution telemetry and multi-year historical retention |
| Grafana | Advanced visualization and comparative analysis |

### 5. Preserve raw values when useful

During development, unusual or firmware-sensitive values should be retained in raw form in addition to the interpreted entity. Candidates include:

- battery temperature raw value;
- battery power raw signed value;
- battery current raw signed value;
- fault words 103-106;
- relay status words;
- unusual 32-bit counters.

Keeping raw values makes future reinterpretation possible if firmware behavior differs from the public map.

## Addressing model

The public V1.4 protocol documents unit ID `0x01`, but field testing demonstrated that parallel addressing can affect the Modbus unit ID. The validated pair used:

```text
Waveshare endpoint 1 -> Sol-Ark #1 -> unit ID 1
Waveshare endpoint 2 -> Sol-Ark #2 -> unit ID 2
```

The integration therefore stores both the TCP endpoint and unit ID per inverter. Register 183 should be tested on each endpoint before Home Assistant polling is enabled.

## Suggested network plan

Example only:

```text
Gateway endpoint 1: XXX.XXX.XXX.XXX:502
Gateway endpoint 2: XXX.XXX.XXX.XXX:502
Home Assistant: existing HA address
```

Use static addresses or DHCP reservations. Keep the gateway reachable only from trusted management/automation networks where practical.

## Polling model

Recommended starting point:

- real-time power/voltage/current: 10 seconds;
- temperature and status: 10-30 seconds;
- daily/lifetime energy counters: 60 seconds;
- fault words: 10 seconds.

Once stability is proven, polling can be optimized. Avoid unnecessary high-rate polling of dozens of unchanged configuration values.

## Future architecture extensions

Planned or potential additions include:

- dual-inverter production package;
- fault-bit decoding into named binary sensors;
- InfluxDB retention/downsampling automation;
- Grafana dashboard JSON;
- outage-event analysis;
- per-MPPT performance comparison;
- battery throughput and equivalent-cycle estimates;
- generator runtime and energy analysis;
- firmware/register compatibility matrix.
