from oryxenai.agents.code_generator.core.build_runner import diagnostic
from oryxenai.jobs.handlers.code_generator_verification import _infrastructure_build_terminal


def test_vite_windows_spawn_denial_bypasses_source_repair_terminal() -> None:
    failure = diagnostic(
        "VITE_NODE_SPAWN_EPERM",
        "Vite could not start its Windows path-resolution helper.",
        phase="build",
        owner="infrastructure",
    )

    terminal = _infrastructure_build_terminal([failure])

    assert terminal is not None
    code, summary, next_action = terminal
    assert code == "TOOLCHAIN_NODE_SPAWN_DENIED"
    assert "source was not judged defective" in summary
    assert "rerun the toolchain preflight" in next_action


def test_source_build_failure_keeps_the_repair_path_available() -> None:
    failure = diagnostic(
        "BUILD_FAILED",
        "A generated module did not compile.",
        phase="build",
    )

    assert _infrastructure_build_terminal([failure]) is None
