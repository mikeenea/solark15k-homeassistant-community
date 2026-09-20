"""Persistent Modbus TCP client for Sol-Ark telemetry and guarded settings."""

from __future__ import annotations

import asyncio
import struct

FC_READ_HOLDING = 3
FC_WRITE_MULTIPLE = 16


class SolArkModbusError(Exception):
    """Base exception for Sol-Ark Modbus communication errors."""


def build_read_holding_request(
    transaction_id: int, slave_id: int, start: int, count: int
) -> bytes:
    """Build one Modbus TCP FC3 request with the configured RTU unit ID."""
    if not 1 <= count <= 125:
        raise ValueError("Modbus FC3 register count must be 1..125")
    if not 1 <= slave_id <= 247:
        raise ValueError("Modbus unit ID must be 1..247")
    pdu = struct.pack(">BHH", FC_READ_HOLDING, start, count)
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, slave_id) + pdu


def parse_read_holding_response(
    mbap: bytes,
    body: bytes,
    expected_transaction_id: int,
    expected_slave_id: int,
    expected_count: int,
) -> list[int]:
    """Validate and decode one Modbus TCP FC3 response."""
    if len(mbap) != 7:
        raise SolArkModbusError(f"Unexpected MBAP length {len(mbap)}")
    rx_tid, protocol, length, unit = struct.unpack(">HHHB", mbap)
    if rx_tid != expected_transaction_id:
        raise SolArkModbusError(
            "Transaction ID mismatch: "
            f"sent {expected_transaction_id}, received {rx_tid}"
        )
    if protocol != 0:
        raise SolArkModbusError(f"Unexpected Modbus protocol ID {protocol}")
    if unit != expected_slave_id:
        raise SolArkModbusError(
            f"Unit ID mismatch: expected {expected_slave_id}, received {unit}"
        )
    if length != len(body) + 1:
        raise SolArkModbusError(
            f"Unexpected Modbus length: header={length}, actual={len(body) + 1}"
        )
    if not body:
        raise SolArkModbusError("Empty Modbus response")
    function = body[0]
    if function == (FC_READ_HOLDING | 0x80):
        code = body[1] if len(body) > 1 else None
        raise SolArkModbusError(f"Modbus exception response, code={code}")
    if function != FC_READ_HOLDING:
        raise SolArkModbusError(f"Unexpected function code {function}")
    if len(body) < 2:
        raise SolArkModbusError("Missing Modbus byte count")
    byte_count = body[1]
    payload = body[2:]
    if byte_count != expected_count * 2 or len(payload) != byte_count:
        raise SolArkModbusError(
            "Unexpected byte count: "
            f"expected {expected_count * 2}, header={byte_count}, "
            f"actual={len(payload)}"
        )
    return list(struct.unpack(">" + "H" * expected_count, payload))


def build_write_one_request(
    transaction_id: int, slave_id: int, address: int, value: int
) -> bytes:
    """Build an FC16 request containing exactly one holding register."""
    if not 1 <= slave_id <= 247:
        raise ValueError("Modbus unit ID must be 1..247")
    if not 0 <= address <= 0xFFFF:
        raise ValueError("Modbus register address must be 0..65535")
    if not 0 <= value <= 0xFFFF:
        raise ValueError("Modbus register value must be 0..65535")
    pdu = struct.pack(">BHHBH", FC_WRITE_MULTIPLE, address, 1, 2, value)
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, slave_id) + pdu


def parse_write_one_response(
    mbap: bytes,
    body: bytes,
    expected_transaction_id: int,
    expected_slave_id: int,
    expected_address: int,
) -> None:
    """Validate an FC16 quantity-one acknowledgement."""
    if len(mbap) != 7:
        raise SolArkModbusError(f"Unexpected MBAP length {len(mbap)}")
    rx_tid, protocol, length, unit = struct.unpack(">HHHB", mbap)
    if rx_tid != expected_transaction_id:
        raise SolArkModbusError(
            "Transaction ID mismatch: "
            f"sent {expected_transaction_id}, received {rx_tid}"
        )
    if protocol != 0:
        raise SolArkModbusError(f"Unexpected Modbus protocol ID {protocol}")
    if unit != expected_slave_id:
        raise SolArkModbusError(
            f"Unit ID mismatch: expected {expected_slave_id}, received {unit}"
        )
    if length != len(body) + 1:
        raise SolArkModbusError(
            f"Unexpected Modbus length: header={length}, actual={len(body) + 1}"
        )
    if not body:
        raise SolArkModbusError("Empty Modbus response")
    function = body[0]
    if function == (FC_WRITE_MULTIPLE | 0x80):
        code = body[1] if len(body) > 1 else None
        raise SolArkModbusError(f"Modbus exception response, code={code}")
    if function != FC_WRITE_MULTIPLE or len(body) != 5:
        raise SolArkModbusError("Unexpected FC16 response")
    address, count = struct.unpack(">HH", body[1:])
    if address != expected_address or count != 1:
        raise SolArkModbusError(
            "FC16 response did not confirm the requested address and count"
        )


