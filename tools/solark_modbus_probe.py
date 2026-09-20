#!/usr/bin/env python3
"""Read-only Sol-Ark 15K Modbus TCP commissioning probe.

No third-party modules are required.

Usage:
    python solark_modbus_probe.py XXX.XXX.XXX.XXX
    python solark_modbus_probe.py XXX.XXX.XXX.XXX --port 502 --unit-id 2 --dump
    python solark_modbus_probe.py XXX.XXX.XXX.XXX --chunk-size 8 --retries 2 --delay 10

Protocol basis: public Sol-Ark Modbus RTU Protocol V1.4
- Gateway transport: Modbus TCP -> Modbus RTU
- Unit/slave ID: configurable; default 1
- Function: 3 (Read Holding Registers)

This utility contains no Modbus write functions.

Commissioning note:
The field link may occasionally miss a response. The useful ranges are read in
small chunks and each chunk is retried before the probe aborts. The probe keeps
one TCP session open across normal requests because serial gateways often behave
more reliably with a persistent Modbus-TCP master connection. If a request
fails, the socket is discarded and the retry establishes a fresh connection.
Use a conservative inter-request delay while commissioning; 7-20 seconds has
been reported in field use for similar Sol-Ark polling arrangements.
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys
import time

DEFAULT_UNIT_ID = 1
FC_READ_HOLDING = 3


def read_exact(sock: socket.socket, count: int) -> bytes:
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data")
        data += chunk
    return data


class ModbusTCP:
    def __init__(
        self,
        host: str,
        port: int = 502,
        timeout: float = 5.0,
        unit_id: int = DEFAULT_UNIT_ID,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.unit_id = unit_id
        self.transaction_id = 0
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        if self.sock is None:
            sock = socket.create_connection((self.host, self.port), self.timeout)
            sock.settimeout(self.timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.sock = sock

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def read_holding(self, start: int, count: int) -> list[int]:
        if not 1 <= count <= 125:
            raise ValueError("Modbus FC3 register count must be 1..125")

        self.transaction_id = (self.transaction_id + 1) & 0xFFFF
        pdu = struct.pack(">BHH", FC_READ_HOLDING, start, count)
        request = (
            struct.pack(">HHHB", self.transaction_id, 0, len(pdu) + 1, self.unit_id)
            + pdu
        )

        try:
            self.connect()
            assert self.sock is not None
            self.sock.sendall(request)
            mbap = read_exact(self.sock, 7)
            rx_tid, protocol, length, unit = struct.unpack(">HHHB", mbap)
            body = read_exact(self.sock, length - 1)
        except Exception:
            # A timeout or broken gateway session can leave a TCP stream unusable.
            # Force the next retry to establish a clean connection.
            self.close()
            raise

        if rx_tid != self.transaction_id:
            self.close()
            raise RuntimeError(
                f"Transaction ID mismatch: sent {self.transaction_id}, received {rx_tid}"
            )
        if protocol != 0:
            self.close()
            raise RuntimeError(f"Unexpected Modbus protocol ID {protocol}")
        if unit != self.unit_id:
            self.close()
            raise RuntimeError(f"Unit ID mismatch: expected {self.unit_id}, received {unit}")
        if not body:
            self.close()
            raise RuntimeError("Empty Modbus response")

        function = body[0]
        if function == (FC_READ_HOLDING | 0x80):
            code = body[1] if len(body) > 1 else None
            raise RuntimeError(f"Modbus exception response, code={code}")
        if function != FC_READ_HOLDING:
            self.close()
            raise RuntimeError(f"Unexpected function code {function}")

        byte_count = body[1]
        payload = body[2:]
        if byte_count != count * 2 or len(payload) != byte_count:
            self.close()
            raise RuntimeError(
                "Unexpected byte count: "
                f"expected {count * 2}, header={byte_count}, actual={len(payload)}"
            )

        return list(struct.unpack(">" + "H" * count, payload))


def read_range(
    modbus: ModbusTCP,
    start: int,
    end: int,
    chunk_size: int,
    retries: int,
    delay: float,
) -> dict[int, int]:
    """Read an inclusive register range in small chunks with retries."""
    registers: dict[int, int] = {}
    address = start

    while address <= end:
        count = min(chunk_size, end - address + 1)
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                values = modbus.read_holding(address, count)
                registers.update(
                    {address + i: value for i, value in enumerate(values)}
                )
                if attempt:
                    print(
                        f"Recovered: registers {address}..{address + count - 1} "
                        f"succeeded on attempt {attempt + 1}."
                    )
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    print(
                        f"Retry {attempt + 1}/{retries}: registers "
                        f"{address}..{address + count - 1} failed: {exc}",
                        file=sys.stderr,
                    )
                    time.sleep(delay)

        if last_error is not None:
            raise RuntimeError(
                f"registers {address}..{address + count - 1} failed after "
                f"{retries + 1} attempts: {last_error}"
            )

        address += count
        if address <= end:
            time.sleep(delay)

    return registers


def s16(value: int) -> int:
    """Interpret a Modbus uint16 word as signed int16."""
    return value - 65536 if value & 0x8000 else value


def u32_low_high(low: int, high: int) -> int:
    """Combine Sol-Ark low-word/high-word ordering into an unsigned integer."""
    return (high << 16) | low


def fmt(value: float | int, unit: str = "", decimals: int | None = None) -> str:
    text = str(value) if decimals is None else f"{value:.{decimals}f}"
    return f"{text} {unit}".strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Sol-Ark 15K Modbus TCP probe"
    )
    parser.add_argument("host", help="Waveshare channel IP address")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--unit-id",
        type=int,
        default=DEFAULT_UNIT_ID,
        help="Modbus unit/slave ID, 1..247 (default: 1)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=8,
        help="Registers per FC3 request (default: 8)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retries after a failed chunk (default: 2)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=10.0,
        help="Delay between Modbus requests in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--dump", action="store_true", help="Print all raw registers read"
    )
    args = parser.parse_args()

    if not 1 <= args.unit_id <= 247:
        parser.error("--unit-id must be 1..247")
    if not 1 <= args.chunk_size <= 125:
        parser.error("--chunk-size must be 1..125")
    if args.retries < 0:
        parser.error("--retries must be 0 or greater")
    if args.delay < 0:
        parser.error("--delay must be 0 or greater")

    modbus = ModbusTCP(args.host, args.port, args.timeout, args.unit_id)

    print(
        f"Connecting to {args.host}:{args.port}, unit/slave {args.unit_id}, FC3; "
        f"chunk={args.chunk_size}, retries={args.retries}, delay={args.delay:.2f}s; "
        "persistent TCP session..."
    )
    try:
        registers: dict[int, int] = {}
        registers.update(
            read_range(modbus, 60, 114, args.chunk_size, args.retries, args.delay)
        )
        time.sleep(args.delay)
        registers.update(
            read_range(modbus, 150, 196, args.chunk_size, args.retries, args.delay)
        )
    except Exception as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        print(
            "\nThe Ethernet endpoint may still be reachable even when an RTU reply "
            "is missed. Check RS485 termination/timing, Waveshare gateway mode, "
            f"9600/8/N/1, field-validated A/B/GND polarity, and slave ID {args.unit_id}."
        )
        return 2
    finally:
        modbus.close()

    def r(address: int) -> int:
        return registers.get(address, 0)

    metrics = [
        ("Grid frequency", r(79) * 0.01, "Hz", 2),
        ("Daily PV energy", r(108) * 0.1, "kWh", 1),
        ("PV1 voltage", r(109) * 0.1, "V", 1),
        ("PV1 current", r(110) * 0.1, "A", 1),
        ("PV2 voltage", r(111) * 0.1, "V", 1),
        ("PV2 current", r(112) * 0.1, "A", 1),
        ("PV3 voltage", r(113) * 0.1, "V", 1),
        ("PV3 current", r(114) * 0.1, "A", 1),
        ("Grid L1-N voltage", r(150) * 0.1, "V", 1),
        ("Grid L2-N voltage", r(151) * 0.1, "V", 1),
        ("Grid L1-L2 voltage", r(152) * 0.1, "V", 1),
        ("Inverter L1-N voltage", r(154) * 0.1, "V", 1),
        ("Inverter L2-N voltage", r(155) * 0.1, "V", 1),
        ("Load L1 voltage", r(157) * 0.1, "V", 1),
        ("Load L2 voltage", r(158) * 0.1, "V", 1),
        ("Grid total power", s16(r(169)), "W", 0),
        ("Inverter total power", s16(r(175)), "W", 0),
        ("Load total power", s16(r(178)), "W", 0),
        ("Generator port voltage", r(181) * 0.1, "V", 1),
        ("Battery temperature", r(182) * 0.1 - 100.0, "°C", 1),
        ("Battery voltage", r(183) * 0.01, "V", 2),
        ("Battery SOC", r(184), "%", 0),
        ("PV1 power", r(186), "W", 0),
        ("PV2 power", r(187), "W", 0),
        ("PV3 power", r(188), "W", 0),
        ("PV total calculated", r(186) + r(187) + r(188), "W", 0),
        ("Battery power (signed)", s16(r(190)), "W", 0),
        ("Battery current (signed)", s16(r(191)) * 0.01, "A", 2),
        ("Load frequency", r(192) * 0.01, "Hz", 2),
        ("Inverter frequency", r(193) * 0.01, "Hz", 2),
        ("Grid relay raw", r(194), "", 0),
        ("Generator relay raw", r(195), "", 0),
        ("Generator relay low nibble", r(195) & 0x000F, "", 0),
        ("Generator frequency", r(196) * 0.01, "Hz", 2),
        ("Heat-sink temperature", r(91) * 0.1 - 100.0, "°C", 1),
    ]

    print("\nREAD SUCCESSFUL\n")
    width = max(len(item[0]) for item in metrics)
    for name, value, unit, decimals in metrics:
        print(f"{name:<{width}} : {fmt(value, unit, decimals)}")

    fault_words = [r(103), r(104), r(105), r(106)]
    print("\nFault words 103..106 : " + " ".join(f"0x{x:04X}" for x in fault_words))
    if any(fault_words):
        print("WARNING: one or more fault bits are set.")
    else:
        print("No fault bits reported in registers 103..106.")

    total_batt_charge = u32_low_high(r(72), r(73)) * 0.1
    total_batt_discharge = u32_low_high(r(74), r(75)) * 0.1
    total_grid_buy = u32_low_high(r(78), r(80)) * 0.1
    total_grid_sell = u32_low_high(r(81), r(82)) * 0.1
    total_load = u32_low_high(r(85), r(86)) * 0.1
    total_pv = u32_low_high(r(96), r(97)) * 0.1

    print("\nENERGY COUNTERS")
    print(f"Total battery charge    : {total_batt_charge:.1f} kWh")
    print(f"Total battery discharge : {total_batt_discharge:.1f} kWh")
    print(f"Total grid import       : {total_grid_buy:.1f} kWh")
    print(f"Total grid export       : {total_grid_sell:.1f} kWh")
    print(f"Total load              : {total_load:.1f} kWh")
    print(f"Total PV                : {total_pv:.1f} kWh")

    if args.dump:
        print("\nRAW REGISTER DUMP")
        for address in sorted(registers):
            value = registers[address]
            print(f"{address:3d}: {value:5d}  0x{value:04X}")

    print("\nCompare these values to the Sol-Ark display before enabling long-term polling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
