"""Finite, generator-owned repair policy for the final verification gates."""

from __future__ import annotations

from dataclasses import dataclass, field

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic

_NON_REPAIRABLE_PREFIXES = (
    "SOURCE_RUNTIME_NETWORK",
    "SOURCE_SECRET_ACCESS",
    "PACK_",
    "INPUT_",
    "TARGET_",
    "PROVENANCE_",
    "BROWSER_",
    "PREVIEW_",
)


@dataclass(slots=True)
class RepairBudget:
    max_total: int
    max_per_unit: int
    total_used: int = 0
    per_unit_used: dict[str, int] = field(default_factory=dict)
    fingerprint_counts: dict[str, int] = field(default_factory=dict)
    strategies: list[str] = field(default_factory=list)

    def can_attempt(self, diagnostics: list[Diagnostic], *, unit_id: str = "final") -> bool:
        if not diagnostics or self.total_used >= self.max_total:
            return False
        if self.per_unit_used.get(unit_id, 0) >= self.max_per_unit:
            return False
        return all(
            item.owner == "generator"
            and item.severity == "blocking"
            and not item.code.startswith(_NON_REPAIRABLE_PREFIXES)
            for item in diagnostics
        )

    def consume(self, diagnostics: list[Diagnostic], *, unit_id: str = "final") -> str:
        if not self.can_attempt(diagnostics, unit_id=unit_id):
            raise ValueError("The configured final repair budget cannot accept another attempt.")
        fingerprints = sorted({item.fingerprint for item in diagnostics})
        recurrence = any(self.fingerprint_counts.get(item, 0) > 0 for item in fingerprints)
        strategy = "bounded-correction" if not recurrence else "bounded-simplification"
        self.total_used += 1
        self.per_unit_used[unit_id] = self.per_unit_used.get(unit_id, 0) + 1
        for fingerprint in fingerprints:
            self.fingerprint_counts[fingerprint] = self.fingerprint_counts.get(fingerprint, 0) + 1
        self.strategies.append(strategy)
        return strategy

    def exhausted(self) -> bool:
        return self.total_used >= self.max_total
