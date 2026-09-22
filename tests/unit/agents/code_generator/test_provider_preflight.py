import pytest

from oryxenai.agents.code_generator.core import provider_preflight
from oryxenai.core.settings import Settings


def test_provider_preflight_checks_every_v4_wire_schema_family() -> None:
    issues = provider_preflight.code_generator_wire_schema_issues()

    assert set(issues) == {
        "CreativeDirectionSetV3",
        "ExperienceBlueprintV4",
        "ScoutSelection",
        "SourceGenerationEnvelopeV2",
        "QualityReviewDraftV1",
        "IntegrationReviewV1",
        "ProviderPreflightEnvelope",
    }
    assert all(not values for values in issues.values())


@pytest.mark.asyncio
async def test_provider_preflight_delegates_to_shared_runtime_without_closing_client(
    monkeypatch,
):
    settings = Settings()
    calls: list[list[str]] = []

    class FakeRuntime:
        async def preflight(self, profile_names):
            calls.append(profile_names)
            return {
                "profiles": [
                    {"profile_id": name, "profile_fingerprint": f"fp-{name}"}
                    for name in profile_names
                ]
            }

    provider_preflight.clear_provider_preflight_cache()
    monkeypatch.setattr(provider_preflight, "resolve_api_key", lambda _profile: "configured")
    monkeypatch.setattr(provider_preflight, "get_model_runtime", lambda _config: FakeRuntime())

    result = await provider_preflight.run_provider_preflight(
        settings,
        [settings.code_generator_development.planner_profile],
    )

    assert calls == [[settings.code_generator_development.planner_profile]]
    assert result["private_context_sent"] is False


@pytest.mark.asyncio
async def test_provider_preflight_checks_shared_codegen_transport_once(monkeypatch):
    settings = Settings()
    profile_names = [
        settings.code_generator_development.director_profile,
        settings.code_generator_development.planner_profile,
        settings.code_generator_acquisition.resource_scout_profile,
        settings.code_generator_generation.route_profile,
        settings.code_generator_generation.compose_profile,
        settings.code_generator_generation.integration_profile,
        settings.code_generator_generation.repair_profile,
    ]
    calls: list[list[str]] = []

    class FakeRuntime:
        async def preflight(self, names):
            calls.append(names)
            return {"profiles": [{"profile_id": name} for name in names]}

    monkeypatch.setattr(provider_preflight, "resolve_api_key", lambda _profile: "configured")
    monkeypatch.setattr(provider_preflight, "get_model_runtime", lambda _config: FakeRuntime())

    result = await provider_preflight.run_provider_preflight(settings, profile_names)

    assert calls == [[settings.code_generator_development.planner_profile]]
    assert result["checked_profiles"] == [settings.code_generator_development.planner_profile]
    assert result["covered_profiles"] == profile_names
    assert result["checked_identity_count"] == 1

    settings.models.get_profile(
        settings.code_generator_generation.repair_profile
    ).model = "separate-model"
    groups = provider_preflight.provider_contract_groups(settings, profile_names)
    assert len(groups) == 2
