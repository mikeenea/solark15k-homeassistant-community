"""Regression tests for register decoding and two-inverter aggregation."""

from __future__ import annotations

import unittest

from module_loader import load_integration_module

calculations = load_integration_module("calculations")


class RegisterDecodingTests(unittest.TestCase):
    """Validate field-confirmed Sol-Ark numeric encodings."""

    def test_signed_16_boundaries(self) -> None:
        self.assertEqual(calculations.signed_16(0x0000), 0)
        self.assertEqual(calculations.signed_16(0x7FFF), 32767)
        self.assertEqual(calculations.signed_16(0x8000), -32768)
        self.assertEqual(calculations.signed_16(0xFFFF), -1)

    def test_battery_power_and_current_sign_orientation(self) -> None:
        # Sol-Ark registers 190/191: positive is discharge, negative is charge.
        self.assertEqual(calculations.signed_16(0x07D0), 2000)
        self.assertEqual(calculations.signed_16(0xF830), -2000)
        self.assertAlmostEqual(calculations.signed_16(0xF830) * 0.01, -20.0)

    def test_unsigned_32_low_word_first(self) -> None:
        self.assertEqual(calculations.unsigned_32(0x5678, 0x1234), 0x12345678)
        self.assertEqual(calculations.unsigned_32(0xFFFF, 0x0001), 131071)


class X2AggregationTests(unittest.TestCase):
    """Validate sums, means, availability, and creation rules."""

    def test_sum(self) -> None:
        self.assertEqual(calculations.aggregate_x2([3201, 3134], "sum"), 6335)

    def test_arithmetic_mean(self) -> None:
        self.assertEqual(calculations.aggregate_x2([281.3, 293.3], "mean"), 287.3)

    def test_missing_source_never_returns_partial_total(self) -> None:
        self.assertIsNone(calculations.aggregate_x2([3201, None], "sum"))
        self.assertIsNone(calculations.aggregate_x2([3201], "sum"))

    def test_unknown_operation_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            calculations.aggregate_x2([1, 2], "maximum")

    def test_availability_requires_two_current_datasets(self) -> None:
        self.assertTrue(
            calculations.x2_sources_available([(True, {183: 5300}), (True, {183: 5310})])
        )
        self.assertFalse(
            calculations.x2_sources_available([(True, {183: 5300}), (False, {183: 5310})])
        )
        self.assertFalse(calculations.x2_sources_available([(True, {183: 5300})]))

    def test_x2_created_once_when_second_entry_registers(self) -> None:
        self.assertFalse(calculations.should_create_x2(1, False))
        self.assertTrue(calculations.should_create_x2(2, False))
        self.assertFalse(calculations.should_create_x2(2, True))
        self.assertFalse(calculations.should_create_x2(3, False))


if __name__ == "__main__":
    unittest.main()
