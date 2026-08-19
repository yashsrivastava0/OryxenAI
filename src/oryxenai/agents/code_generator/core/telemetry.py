"""Safe, dependency-light telemetry primitives for producer/consumer jobs.

OpenTelemetry can be layered over this boundary later.  The durable UI and
tests use the same span/metric records without requiring an external backend.
Only low-cardinality identifiers, hashes, counts, durations, profiles, and
safe error codes are accepted.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class TelemetrySpan:
    name: str
    trace_id: str
    span_id: str
    kind: str
    attributes: dict[str, str | int | float | bool]
    duration_ms: float
    status: str = "ok"


@dataclass(slots=True)
class MetricsRegistry:
    counters: dict[str, int] = field(default_factory=dict)
    durations_ms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def observe(self, name: str, duration_ms: float) -> None:
        self.durations_ms.setdefault(name, []).append(round(float(duration_ms), 3))

    def snapshot(self) -> dict[str, object]:
        return {
            "counters": dict(self.counters),
            "durations_ms": {key: list(value) for key, value in self.durations_ms.items()},
        }


class Telemetry:
    def __init__(self, *, metrics: MetricsRegistry | None = None) -> None:
        self.metrics = metrics or MetricsRegistry()
        self.spans: list[TelemetrySpan] = []

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str = "",
        kind: str = "internal",
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> Iterator[str]:
        current_trace = trace_id or uuid4().hex
        span_id = uuid4().hex
        started = time.perf_counter()
        status = "ok"
        try:
            yield current_trace
        except Exception:
            status = "error"
            self.metrics.increment(f"{name}.errors")
            raise
        finally:
            duration = (time.perf_counter() - started) * 1000
            self.metrics.observe(name, duration)
            self.spans.append(
                TelemetrySpan(
                    name=name,
                    trace_id=current_trace,
                    span_id=span_id,
                    kind=kind,
                    attributes=dict(attributes or {}),
                    duration_ms=duration,
                    status=status,
                )
            )

    def producer(
        self,
        name: str,
        *,
        trace_id: str = "",
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> AbstractContextManager[str]:
        return self.span(name, trace_id=trace_id, kind="producer", attributes=attributes)

    def consumer(
        self,
        name: str,
        *,
        trace_id: str = "",
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> AbstractContextManager[str]:
        return self.span(name, trace_id=trace_id, kind="consumer", attributes=attributes)
