"""Protocol-level tests for Modbus request/response handling."""

from __future__ import annotations

import struct
import unittest

from module_loader import load_integration_module

modbus = load_integration_module("modbus_client")


class ModbusProtocolTests(unittest.TestCase):
    """Protect transaction, unit-ID, function-code, and register decoding."""

    def test_requests_preserve_distinct_inverter_unit_ids(self) -> None:
        inverter_1 = modbus.build_read_holding_request(1, 1, 183, 1)
        inverter_2 = modbus.build_read_holding_request(1, 2, 183, 1)
        self.assertEqual(inverter_1, bytes.fromhex("000100000006010300b70001"))
        self.assertEqual(inverter_2, bytes.fromhex("000100000006020300b70001"))

    def test_valid_fc3_response_decodes_registers(self) -> None:
        body = bytes.fromhex("03041555002a")
        mbap = struct.pack(">HHHB", 7, 0, len(body) + 1, 2)
        self.assertEqual(
            modbus.parse_read_holding_response(mbap, body, 7, 2, 2),
            [0x1555, 0x002A],
        )

    def test_wrong_unit_id_is_rejected(self) -> None:
        body = bytes.fromhex("03021555")
        mbap = struct.pack(">HHHB", 7, 0, len(body) + 1, 1)
        with self.assertRaisesRegex(modbus.SolArkModbusError, "Unit ID mismatch"):
            modbus.parse_read_holding_response(mbap, body, 7, 2, 1)

    def test_exception_response_is_rejected(self) -> None:
        body = bytes.fromhex("8302")
        mbap = struct.pack(">HHHB", 7, 0, len(body) + 1, 2)
        with self.assertRaisesRegex(modbus.SolArkModbusError, "code=2"):
            modbus.parse_read_holding_response(mbap, body, 7, 2, 1)

    def test_fc16_quantity_one_request(self) -> None:
        request = modbus.build_write_one_request(9, 1, 256, 11900)
        self.assertEqual(
            request,
            bytes.fromhex("000900000009011001000001022e7c"),
        )

    def test_fc16_quantity_one_response(self) -> None:
        body = bytes.fromhex("1001000001")
        mbap = struct.pack(">HHHB", 9, 0, len(body) + 1, 1)
        self.assertIsNone(
            modbus.parse_write_one_response(mbap, body, 9, 1, 256)
        )

    def test_fc16_wrong_address_is_rejected(self) -> None:
        body = bytes.fromhex("1001010001")
        mbap = struct.pack(">HHHB", 9, 0, len(body) + 1, 1)
        with self.assertRaisesRegex(modbus.SolArkModbusError, "did not confirm"):
            modbus.parse_write_one_response(mbap, body, 9, 1, 256)


if __name__ == "__main__":
    unittest.main()