class SolArkModbusClient:
    """Persistent Modbus TCP client for a TCP-to-RTU gateway.

    Normal telemetry uses FC3. Development-only settings use FC16 with exactly
    one register plus read-before-write and immediate read-back verification.
    """

    def __init__(
        self,
        host: str,
        port: int,
        slave_id: int,
        timeout: float,
    ) -> None:
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._transaction_id = 0
        self._lock = asyncio.Lock()

    async def async_connect(self) -> None:
        """Open the TCP connection if it is not already open."""
        if self._writer is not None and not self._writer.is_closing():
            return

        try:
            async with asyncio.timeout(self.timeout):
                self._reader, self._writer = await asyncio.open_connection(
                    self.host, self.port
                )
        except (TimeoutError, OSError) as err:
            await self.async_close()
            raise SolArkModbusError(
                f"Unable to connect to {self.host}:{self.port}: {err}"
            ) from err

    async def async_close(self) -> None:
        """Close the TCP connection."""
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is None:
            return

        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass

    async def async_read_holding(self, start: int, count: int) -> list[int]:
        """Read holding registers using Modbus function code 3."""
        if not 1 <= count <= 125:
            raise ValueError("Modbus FC3 register count must be 1..125")

        async with self._lock:
            try:
                await self.async_connect()
                assert self._reader is not None
                assert self._writer is not None

                self._transaction_id = (self._transaction_id + 1) & 0xFFFF
                request = build_read_holding_request(
                    self._transaction_id, self.slave_id, start, count
                )

                self._writer.write(request)
                await self._writer.drain()

                async with asyncio.timeout(self.timeout):
                    mbap = await self._reader.readexactly(7)
                    _, _, length, _ = struct.unpack(">HHHB", mbap)
                    body = await self._reader.readexactly(length - 1)
                return parse_read_holding_response(
                    mbap,
                    body,
                    self._transaction_id,
                    self.slave_id,
                    count,
                )

            except (TimeoutError, asyncio.IncompleteReadError, OSError) as err:
                await self.async_close()
                raise SolArkModbusError(str(err) or "Modbus request timed out") from err
            except SolArkModbusError:
                await self.async_close()
                raise

    async def _async_exchange(self, request: bytes) -> tuple[bytes, bytes]:
        """Send one request while the caller holds the client lock."""
        await self.async_connect()
        assert self._reader is not None
        assert self._writer is not None
        self._writer.write(request)
        await self._writer.drain()
        async with asyncio.timeout(self.timeout):
            mbap = await self._reader.readexactly(7)
            _, _, length, _ = struct.unpack(">HHHB", mbap)
            body = await self._reader.readexactly(length - 1)
        return mbap, body

    async def _async_read_one_locked(self, address: int) -> int:
        """Read one register while the caller holds the client lock."""
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        request = build_read_holding_request(
            self._transaction_id, self.slave_id, address, 1
        )
        mbap, body = await self._async_exchange(request)
        return parse_read_holding_response(
            mbap, body, self._transaction_id, self.slave_id, 1
        )[0]

    async def async_write_holding_one(
        self, address: int, value: int, *, expected: int
    ) -> int:
        """Guard, write, and verify one register using FC16 quantity one."""
        async with self._lock:
            try:
                current = await self._async_read_one_locked(address)
                if current != expected:
                    raise SolArkModbusError(
                        f"Register {address} changed before write: "
                        f"expected {expected}, read {current}"
                    )

                self._transaction_id = (self._transaction_id + 1) & 0xFFFF
                request = build_write_one_request(
                    self._transaction_id, self.slave_id, address, value
                )
                mbap, body = await self._async_exchange(request)
                parse_write_one_response(
                    mbap,
                    body,
                    self._transaction_id,
                    self.slave_id,
                    address,
                )

                actual = await self._async_read_one_locked(address)
                if actual != value:
                    raise SolArkModbusError(
                        f"Register {address} read-back failed: "
                        f"wrote {value}, read {actual}"
                    )
                return actual
            except (TimeoutError, asyncio.IncompleteReadError, OSError) as err:
                await self.async_close()
                raise SolArkModbusError(
                    str(err) or "Modbus request timed out"
                ) from err
            except SolArkModbusError:
                await self.async_close()
                raise
