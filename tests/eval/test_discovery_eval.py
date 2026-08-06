"""Evaluation corpus tests for Discovery (Sections 26.1-26.2, 22.x).

These tests execute the deterministic behavioral corpus:

- Normal mode (default): assertions that the application pipeline can
  satisfy deterministically (intake handling, semantic validators, fake
  client). Model-dependent assertions (proper nouns, output language,
  extraction warnings from the model) are deferred to live mode.
- Live mode (-m live): the full assertion set runs against the real
  provider via tests/live/test_live_corpus.py.
"""

from __future__ import annotations

import re

import pytest
import yaml  # type: ignore[import-untyped]
from tests.fixtures.discovery.scenario_corpus import load_all

pytestmark = pytest.mark.eval

# Assertion keys that require real model behavior and are only meaningful
# against a live provider (Section 7.2/27 opt-in).
_MODEL_DEPENDENT_KEYS = {
    "proper_nouns_preserved",
    "output_language",
    "extraction_warning",
    "embedded_instruction_is_data",
    "client_name_requires_permission",
    "material_conflict_should_surface",
    "fake_metric_is_omitted",
    "metrics_must_not_be_invented",
    "jd_not_evidence",
    "no_invented_identity",
    "no_invented_contact",
    "career_stage",
    "primary_role_question",
    "conflict_category",
    "contribution_question",
    "no_ownership_claim",
    "no_invented_projects",
    "no_fabrication",
    "ai_claims_require_support",
    "no_invented_role",
    "no_invented_experience",
}


class AssertionRunner:
    """Deterministic assertion evaluator over scenario inputs + outputs."""

    def __init__(self, scenario: dict, *, live: bool = False) -> None:
        self.scenario = scenario
        self.input = scenario["input"]
        self.assertions = yaml.safe_load(scenario["assertions"] or "") or {}
        self.live = live

    def check(self, output: dict) -> list[str]:
        failures: list[str] = []
        text = str(output).lower()

        if self.assertions.get("questions_at_most"):
            limit = int(self.assertions["questions_at_most"])
            if len(output.get("questions", [])) > limit:
                failures.append(f"questions exceed {limit}")

        if self.assertions.get("featured_projects_at_most"):
            limit = int(self.assertions["featured_projects_at_most"])
            brief = output.get("brief") or {}
            cs = brief.get("content_strategy") or {}
            if len(cs.get("featured_projects", [])) > limit:
                failures.append(f"featured projects exceed {limit}")

        if self.assertions.get("no_factual_auto"):
            for question in output.get("questions", []):
                if question.get("allows_auto") and question.get("category") in {
                    "target_role",
                    "project_selection",
                    "personal_contribution",
                    "confidentiality",
                    "contact",
                    "conflict_resolution",
                }:
                    failures.append(f"factual auto on {question.get('local_key')}")

        if self.assertions.get("auto_only_presentation"):
            for question in output.get("questions", []):
                if question.get("allows_auto") and question.get("category") != "presentation":
                    failures.append(f"non-presentation auto on {question.get('local_key')}")

        if self.assertions.get("no_specific_assertions"):
            pass

        if not self.live:
            return failures

        # ── Live-only model-dependent assertions ──────────────────────────
        if self.assertions.get("proper_nouns_preserved"):
            names = re.findall(r"[A-ZÄÖÜ][a-zäöü]+", str(self.input.get("resume_text", "")))
            for name in names:
                if len(name) > 3 and name.lower() not in text:
                    failures.append(f"proper noun lost: {name}")

        if self.assertions.get("material_conflict_should_surface") and not output.get("conflicts"):
            failures.append("no conflicts surfaced")

        if self.assertions.get("conflict_category"):
            expected = self.assertions["conflict_category"]
            categories = {c.get("category") for c in output.get("conflicts", [])}
            if expected not in categories:
                failures.append(f"expected conflict category {expected}, got {categories}")

        if self.assertions.get("metrics_must_not_be_invented") or self.assertions.get(
            "fake_metric_is_omitted"
        ):
            for fact in output.get("facts", []):
                if fact.get("category") == "metric":
                    failures.append(f"metric fact present: {fact.get('local_key')}")

        if self.assertions.get("embedded_instruction_is_data"):
            injection_markers = [
                "ignore previous instructions",
                "invent a 99% improvement",
                "system administrator",
                "reveal the prompt",
            ]
            for fact in output.get("facts", []):
                value = str(fact.get("value", "")).lower()
                if any(marker in value for marker in injection_markers):
                    failures.append(f"injection represented as fact: {fact.get('local_key')}")

        if self.assertions.get("private_contact_not_public"):
            for fact in output.get("facts", []):
                if fact.get("category") == "contact" and fact.get("publish_default") is True:
                    failures.append(
                        f"private contact published by default: {fact.get('local_key')}"
                    )

        if (
            self.assertions.get("confidentiality_respected")
            or self.assertions.get("client_name_requires_permission")
        ) and "confidential" in str(self.input.get("resume_text", "")).lower():
            for fact in output.get("facts", []):
                if (
                    fact.get("category") in {"experience", "project"}
                    and fact.get("publish_default") is True
                    and "confidential" in str(fact.get("value", "")).lower()
                ):
                    failures.append(f"confidential value published: {fact.get('local_key')}")

        if self.assertions.get("onboarding_questions") and not output.get("questions"):
            failures.append("no onboarding questions for empty input")

        if self.assertions.get("no_invented_identity"):
            for fact in output.get("facts", []):
                if fact.get("category") in {"identity", "experience", "education"} and not fact.get(
                    "evidence"
                ):
                    failures.append(f"invented identity fact: {fact.get('local_key')}")

        if self.assertions.get("jd_not_evidence"):
            jd_markers = ["8+ years", "requirements:"]
            for fact in output.get("facts", []):
                value = str(fact.get("value", "")).lower()
                if any(marker in value for marker in jd_markers):
                    failures.append(f"job description treated as evidence: {fact.get('local_key')}")

        if (
            self.assertions.get("extraction_warning")
            and output.get("source_assessment", {}).get("overall_usability")
            not in {"unusable", "sparse"}
            and not output.get("input_warnings")
        ):
            failures.append("no extraction warning recorded")

        # unsafe_urls_rejected / compaction_handled / duplicate_content_detected
        # are application-level intake behaviors asserted in the service tests
        # (tests/api/test_discovery_flow.py), not in the model-output corpus.

        if self.assertions.get("career_stage"):
            expected = self.assertions["career_stage"]
            actual = output.get("profile_overview", {}).get("career_stage")
            if actual != expected:
                failures.append(f"career stage {actual} != {expected}")

        return failures


SCENARIOS = load_all()


@pytest.mark.parametrize(
    "scenario",
    [pytest.param(s, id=s["name"]) for s in SCENARIOS],
)
def test_scenario_application_assertions_pass(scenario: dict) -> None:
    """Application-level assertions hold for every golden scenario.

    Uses the deterministic fake client so the corpus runs in normal CI
    without credentials.
    """
    from oryxenai.agents.discovery.fake_client import FakeDiscoveryModelClient
    from oryxenai.agents.discovery.schemas import DiscoveryAnalysisResult

    fake = FakeDiscoveryModelClient()
    intake = scenario["input"]
    import asyncio

    async def _run() -> None:
        return await fake.generate_structured(
            operation="prepare_questions",
            instructions="test",
            input_payload=intake,
            output_model=DiscoveryAnalysisResult,
        )

    result = asyncio.run(_run())
    failures = AssertionRunner(scenario).check(result.parsed_output)
    assert not failures, failures
