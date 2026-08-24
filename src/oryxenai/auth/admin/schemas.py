"""Strict administrator request and safe projection schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class AdminActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    confirmation: UUID = Field(validation_alias=AliasChoices("confirmation", "confirm_target_id"))
    username: str | None = Field(default=None, max_length=30)
    reason: str | None = Field(default=None, max_length=500)


class AdminOperationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    action: str
    target_type: str
    target_id: UUID | None
    status: str
    step: str
    attempt_count: int
    last_error_code: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    safe_state: dict[str, Any] = Field(default_factory=dict)


class AdminPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, Any]]
    next_cursor: str | None = None


class AdminSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    users: dict[str, int]
    projects: dict[str, int]
    jobs: dict[str, int]
    pending_operations: int
