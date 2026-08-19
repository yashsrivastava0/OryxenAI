"""Bounded deterministic scheduling for independent generation work units."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from oryxenai.agents.code_generator.core.development_schemas import WorkUnit


@dataclass(frozen=True, slots=True)
class ScheduledUnitResult:
    unit_id: str
    wave: int
    value: object


def isolated_workspace_path(root: Path, unit: WorkUnit) -> Path:
    key = unit.isolated_workspace_key or unit.unit_id
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in key)
    return root / "route-batches" / safe


async def execute_waves(
    units: Iterable[WorkUnit],
    execute: Callable[[WorkUnit], Awaitable[object]],
    *,
    max_concurrency: int = 3,
) -> list[ScheduledUnitResult]:
    """Execute ready units in sorted waves with a hard concurrency ceiling."""

    values = list(units)
    by_id = {unit.unit_id: unit for unit in values}
    if len(by_id) != len(values):
        raise ValueError("work unit IDs must be unique")
    remaining = set(by_id)
    completed: set[str] = set()
    results: list[ScheduledUnitResult] = []
    semaphore = asyncio.Semaphore(max(1, int(max_concurrency)))
    wave = 0
    while remaining:
        ready = sorted(
            unit_id for unit_id in remaining if set(by_id[unit_id].depends_on).issubset(completed)
        )
        if not ready:
            raise ValueError("work graph contains a cycle or unknown dependency")

        async def run_one(unit_id: str, wave_number: int = wave) -> ScheduledUnitResult:
            async with semaphore:
                return ScheduledUnitResult(unit_id, wave_number, await execute(by_id[unit_id]))

        wave_results = await asyncio.gather(*(run_one(unit_id) for unit_id in ready))
        for item in sorted(wave_results, key=lambda value: value.unit_id):
            results.append(item)
            completed.add(item.unit_id)
            remaining.remove(item.unit_id)
        wave += 1
    return results
