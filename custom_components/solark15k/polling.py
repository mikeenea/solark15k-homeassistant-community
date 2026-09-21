"""Tiered polling schedule definitions for Sol-Ark 15K telemetry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PollGroup:
    """One independently scheduled contiguous Modbus read group."""

    name: str
    start: int
    count: int
    interval: float
    priority: int


def build_poll_groups(live_interval: float, fault_interval: float, detail_interval: float, energy_interval: float, *, include_settings: bool = False) -> tuple[PollGroup, ...]:
    """Return the tiered register schedule."""
    groups = (
        PollGroup("live", 166, 31, live_interval, 0),
        PollGroup("faults", 103, 4, fault_interval, 1),
        PollGroup("pv_detail", 107, 8, detail_interval, 2),
        PollGroup("ac_detail", 150, 16, detail_interval, 2),
        PollGroup("energy_60_75", 60, 16, energy_interval, 3),
        PollGroup("energy_76_91", 76, 16, energy_interval, 3),
        PollGroup("energy_92_102", 92, 11, energy_interval, 3),
    )
    if not include_settings:
        return groups
    return groups + (
        PollGroup("settings_generator", 231, 1, detail_interval, 4),
        PollGroup("settings_tou", 250, 30, detail_interval, 4),
    )
