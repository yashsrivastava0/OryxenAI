from oryxenai.agents.shared.model_router import ModelRouter
from oryxenai.core.settings import ModelConfig, ModelProfile, ModelRoutingConfig


def _profile(provider: str, model: str, display_name: str = "") -> ModelProfile:
    return ModelProfile(
        provider=provider,
        model=model,
        display_name=display_name,
        api_key_env="TEST_PROVIDER_KEY",
    )


def test_router_resolves_engine_routes_and_safe_override_options() -> None:
    config = ModelConfig(
        profiles={
            "default": _profile("anthropic", "claude-sonnet-5", "Anthropic default"),
            "discovery": _profile("anthropic", "claude-sonnet-5"),
            "fast": _profile("openai", "gpt-test", "Fast alternative"),
        },
        routing=ModelRoutingConfig(
            fallback_profile="default",
            selectable_profiles=["fast", "missing", "fast"],
            engine_profiles={"discovery": "discovery", "future_engine": "fast"},
        ),
    )
    router = ModelRouter(config)

    assert router.routed_profile_name("discovery") == "discovery"
    assert router.routed_profile_name("unknown") == "default"
    assert router.resolve_profile_name("discovery") == "discovery"
    assert router.resolve_profile_name("discovery", "fast") == "fast"
    assert router.resolve_profile_name("discovery", "missing") == "discovery"
    assert router.selectable_profile_names() == ("fast",)

    options = router.public_options()
    assert [option.id for option in options] == ["", "fast"]
    assert options[0].is_default is True
    assert options[0].id == ""
    assert all("api_key" not in str(option.as_dict()).lower() for option in options)
    assert all("base_url" not in str(option.as_dict()).lower() for option in options)
