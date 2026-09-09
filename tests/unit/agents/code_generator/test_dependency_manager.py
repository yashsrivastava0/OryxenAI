from __future__ import annotations

import asyncio

import pytest

from oryxenai.agents.code_generator.core.dependency_manager import (
    DependencyManager,
    DependencyPolicyError,
    _create_stage_dir,
    _npm_executable,
    detect_import_dependencies,
    detect_supported_import_dependencies,
    detect_unsupported_import_dependencies,
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
    assert not (tmp_path / "repo" / "package.json").exists()
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


def test_dependency_stage_directory_is_immediately_writable(tmp_path) -> None:
    stage_dir = _create_stage_dir(tmp_path)

    marker = stage_dir / "package.json"
    marker.write_text("{}", encoding="utf-8")

    assert marker.read_text(encoding="utf-8") == "{}"


def test_dependency_manager_resolves_portable_npm_name(monkeypatch) -> None:
    settings = Settings()
    settings.code_generator_dependencies.npm_executable = "npm"
    monkeypatch.setattr(
        "oryxenai.agents.code_generator.core.dependency_manager.shutil.which",
        lambda value: "C:/Program Files/nodejs/npm.cmd" if value == "npm" else None,
    )

    assert _npm_executable(settings) == "C:/Program Files/nodejs/npm.cmd"


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


def test_detect_supported_import_dependencies_finds_subpath_and_scoped_imports() -> None:
    # Live-confirmed 2026-09-08/09: a pinned component fetched via Build
    # Preparation's resolution can import "motion/react" with no declared
    # dependency anywhere in the admitted pack -- this is the source-scan
    # fallback that catches it before the generated project ever fails
    # typecheck on a missing module.
    text = (
        'import { AnimatePresence, motion } from "motion/react";\n'
        'import { useId } from "react";\n'
        'import { cn } from "@/lib/utils";\n'
        'import Thing from "@radix-ui/react-id";\n'
        'const x = require("lucide-react");\n'
        'import "./local-styles.css";\n'
    )
    found = detect_supported_import_dependencies(
        text, {"motion", "lucide-react", "@radix-ui/react-id"}
    )
    assert found == {"motion", "lucide-react", "@radix-ui/react-id"}


def test_detect_supported_import_dependencies_ignores_unsupported_and_relative_imports() -> None:
    text = 'import { z } from "zod";\nimport util from "../shared/util";\n'
    assert detect_supported_import_dependencies(text, {"motion"}) == set()
    assert detect_supported_import_dependencies(text, set()) == set()


def test_dependency_scan_covers_dynamic_imports_and_reexports() -> None:
    text = (
        'export { motion } from "motion/react";\n'
        'const lazy = import("lucide-react/icons");\n'
        'const helper = require("@radix-ui/react-id");\n'
    )
    assert detect_import_dependencies(text) == {"motion", "lucide-react", "@radix-ui/react-id"}
    assert detect_unsupported_import_dependencies(
        text,
        installed_packages={"react"},
        supported_packages={"motion", "lucide-react"},
    ) == {"@radix-ui/react-id"}
