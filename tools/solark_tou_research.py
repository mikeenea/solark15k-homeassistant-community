#!/usr/bin/env python3
"""Experimental Sol-Ark TOU register research utility.

This tool is intentionally separate from the Home Assistant integration.  It
does not contain a guessed TOU register map.  Use snapshots and offline diffs
to identify candidate registers before considering a single-register write.

WARNING: Modbus writes can change inverter behavior.  The public Sol-Ark V1.4
map used by this project documents reads, not configuration writes.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UNIT_ID = 1
FC_READ_HOLDING = 3
FC_WRITE_SINGLE = 6
FC_WRITE_MULTIPLE = 16
WRITE_ENV_NAME = "SOLARK_UNSAFE_WRITE_ACK"
WRITE_ENV_VALUE = "I_ACCEPT_THE_RISK"


def read_exact(sock: socket.socket, count: int) -> bytes:
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data")
        data += chunk
    return data


class ModbusTCP:
    """Small persistent Modbus TCP client for controlled research."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.transaction_id = 0
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        if self.sock is None:
            self.sock = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
            self.sock.settimeout(self.timeout)

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def request(self, pdu: bytes, expected_function: int) -> bytes:
        self.transaction_id = (self.transaction_id + 1) & 0xFFFF
        request = (
            struct.pack(">HHHB", self.transaction_id, 0, len(pdu) + 1, UNIT_ID)
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
            self.close()
            raise

        if rx_tid != self.transaction_id:
            self.close()
            raise RuntimeError(
                f"Transaction ID mismatch: sent {self.transaction_id}, received {rx_tid}"
            )
        if protocol != 0 or unit != UNIT_ID:
            raise RuntimeError("Unexpected Modbus response header")
        if not body:
            raise RuntimeError("Empty Modbus response")
        if body[0] == (expected_function | 0x80):
            code = body[1] if len(body) > 1 else None
            raise RuntimeError(f"Modbus exception response, code={code}")
        if body[0] != expected_function:
            raise RuntimeError(f"Unexpected function code {body[0]}")
        return body

    def read_holding(self, start: int, count: int) -> list[int]:
        if not 0 <= start <= 65535 or not 1 <= count <= 125:
            raise ValueError("Invalid FC3 register range")
        body = self.request(
            struct.pack(">BHH", FC_READ_HOLDING, start, count), FC_READ_HOLDING
        )
        byte_count = body[1]
        payload = body[2:]
        if byte_count != count * 2 or len(payload) != byte_count:
            raise RuntimeError("Unexpected FC3 byte count")
        return list(struct.unpack(">" + "H" * count, payload))

    def write_single(self, address: int, value: int) -> None:
        """Write exactly one holding register with FC6 and validate its echo."""
        if not 0 <= address <= 65535 or not 0 <= value <= 65535:
            raise ValueError("Address and value must be uint16")
        request = struct.pack(">BHH", FC_WRITE_SINGLE, address, value)
        body = self.request(request, FC_WRITE_SINGLE)
        if body != request:
            raise RuntimeError("FC6 response did not echo the requested write")

    def write_multiple_one(self, address: int, value: int) -> None:
        """Write one holding register with FC16 and validate address/count reply."""
        if not 0 <= address <= 65535 or not 0 <= value <= 65535:
            raise ValueError("Address and value must be uint16")
        pdu = struct.pack(">BHHBH", FC_WRITE_MULTIPLE, address, 1, 2, value)
        body = self.request(pdu, FC_WRITE_MULTIPLE)
        expected = struct.pack(">BHH", FC_WRITE_MULTIPLE, address, 1)
        if body != expected:
            raise RuntimeError("FC16 response did not confirm the requested address/count")


def read_range(
    client: ModbusTCP,
    start: int,
    end: int,
    chunk_size: int,
    delay: float,
    retries: int,
) -> dict[int, int]:
    result: dict[int, int] = {}
    address = start
    while address <= end:
        count = min(chunk_size, end - address + 1)
        last_error: Exception | None = None
        values: list[int] | None = None
        for attempt in range(retries + 1):
            try:
                values = client.read_holding(address, count)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                client.close()
                if attempt < retries:
                    print(
                        f"Retry {attempt + 1}/{retries}: registers "
                        f"{address}..{address + count - 1} failed: {exc}",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
        if last_error is not None or values is None:
            raise RuntimeError(
                f"registers {address}..{address + count - 1} failed after "
                f"{retries + 1} attempts: {last_error}"
            )
        result.update({address + index: value for index, value in enumerate(values)})
        address += count
        if address <= end and delay:
            time.sleep(delay)
    return result


def snapshot_document(
    host: str, port: int, start: int, end: int, registers: dict[int, int]
) -> dict[str, Any]:
    return {
        "format": "solark-tou-register-snapshot-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": {"host": host, "port": port, "unit_id": UNIT_ID},
        "range": {"start": start, "end": end},
        "registers": {str(key): value for key, value in sorted(registers.items())},
    }


def load_snapshot(path: Path) -> dict[int, int]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != "solark-tou-register-snapshot-v1":
        raise ValueError(f"{path} is not a supported snapshot")
    return {int(key): int(value) for key, value in document["registers"].items()}


def changed_registers(before: dict[int, int], after: dict[int, int]) -> list[tuple[int, int, int]]:
    return [
        (address, before[address], after[address])
        for address in sorted(before.keys() & after.keys())
        if before[address] != after[address]
    ]


def add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("host", help="MASTER inverter gateway IP address")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--timeout", type=float, default=5.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser("snapshot", help="Save a read-only register snapshot")
    add_connection_arguments(snapshot)
    snapshot.add_argument("--start", type=int, default=0)
    snapshot.add_argument("--end", type=int, default=255)
    snapshot.add_argument("--chunk-size", type=int, default=8)
    snapshot.add_argument("--delay", type=float, default=1.0)
    snapshot.add_argument("--retries", type=int, default=3)
    snapshot.add_argument("--output", type=Path, required=True)

    diff = commands.add_parser("diff", help="Compare two snapshots without an inverter connection")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)

    write = commands.add_parser(
        "write-single", help="EXPERIMENTAL: guarded FC6 write of one confirmed register"
    )
    add_connection_arguments(write)
    write.add_argument("--address", type=int, required=True)
    write.add_argument("--expected", type=int, required=True)
    write.add_argument("--value", type=int, required=True)
    write.add_argument(
        "--confirm",
        required=True,
        help="Must equal WRITE-MASTER-<address>-FROM-<expected>-TO-<value>",
    )

    write_fc16 = commands.add_parser(
        "write-one-fc16",
        help="EXPERIMENTAL: guarded FC16 write containing exactly one register",
    )
    add_connection_arguments(write_fc16)
    write_fc16.add_argument("--address", type=int, required=True)
    write_fc16.add_argument("--expected", type=int, required=True)
    write_fc16.add_argument("--value", type=int, required=True)
    write_fc16.add_argument(
        "--confirm",
        required=True,
        help="Must equal WRITE-FC16-MASTER-<address>-FROM-<expected>-TO-<value>",
    )
    return parser


def run_snapshot(args: argparse.Namespace) -> int:
    if not 0 <= args.start <= args.end <= 65535:
        raise ValueError("Snapshot range must satisfy 0 <= start <= end <= 65535")
    if not 1 <= args.chunk_size <= 125 or args.delay < 0 or args.retries < 0:
        raise ValueError(
            "chunk-size must be 1..125; delay and retries must be non-negative"
        )
    client = ModbusTCP(args.host, args.port, args.timeout)
    try:
        registers = read_range(
            client,
            args.start,
            args.end,
            args.chunk_size,
            args.delay,
            args.retries,
        )
    finally:
        client.close()
    document = snapshot_document(args.host, args.port, args.start, args.end, registers)
    args.output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(registers)} registers to {args.output}")
    return 0


