"""Compatibility names for historical output rows used by cleanup only.

The existing table mappings stay singular so retained rows remain readable
without creating a second SQLAlchemy mapping for the same database tables.
"""

from oryxenai.db.models.code_generator_development import (
    CodeGeneratorEvent as ArchivedOutputEvent,
)
from oryxenai.db.models.code_generator_development import (
    CodeGeneratorRun as ArchivedOutputRun,
)
from oryxenai.db.models.code_generator_development import (
    CodeGeneratorStageAttempt as ArchivedOutputAttempt,
)

__all__ = ["ArchivedOutputAttempt", "ArchivedOutputEvent", "ArchivedOutputRun"]
