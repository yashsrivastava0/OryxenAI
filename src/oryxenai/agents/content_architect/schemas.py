"""Minimal request/response schemas for the Content Architect agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContentArchitectRequest(BaseModel):
    """Input for the Content Architect agent."""

    discovery: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)


class ContentArchitectResponse(BaseModel):
    """Output from the Content Architect agent."""

    sections: list[dict[str, Any]] = Field(default_factory=list)
    outline: dict[str, Any] = Field(default_factory=dict)
