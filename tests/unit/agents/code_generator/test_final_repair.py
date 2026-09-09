from __future__ import annotations

from oryxenai.agents.code_generator.core.development_schemas import Diagnostic, RoutePlan, SitePlan
from oryxenai.agents.code_generator.core.final_repair import repair_allowed_paths


def _diagnostic(file: str = "", route_id: str = "") -> Diagnostic:
    return Diagnostic(
        diagnostic_id="diagnostic-test",
        group="source_contract",
        code="SOURCE_BLUEPRINT_MOVE_MARKER_ONLY",
        phase="source_contract",
        normalized_message="The section CSS does not implement its compiler selector.",
        file=file,
        route_id=route_id,
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


def test_route_scoped_diagnostic_resolves_the_hashed_storage_key() -> None:
    paths = repair_allowed_paths(
        [_diagnostic(route_id="home")],
        SitePlan(plan_id="test", routes=[]),
        {
            "site/contract.json": {
                "routes": [{"route_id": "home", "storage_key": "home-4ea140588150-4859f06d"}]
            }
        },
    )

    assert paths == ["src/routes/home-4ea140588150-4859f06d/**"]


def test_route_scoped_diagnostic_prefers_canonical_plan_storage_key() -> None:
    """Runtime diagnostics must expose the source tree the compiler wrote.

    Build Preparation's projection can still contain ``routes/home`` while
    the accepted plan carries the collision-safe key used on disk.  A final
    repair must follow the plan rather than authorize a nonexistent semantic
    directory.
    """

    plan = SitePlan(
        plan_id="test",
        routes=[
            RoutePlan(
                route_id="home",
                path="/",
                storage_key="home-4ea14058",
                section_ids=["home:introduction"],
                responsive_outcome="",
                reduced_motion_outcome="",
                interaction_outcome="",
            )
        ],
    )

    paths = repair_allowed_paths(
        [_diagnostic(route_id="home")],
        plan,
        {
            "site/contract.json": {
                "routes": [{"route_id": "home", "storage_key": "routes/home"}]
            }
        },
    )

    assert paths == ["src/routes/home-4ea14058/**"]


def test_route_scoped_diagnostic_never_guesses_a_bare_route_directory() -> None:
    """A missing/stale site-contract projection must not fabricate a
    src/routes/<bare-route-id>/** path — a real past export shows the model
    creating a wrong, separate route tree there instead of touching the
    actual hashed directory."""

    paths = repair_allowed_paths(
        [_diagnostic(route_id="home")],
        SitePlan(plan_id="test", routes=[]),
        {"site/contract.json": {"routes": []}},
    )

    assert paths == ["src/design/**", "src/components/shared/**"]
    assert "src/routes/home/**" not in paths
