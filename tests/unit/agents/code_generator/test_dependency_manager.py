from __future__ import annotations

import asyncio

import pytest

from oryxenai.agents.code_generator.core.dependency_manager import (
    DependencyManager,
    DependencyPolicyError,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    DependencyRequest,
    ResourceReceipt,
)
from oryxenai.core.settings import Settings


def _request(package_name: str = "lucide-react") -> DependencyRequest:
    return DependencyRequest(
        request_id="dep-1",
        requesting_resource_receipt_hash="resource-1",
        package_name=package_name,
        required_api_or_exports=["Heart"],
        compatibility_constraints="react-vite-v1",
        reason_existing_stack_is_insufficient="The component imports the icon API.",
        fallback_component_strategy="use a simple local icon",
    )


def test_supported_dependency_never_synthesizes_a_package_install_and_unsupported_uses_fallback(
    tmp_path,
) -> None:
    settings = Settings()
    settings.code_generator_dependencies.workspaces_root = str(tmp_path / "workspaces")
    # Hermetic: an empty offline cache guarantees the real npm invocation
    # fails instead of depending on whatever the developer warmed.
    settings.code_generator_dependencies.npm_cache_root = str(tmp_path / "empty-cache")
    receipt = ResourceReceipt(request_hash="resource-1", disposition="admitted", licence="MIT")
    manager = DependencyManager([receipt])
    with pytest.raises(DependencyPolicyError, match="package-manager lockfile command failed"):
        asyncio.run(
            manager.resolve(
                _request(),
                repo_dir=tmp_path / "repo",
                prior_manifest={},
                prior_lock={},
                settings=settings,
            )
        )
    assert not (tmp_path / "repo" / "node_modules").exists()
    assert not (tmp_path / "repo" / "package-lock.json").exists()
    configured_pin = str(
        settings.code_generator_dependencies.supported_packages["lucide-react"]["version_pin"]
    )
    second = asyncio.run(
        manager.resolve(
            _request("not-configured"),
            repo_dir=tmp_path / "repo",
            prior_manifest={"dependencies": {"lucide-react": configured_pin}},
            prior_lock={},
            settings=settings,
        )
    )
    assert second.decision == "rejected_fallback"


def test_existing_dependency_does_not_reinstall(tmp_path) -> None:
    settings = Settings()
    receipt = ResourceReceipt(request_hash="resource-1", disposition="admitted", licence="MIT")
    manager = DependencyManager([receipt])
    configured_pin = str(
        settings.code_generator_dependencies.supported_packages["lucide-react"]["version_pin"]
    )
    result = asyncio.run(
        manager.resolve(
            _request(),
            repo_dir=tmp_path / "repo",
            prior_manifest={"dependencies": {"lucide-react": configured_pin}},
            prior_lock={"lockfileVersion": 3},
            settings=settings,
        )
    )
    assert result.decision == "existing"


def test_install_script_dependency_is_rejected_by_policy(tmp_path) -> None:
    settings = Settings()
    settings.code_generator_dependencies.supported_packages["unsafe"] = {
        "version_pin": "1.0.0",
        "licence": "MIT",
        "install_scripts": True,
    }
    request = _request("unsafe")
    result = asyncio.run(
        DependencyManager(
            [ResourceReceipt(request_hash="resource-1", disposition="admitted", licence="MIT")]
        ).resolve(
            request, repo_dir=tmp_path / "repo", prior_manifest={}, prior_lock={}, settings=settings
        )
    )
    assert result.decision == "rejected_fallback"
    assert result.install_script_result == "blocked_per_policy"
