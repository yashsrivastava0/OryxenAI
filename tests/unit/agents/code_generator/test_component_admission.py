from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from oryxenai.agents.code_generator.core import component_admission
from oryxenai.agents.code_generator.core.component_admission import (
    ComponentAdmissionError,
    run_component_toolchain_admission,
    validate_component_candidate,
)
from oryxenai.agents.code_generator.core.development_schemas import (
    LocalMaterialFile,
    ResourceCandidate,
)
from oryxenai.agents.code_generator.core.process_runner import ProcessResult
from tests.unit.agents.code_generator.test_acquisition_validators import _request


def _settings(tmp_path: Path, *, use_real_typecheck: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        code_generator_generation=SimpleNamespace(
            scaffold_root=str(tmp_path / "scaffold"),
            scaffold_profile="profile",
            use_real_typecheck=use_real_typecheck,
            typecheck_timeout_seconds=1.0,
        ),
        code_generator_dependencies=SimpleNamespace(
            npm_executable="npm",
            supported_packages={"react": {}},
        ),
    )


def _candidate(**metadata: object) -> ResourceCandidate:
    return ResourceCandidate(
        candidate_id="component-card",
        provider_key="fixture",
        provider_resource_id="component-card",
        category="component_source",
        title="Card",
        canonical_source="fixture://component-card",
        licence="MIT",
        vendoring_policy="vendor source",
        technical_metadata=dict(metadata),
    )


def _materialize_source(
    root: Path, source: str, *, css: str | None = None
) -> list[LocalMaterialFile]:
    directory = root / "component"
    directory.mkdir(parents=True, exist_ok=True)
    source_path = directory / "Card.tsx"
    source_path.write_text(source, encoding="utf-8")
    files = [
        LocalMaterialFile(
            local_path="component/Card.tsx",
            media_type="text/plain",
            size=len(source.encode("utf-8")),
            sha256="source-hash",
        )
    ]
    if css is not None:
        css_path = directory / "Card.css"
        css_path.write_text(css, encoding="utf-8")
        files.append(
            LocalMaterialFile(
                local_path="component/Card.css",
                media_type="text/plain",
                size=len(css.encode("utf-8")),
                sha256="css-hash",
            )
        )
    return files


def test_component_admission_checks_exports_dependencies_and_css(tmp_path: Path) -> None:
    storage = tmp_path / "materials"
    files = _materialize_source(
        storage,
        'import "./Card.css";\nexport function Card() { return null; }\n',
        css=".card { display: block; }\n",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"dependencies": {"react": "19.0.0"}}), encoding="utf-8"
    )
    settings = _settings(tmp_path)
    request = _request(
        category="component_source",
        technical_constraints={"required_exports": ["Card"]},
    )

    receipt = validate_component_candidate(
        files,
        storage_root=storage,
        candidate=_candidate(css_required=True),
        request=request,
        repo_dir=repo,
        settings=settings,
    )

    assert receipt["exports"] == ["Card"]
    assert receipt["css_present"] is True
    assert "./Card.css" in receipt["imports"]


def test_component_admission_rejects_unsupported_package_and_missing_export(tmp_path: Path) -> None:
    storage = tmp_path / "materials"
    files = _materialize_source(
        storage,
        'import { motion } from "framer-motion";\nexport function Card() { return motion; }\n',
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"dependencies": {"react": "19.0.0"}}), encoding="utf-8"
    )
    settings = _settings(tmp_path)
    request = _request(category="component_source")

    with pytest.raises(ComponentAdmissionError, match="unsupported package"):
        validate_component_candidate(
            files,
            storage_root=storage,
            candidate=_candidate(),
            request=request,
            repo_dir=repo,
            settings=settings,
        )

    package_dir = repo / "node_modules" / "react"
    package_dir.mkdir(parents=True)
    (package_dir / "package.json").write_text(
        json.dumps({"exports": {".": "./index.js"}}), encoding="utf-8"
    )
    files = _materialize_source(
        storage,
        'import "react/private";\nexport function Card() { return null; }\n',
    )
    with pytest.raises(ComponentAdmissionError, match="does not export"):
        validate_component_candidate(
            files,
            storage_root=storage,
            candidate=_candidate(),
            request=request,
            repo_dir=repo,
            settings=settings,
        )


@pytest.mark.asyncio
async def test_component_toolchain_admission_is_disposable(tmp_path: Path, monkeypatch) -> None:
    storage = tmp_path / "materials"
    files = _materialize_source(
        storage,
        "export function Card() { return null; }\n",
    )
    repo = tmp_path / "repo"
    (repo / "node_modules" / "typescript").mkdir(parents=True)
    (repo / "src").mkdir(parents=True)
    sentinel = repo / "src" / "App.tsx"
    sentinel.write_text("export default function App() { return null; }\n", encoding="utf-8")
    settings = _settings(tmp_path, use_real_typecheck=True)

    async def fake_run_command(command, **_kwargs) -> ProcessResult:
        return ProcessResult(command=tuple(command), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(component_admission, "run_command", fake_run_command)
    result = await run_component_toolchain_admission(
        files,
        storage_root=storage,
        candidate=_candidate(),
        request=_request(category="component_source"),
        repo_dir=repo,
        settings=settings,
    )

    assert result["typecheck"] == "passed"
    assert sentinel.read_text(encoding="utf-8").startswith("export default")
    assert not (repo / "src" / "generated" / "__admission__").exists()
    assert not list(repo.glob("tsconfig.component-admission-*.json"))
