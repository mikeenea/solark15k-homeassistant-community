"""Dependency-free register decoding and x2 aggregation helpers."""

from __future__ import annotations

from collections.abc import Iterable


def signed_16(raw: int) -> int:
    """Decode one unsigned Modbus register as a signed 16-bit integer."""
    raw &= 0xFFFF
    return raw - 0x10000 if raw & 0x8000 else raw


def unsigned_32(low_word: int, high_word: int) -> int:
    """Decode the Sol-Ark low-word/high-word 32-bit counter ordering."""
    return ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)


def aggregate_x2(
    values: Iterable[int | float | None], operation: str
) -> int | float | None:
    """Return a complete two-source sum or arithmetic mean.

    A combined value is deliberately unavailable if either inverter is
    missing. This prevents a partial system total from looking valid.
    """
    materialized = list(values)
    if len(materialized) != 2 or any(value is None for value in materialized):
        return None
    numeric = [float(value) for value in materialized if value is not None]
    result = sum(numeric)
    if operation == "mean":
        result /= 2
    elif operation != "sum":
        raise ValueError(f"Unsupported x2 operation: {operation}")
    if all(value.is_integer() for value in numeric) and result.is_integer():
        return int(result)
    return result


def x2_sources_available(
    sources: Iterable[tuple[bool, object | None]],
) -> bool:
    """Return true only when exactly two current source datasets exist."""
    materialized = list(sources)
    return len(materialized) == 2 and all(
        last_update_success and data is not None
        for last_update_success, data in materialized
    )


def should_create_x2(registration_count: int, owner_exists: bool) -> bool:
    """Return whether the second active config entry should create x2 sensors."""
    return registration_count == 2 and not owner_exists
