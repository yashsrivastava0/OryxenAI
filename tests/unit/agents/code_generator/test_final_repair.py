from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic, SitePlan
from oryxenai.agents.code_generator.core.final_repair import repair_allowed_paths


def _diagnostic(file: str) -> Diagnostic:
    return Diagnostic(
        diagnostic_id="diagnostic-test",
        group="source_contract",
        code="SOURCE_BLUEPRINT_MOVE_MARKER_ONLY",
        phase="source_contract",
        normalized_message="The section CSS does not implement its compiler selector.",
        file=file,
        fingerprint="test",
    )


def test_final_repair_includes_only_existing_section_source_companion(tmp_path) -> None:
    section = tmp_path / "src/routes/home/sections/hero.tsx"
    section.parent.mkdir(parents=True)
    section.write_text("export const Hero = () => <section />;", encoding="utf-8")
    section.with_suffix(".css").write_text(".hero {}", encoding="utf-8")
    (section.parent / "unrelated.tsx").write_text(
        "export const Unrelated = () => <section />;", encoding="utf-8"
    )

    paths = repair_allowed_paths(
        [_diagnostic("src/routes/home/sections/hero.tsx")],
        SitePlan(plan_id="test", routes=[]),
        repo_dir=tmp_path,
    )

    assert paths == [
        "src/routes/home/sections/hero.css",
        "src/routes/home/sections/hero.tsx",
    ]


def test_final_repair_includes_existing_route_stylesheet_for_composer(tmp_path) -> None:
    composer = tmp_path / "src/routes/home/index.tsx"
    composer.parent.mkdir(parents=True)
    composer.write_text("export default function Home() { return null; }", encoding="utf-8")
    (composer.parent / "route.css").write_text(".route {}", encoding="utf-8")

    paths = repair_allowed_paths(
        [_diagnostic("src/routes/home/index.tsx")],
        SitePlan(plan_id="test", routes=[]),
        repo_dir=tmp_path,
    )

    assert paths == ["src/routes/home/index.tsx", "src/routes/home/route.css"]
