#!/usr/bin/env python3
"""Minimal read-only Modbus TCP test for one Sol-Ark holding register.

Uses only the Python standard library.

Example:
    py tools/solark_single_register_test.py 192.0.2.4 183

Default register is 183 (battery voltage). Unit/slave ID is fixed at 1.
No write functions are implemented.
"""

from __future__ import annotations

import argparse
import socket
import struct
import sys

UNIT_ID = 1
FUNCTION = 3


def read_exact(sock: socket.socket, count: int) -> bytes:
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data")
        data += chunk
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Read one Sol-Ark holding register over Modbus TCP")
    parser.add_argument("host", help="Waveshare IP address")
    parser.add_argument("address", nargs="?", type=int, default=183, help="Holding register address (default: 183)")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    transaction_id = 1
    quantity = 1
    pdu = struct.pack(">BHH", FUNCTION, args.address, quantity)
    request = struct.pack(">HHHB", transaction_id, 0, len(pdu) + 1, UNIT_ID) + pdu

    print(f"Connecting to {args.host}:{args.port}")
    print(f"Reading holding register {args.address}, slave {UNIT_ID}, FC3, quantity 1")
    print("TX Modbus TCP:", request.hex(" ").upper())

    try:
        with socket.create_connection((args.host, args.port), args.timeout) as sock:
            sock.settimeout(args.timeout)
            sock.sendall(request)
            mbap = read_exact(sock, 7)
            tid, protocol, length, unit = struct.unpack(">HHHB", mbap)
            body = read_exact(sock, length - 1)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 2

    response = mbap + body
    print("RX Modbus TCP:", response.hex(" ").upper())

    if tid != transaction_id or protocol != 0 or unit != UNIT_ID:
        print(f"FAILED: unexpected MBAP header tid={tid} protocol={protocol} unit={unit}", file=sys.stderr)
        return 3

    function = body[0]
    if function == (FUNCTION | 0x80):
        code = body[1] if len(body) > 1 else None
        print(f"FAILED: Modbus exception code {code}", file=sys.stderr)
        return 4
    if function != FUNCTION or len(body) < 4 or body[1] != 2:
        print(f"FAILED: unexpected response body {body.hex(' ').upper()}", file=sys.stderr)
        return 5

    value = struct.unpack(">H", body[2:4])[0]
    print(f"SUCCESS: register {args.address} raw value = {value} (0x{value:04X})")

    if args.address == 183:
        print(f"Decoded battery voltage = {value * 0.01:.2f} V")
    elif args.address in (150, 151, 152):
        print(f"Decoded voltage = {value * 0.1:.1f} V")
    elif args.address == 184:
        print(f"Decoded battery SOC = {value} %")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
