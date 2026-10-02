"""Fixed chat copy for build events (what the Studio timeline says about each build)."""

from __future__ import annotations

from oryxenai.agents.code_generator.schemas import FailureEnvelope


def build_started(origin: str) -> str:
    if origin == "retry":
        return "Trying the build again from your approved content."
    if origin == "change":
        return "Applying your change and rebuilding the page."
    return "Building your portfolio from your approved content."


def build_ready(version_number: int) -> str:
    return f"Your portfolio is ready (version {version_number})."


def build_failed(envelope: FailureEnvelope, *, kept_previous: bool) -> str:
    tail = " Your last verified page is unchanged." if kept_previous else ""
    return f"I couldn't finish this build. {envelope.summary}{tail}"


def build_stopped(*, kept_previous: bool) -> str:
    tail = " Your last verified page is unchanged." if kept_previous else ""
    return f"The build was stopped.{tail}"
