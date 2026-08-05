"""Minimal request/response schemas for the Code Generator agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CodeGeneratorRequest(BaseModel):
    """Input for the Code Generator agent."""

    content: dict[str, Any] = Field(default_factory=dict)
    design: dict[str, Any] = Field(default_factory=dict)


class CodeGeneratorResponse(BaseModel):
    """Output from the Code Generator agent."""

    files: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
