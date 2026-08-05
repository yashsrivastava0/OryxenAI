"""Minimal request/response schemas for the Visual Design Director agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class VisualDesignDirectorRequest(BaseModel):
    """Input for the Visual Design Director agent."""

    content: dict[str, Any] = Field(default_factory=dict)
    brand: dict[str, Any] = Field(default_factory=dict)


class VisualDesignDirectorResponse(BaseModel):
    """Output from the Visual Design Director agent."""

    theme: dict[str, Any] = Field(default_factory=dict)
    palette: list[str] = Field(default_factory=list)
    typography: dict[str, Any] = Field(default_factory=dict)
