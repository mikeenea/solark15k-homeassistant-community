"""Minimal persistent Modbus TCP client for Sol-Ark read-only telemetry."""

from __future__ import annotations

import asyncio
import struct

FC_READ_HOLDING = 3


class SolArkModbusError(Exception):
    """Base exception for Sol-Ark Modbus communication errors."""


class SolArkModbusClient:
    """Persistent Modbus TCP client for a TCP-to-RTU gateway.

    Only FC3 (Read Holding Registers) is implemented. There are deliberately no
    Modbus write methods in this commissioning integration.
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
                pdu = struct.pack(">BHH", FC_READ_HOLDING, start, count)
                request = (
                    struct.pack(
                        ">HHHB",
                        self._transaction_id,
                        0,
                        len(pdu) + 1,
                        self.slave_id,
                    )
                    + pdu
                )

                self._writer.write(request)
                await self._writer.drain()

                async with asyncio.timeout(self.timeout):
                    mbap = await self._reader.readexactly(7)
                    rx_tid, protocol, length, unit = struct.unpack(">HHHB", mbap)
                    body = await self._reader.readexactly(length - 1)

                if rx_tid != self._transaction_id:
                    raise SolArkModbusError(
                        "Transaction ID mismatch: "
                        f"sent {self._transaction_id}, received {rx_tid}"
                    )
                if protocol != 0:
                    raise SolArkModbusError(
                        f"Unexpected Modbus protocol ID {protocol}"
                    )
                if unit != self.slave_id:
                    raise SolArkModbusError(
                        f"Unit ID mismatch: expected {self.slave_id}, received {unit}"
                    )
                if not body:
                    raise SolArkModbusError("Empty Modbus response")

                function = body[0]
                if function == (FC_READ_HOLDING | 0x80):
                    code = body[1] if len(body) > 1 else None
                    raise SolArkModbusError(
                        f"Modbus exception response, code={code}"
                    )
                if function != FC_READ_HOLDING:
                    raise SolArkModbusError(
                        f"Unexpected function code {function}"
                    )

                byte_count = body[1]
                payload = body[2:]
                if byte_count != count * 2 or len(payload) != byte_count:
                    raise SolArkModbusError(
                        "Unexpected byte count: "
                        f"expected {count * 2}, header={byte_count}, "
                        f"actual={len(payload)}"
                    )

                return list(struct.unpack(">" + "H" * count, payload))

            except (TimeoutError, asyncio.IncompleteReadError, OSError) as err:
                await self.async_close()
                raise SolArkModbusError(str(err) or "Modbus request timed out") from err
            except SolArkModbusError:
                await self.async_close()
                raise