def run_diff(args: argparse.Namespace) -> int:
    before = load_snapshot(args.before)
    after = load_snapshot(args.after)
    changes = changed_registers(before, after)
    if not changes:
        print("No changed registers in the common snapshot range.")
        return 0
    print("ADDRESS  BEFORE          AFTER           DELTA")
    for address, old, new in changes:
        print(f"{address:7d}  {old:5d} 0x{old:04X}  {new:5d} 0x{new:04X}  {new-old:+d}")
    return 0


def run_write(args: argparse.Namespace) -> int:
    phrase = f"WRITE-MASTER-{args.address}-FROM-{args.expected}-TO-{args.value}"
    if os.environ.get(WRITE_ENV_NAME) != WRITE_ENV_VALUE:
        raise RuntimeError(
            f"Write blocked. Set {WRITE_ENV_NAME}={WRITE_ENV_VALUE} for this process only."
        )
    if args.confirm != phrase:
        raise RuntimeError(f"Write blocked. --confirm must be exactly: {phrase}")
    if not all(0 <= value <= 65535 for value in (args.address, args.expected, args.value)):
        raise ValueError("Address, expected value, and new value must be uint16")
    if args.expected == args.value:
        raise ValueError("New value is identical to expected value")

    client = ModbusTCP(args.host, args.port, args.timeout)
    try:
        current = client.read_holding(args.address, 1)[0]
        if current != args.expected:
            raise RuntimeError(
                f"Write blocked: register {args.address} is {current}, not expected {args.expected}"
            )
        print(f"Verified register {args.address}: {current} (0x{current:04X})")
        client.write_single(args.address, args.value)
        actual = client.read_holding(args.address, 1)[0]
        if actual != args.value:
            raise RuntimeError(
                f"WRITE VERIFICATION FAILED: expected {args.value}, read back {actual}"
            )
        print(f"WRITE VERIFIED: register {args.address} = {actual} (0x{actual:04X})")
        print("Confirm the master and slave inverter screens immediately.")
    finally:
        client.close()
    return 0


def run_write_fc16(args: argparse.Namespace) -> int:
    phrase = f"WRITE-FC16-MASTER-{args.address}-FROM-{args.expected}-TO-{args.value}"
    if os.environ.get(WRITE_ENV_NAME) != WRITE_ENV_VALUE:
        raise RuntimeError(
            f"Write blocked. Set {WRITE_ENV_NAME}={WRITE_ENV_VALUE} for this process only."
        )
    if args.confirm != phrase:
        raise RuntimeError(f"Write blocked. --confirm must be exactly: {phrase}")
    if not all(0 <= value <= 65535 for value in (args.address, args.expected, args.value)):
        raise ValueError("Address, expected value, and new value must be uint16")
    if args.expected == args.value:
        raise ValueError("New value is identical to expected value")

    client = ModbusTCP(args.host, args.port, args.timeout)
    try:
        current = client.read_holding(args.address, 1)[0]
        if current != args.expected:
            raise RuntimeError(
                f"Write blocked: register {args.address} is {current}, not expected {args.expected}"
            )
        print(f"Verified register {args.address}: {current} (0x{current:04X})")
        client.write_multiple_one(args.address, args.value)
        actual = client.read_holding(args.address, 1)[0]
        if actual != args.value:
            raise RuntimeError(
                f"WRITE VERIFICATION FAILED: expected {args.value}, read back {actual}"
            )
        print(f"FC16 WRITE VERIFIED: register {args.address} = {actual} (0x{actual:04X})")
        print("Confirm the master and slave inverter screens immediately.")
    finally:
        client.close()
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "snapshot":
            return run_snapshot(args)
        if args.command == "diff":
            return run_diff(args)
        if args.command == "write-single":
            return run_write(args)
        if args.command == "write-one-fc16":
            return run_write_fc16(args)
        raise RuntimeError("Unknown command")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
