"""Chat-driven changes through the real service, queue-claimed handler and database."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from oryxenai.agents.code_generator.agent import CodeGeneratorAgent
from oryxenai.agents.code_generator.dev.mock_client import ReferenceModelClient
from oryxenai.agents.code_generator.service import CodeGeneratorOperationError
from oryxenai.agents.code_generator.serving import DbBundleProvider
from oryxenai.agents.shared.providers.errors import ProviderTimeoutError
from oryxenai.core.settings import get_settings
from oryxenai.db.models.agent_run import AgentRun
from oryxenai.db.models.background_job import BackgroundJob
from oryxenai.db.models.site_version import PortfolioSiteVersion
from oryxenai.db.session import get_sessionmaker
from oryxenai.jobs.handlers.code_generator import CodeGeneratorBuildHandler
from tests.integration.test_code_generator_worker import (
    _job_payload,
    _new_session,
    _service,
    _start_and_run,
)
from tests.unit.agents.code_generator.helpers import sample_content

pytestmark = pytest.mark.integration

CONTENT = sample_content("01_strong_profile")


def _plan(*ops: dict[str, Any], intent: str = "content_edit", **extra: Any) -> dict[str, Any]:
    return {"intent": intent, "reply": extra.pop("reply", "Done."), "ops": list(ops), **extra}


def _use(monkeypatch: pytest.MonkeyPatch, client: ReferenceModelClient) -> ReferenceModelClient:
    monkeypatch.setattr(
        "oryxenai.jobs.handlers.code_generator._build_code_generator_agent",
        lambda **kwargs: CodeGeneratorAgent(client, theme_id=kwargs["theme_id"]),
    )
    return client


async def _ready_session(db: Any, monkeypatch: pytest.MonkeyPatch, **client_kwargs: Any):
    client = _use(monkeypatch, ReferenceModelClient(**client_kwargs))
    session_id = await _new_session(db)
    await _start_and_run(db, session_id)
    return session_id, client


async def _say(
    db: Any, session_id: UUID, text: str, *, client_id: str | None = None
) -> dict[str, Any]:
    """Post a chat message and run its job like a worker would."""
    service = _service(db)
    state = await service.get_state(session_id)
    started = await service.post_message(
        session_id,
        message=text,
        client_message_id=client_id or str(uuid4()),
        base_version_id=state["code_generator"]["active_version_id"],
    )
    await db.commit()
    payload = await _job_payload(db, started)
    result = await CodeGeneratorBuildHandler().execute(payload, "test-worker")
    db.expire_all()
    return result


@pytest.mark.asyncio
async def test_a_content_change_builds_a_new_version_and_keeps_the_old_one(
    db_session, monkeypatch
) -> None:
    client = _use(monkeypatch, ReferenceModelClient())
    client.plans = [
        _plan(
            {"op": "set", "path": "hero.intro", "value": "A much shorter intro."},
            reply="Shortened your intro.",
        )
    ]
    session_id = await _new_session(db_session)
    await _start_and_run(db_session, session_id)
    first_calls = len(client.requests)

    result = await _say(db_session, session_id, "Make my intro shorter")
    assert result["status"] == "succeeded" and "version_id" in result
    assert [r["operation"] for r in client.requests[first_calls:]] == [
        "interpret_change",
        "generate_page",
    ]

    state = await _service(db_session).get_state(session_id)
    generator = state["code_generator"]
    assert (generator["status"], generator["active_version_number"], generator["last_error"]) == (
        "ready",
        2,
        None,
    )
    by_number = {v["version_number"]: v for v in state["versions"] if v["version_number"]}
    assert by_number[1]["status"] == by_number[2]["status"] == "ready"
    assert (
        by_number[2]["origin"] == "change"
        and by_number[2]["instruction"] == "Make my intro shorter"
    )
    assert by_number[2]["parent_version_id"] == by_number[1]["id"]

    detail = await _service(db_session).get_version(
        session_id, UUID(by_number[2]["id"]), include_html=True
    )
    assert "A much shorter intro." in detail["index_html"]
    old = await _service(db_session).get_version(
        session_id, UUID(by_number[1]["id"]), include_html=True
    )
    assert "A much shorter intro." not in old["index_html"]  # v1 is untouched
    assert [(m["role"], m["body"]) for m in state["chat"] if m["kind"] == "message"] == [
        ("user", "Make my intro shorter"),
        ("assistant", "Shortened your intro."),
    ]
    request = next(r for r in client.requests if r["operation"] == "interpret_change")
    assert request["input_payload"]["user_request"] == "Make my intro shorter"
    assert request["input_payload"]["content"]["hero"]["intro"] == CONTENT["hero"]["intro"]


@pytest.mark.asyncio
async def test_the_interpreter_sees_the_recent_conversation(db_session, monkeypatch) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [_plan(intent="chat_only", reply="Hello! I can edit your wording.")]
    await _say(db_session, session_id, "hi there")
    await _say(db_session, session_id, "what can you do?")
    seen = [r for r in client.requests if r["operation"] == "interpret_change"][-1]
    history = seen["input_payload"]["recent_conversation"]
    assert history == [
        {"role": "user", "text": "hi there"},
        {"role": "assistant", "text": "Hello! I can edit your wording."},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("plan", "expected"),
    [
        (
            _plan(intent="style_request", reply="Styling cannot be changed from chat yet."),
            "Styling cannot",
        ),
        (
            _plan(intent="needs_clarification", reply="", clarification="Which award?"),
            "Which award?",
        ),
        (_plan(intent="unsupported", reply="I cannot add scripts."), "cannot add scripts"),
        (_plan({"op": "set", "path": "hero.nope", "value": "x"}), "could not make that change"),
        (_plan({"op": "set", "path": "hero.name", "value": ""}), "could not make that change"),
    ],
)
async def test_messages_that_change_nothing_are_answered_without_building(
    db_session, monkeypatch, plan: dict[str, Any], expected: str
) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [plan]
    calls_before = len(client.requests)
    result = await _say(db_session, session_id, "change something")
    assert result == {**result, "status": "succeeded", "outcome": "reply"}
    assert [r["operation"] for r in client.requests[calls_before:]] == ["interpret_change"]

    state = await _service(db_session).get_state(session_id)
    assert state["code_generator"]["status"] == "ready"
    assert state["code_generator"]["active_version_number"] == 1
    assert len([v for v in state["versions"] if v["status"] == "ready"]) == 1
    assert len(state["versions"]) == 1  # no junk row for a reply
    assert expected in state["chat"][-1]["body"] and state["chat"][-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_a_failed_build_for_a_change_keeps_the_live_page(db_session, monkeypatch) -> None:
    name = CONTENT["hero"]["name"]
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [_plan({"op": "set", "path": "hero.intro", "value": "Fresh intro."})]
    client.mutate = lambda body: body.replace(name, name + " X", 1)  # the model paraphrases
    result = await _say(db_session, session_id, "freshen the intro")
    assert result["status"] == "failed"

    state = await _service(db_session).get_state(session_id)
    generator = state["code_generator"]
    assert generator["status"] == "ready" and generator["active_version_number"] == 1
    assert generator["last_error"]["code"] == "PAGE_COPY_MISMATCH"
    assert state["chat"][-1]["body"].startswith("I couldn't apply that change.")
    assert "last verified page is unchanged" in state["chat"][-1]["body"]
    assert [v["status"] for v in state["versions"]] == ["failed", "ready"]
    # The next message is accepted: a failure does not lock the chat.
    client.mutate = None
    client.plans = [_plan(intent="chat_only", reply="Ready when you are.")]
    again = await _say(db_session, session_id, "ok try something else")
    assert again["status"] == "succeeded"
    assert (await _service(db_session).get_state(session_id))["code_generator"][
        "last_error"
    ] is None


@pytest.mark.asyncio
async def test_an_interpreter_failure_is_reported_at_the_interpret_stage(
    db_session, monkeypatch
) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.error = ProviderTimeoutError("slow")
    result = await _say(db_session, session_id, "shorten it")
    assert result["status"] == "failed"
    state = await _service(db_session).get_state(session_id)
    error = state["code_generator"]["last_error"]
    assert (error["code"], error["stage"]) == ("PROVIDER_TIMEOUT_ERROR", "interpret")
    assert state["code_generator"]["status"] == "ready"
    assert len(state["versions"]) == 1  # nothing was created for the failed interpretation


@pytest.mark.asyncio
async def test_message_guards(db_session, monkeypatch) -> None:
    session_id = await _new_session(db_session)
    service = _service(db_session)
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.post_message(
            session_id, message="hi", client_message_id="c1", base_version_id=None
        )
    assert caught.value.code == "CODE_GENERATOR_NOT_READY"

    _use(monkeypatch, ReferenceModelClient())
    await _start_and_run(db_session, session_id)
    active = (await service.get_state(session_id))["code_generator"]["active_version_id"]
    for text, client_id, base, code, status in (
        ("", "c1", active, "CODE_GENERATOR_MESSAGE_INVALID", 422),
        ("x" * 1501, "c1", active, "CODE_GENERATOR_MESSAGE_INVALID", 422),
        ("hi", "", active, "CODE_GENERATOR_MESSAGE_INVALID", 422),
        ("hi", "c1", str(uuid4()), "CODE_GENERATOR_STALE_BASE", 409),
    ):
        with pytest.raises(CodeGeneratorOperationError) as caught:
            await service.post_message(
                session_id, message=text, client_message_id=client_id, base_version_id=base
            )
        assert (caught.value.code, caught.value.status_code) == (code, status)

    await service.post_message(
        session_id, message="hello", client_message_id="c2", base_version_id=active
    )
    await db_session.commit()
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.post_message(
            session_id, message="again", client_message_id="c3", base_version_id=active
        )
    assert caught.value.code == "CODE_GENERATOR_BUILD_IN_PROGRESS"
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.restore(session_id, uuid4())
    assert caught.value.code == "CODE_GENERATOR_BUILD_IN_PROGRESS"


@pytest.mark.asyncio
async def test_a_retried_message_is_accepted_once(db_session, monkeypatch) -> None:
    session_id, _client = await _ready_session(db_session, monkeypatch)
    service = _service(db_session)
    active = (await service.get_state(session_id))["code_generator"]["active_version_id"]
    first = await service.post_message(
        session_id, message="hello", client_message_id="same", base_version_id=active
    )
    await db_session.commit()
    second = await service.post_message(
        session_id, message="hello", client_message_id="same", base_version_id=active
    )
    await db_session.commit()
    assert (
        first["code_generator"]["in_flight"]["job_id"]
        == second["code_generator"]["in_flight"]["job_id"]
    )
    assert (
        await db_session.scalar(select(func.count()).select_from(BackgroundJob)) == 2
    )  # build + one change
    runs = (
        (await db_session.execute(select(AgentRun.input_payload["operation"].astext)))
        .scalars()
        .all()
    )
    assert sorted(runs) == ["build", "change"]


@pytest.mark.asyncio
async def test_the_hourly_change_limit(db_session, monkeypatch) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [_plan(intent="chat_only", reply="ok")]
    service = _service(db_session)
    monkeypatch.setattr(service._settings.code_generator, "max_changes_per_hour", 2)
    await _say(db_session, session_id, "one")
    await _say(db_session, session_id, "two")
    active = (await service.get_state(session_id))["code_generator"]["active_version_id"]
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.post_message(
            session_id, message="three", client_message_id="c3", base_version_id=active
        )
    assert (caught.value.code, caught.value.status_code) == ("CODE_GENERATOR_RATE_LIMITED", 429)


@pytest.mark.asyncio
async def test_stop_during_a_change_leaves_the_live_page_alone(db_session, monkeypatch) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    service = _service(db_session)
    active = (await service.get_state(session_id))["code_generator"]["active_version_id"]
    started = await service.post_message(
        session_id, message="shorten", client_message_id="s1", base_version_id=active
    )
    await db_session.commit()
    stopped = await service.stop(session_id)
    await db_session.commit()
    assert stopped["code_generator"]["status"] == "ready"
    assert stopped["code_generator"]["last_error"]["code"] == "JOB_CANCELLED"
    payload = await _job_payload(db_session, started, claim=False)
    result = await CodeGeneratorBuildHandler().execute(payload, "test-worker")
    assert result["status"] == "cancelled"
    assert [r["operation"] for r in client.requests].count("interpret_change") == 0


@pytest.mark.asyncio
async def test_restore_makes_an_older_page_live_as_a_new_version(db_session, monkeypatch) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [_plan({"op": "set", "path": "hero.intro", "value": "Second intro."})]
    await _say(db_session, session_id, "change the intro")
    service = _service(db_session)
    state = await service.get_state(session_id)
    v1 = next(v for v in state["versions"] if v["version_number"] == 1)

    calls = len(client.requests)
    restored = await service.restore(session_id, UUID(v1["id"]))
    await db_session.commit()
    assert len(client.requests) == calls  # no model call
    generator = restored["code_generator"]
    assert (generator["status"], generator["active_version_number"]) == ("ready", 3)
    newest = restored["versions"][0]
    assert (newest["origin"], newest["version_number"], newest["parent_version_id"]) == (
        "restore",
        3,
        v1["id"],
    )
    assert newest["index_sha256"] == v1["index_sha256"]
    assert restored["chat"][-1]["body"] == "Restored version 1 as version 3."
    live = await service.get_version(
        session_id, UUID(generator["active_version_id"]), include_html=True
    )
    assert "Second intro." not in live["index_html"]
    assert live["receipt"]["restored_from"]["version_number"] == 1

    again = await service.restore(session_id, UUID(generator["active_version_id"]))  # already live
    assert again["code_generator"]["active_version_number"] == 3
    assert await db_session.scalar(select(func.count()).select_from(PortfolioSiteVersion)) == 3


@pytest.mark.asyncio
async def test_restore_refuses_unfinished_or_foreign_versions(db_session, monkeypatch) -> None:
    session_id, _first_client = await _ready_session(db_session, monkeypatch)
    other, client = await _ready_session(
        db_session, monkeypatch
    )  # the factory now serves this client
    client.mutate = lambda body: body + "<script>1</script>"
    await _start_and_run_failure(db_session, session_id, client)
    service = _service(db_session)
    failed = next(
        v for v in (await service.get_state(session_id))["versions"] if v["status"] == "failed"
    )
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.restore(session_id, UUID(failed["id"]))
    assert caught.value.code == "CODE_GENERATOR_VERSION_NOT_RESTORABLE"
    foreign = (await service.get_state(other))["versions"][0]["id"]
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.restore(session_id, UUID(foreign))
    assert caught.value.status_code == 404


async def _start_and_run_failure(db: Any, session_id: UUID, client: ReferenceModelClient) -> None:
    client.plans = [_plan({"op": "set", "path": "hero.intro", "value": "Another intro."})]
    await _say(db, session_id, "change it")


@pytest.mark.asyncio
async def test_privacy_requests_make_older_pages_unreachable(db_session, monkeypatch) -> None:
    org = CONTENT["professional_context"]["organizations"][0]
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [
        _plan(
            {"op": "remove", "path": "professional_context.organizations[0]"},
            reply="Removed it.",
            privacy_sensitive=True,
        )
    ]
    await _say(db_session, session_id, f"please remove {org}, it is confidential")
    service = _service(db_session)
    state = await service.get_state(session_id)
    old = next(v for v in state["versions"] if v["version_number"] == 1)
    assert old["restricted"] is True
    assert state["code_generator"]["active_version_number"] == 2
    assert any(m["kind"] == "notice" and "no longer available" in m["body"] for m in state["chat"])

    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.restore(session_id, UUID(old["id"]))
    assert caught.value.code == "CODE_GENERATOR_VERSION_NOT_RESTORABLE"
    with pytest.raises(CodeGeneratorOperationError) as caught:
        await service.mint_preview(session_id, UUID(old["id"]))
    assert caught.value.status_code == 404
    provider = DbBundleProvider(get_sessionmaker(get_settings()))
    assert await provider.load(session_id, UUID(old["id"])) is None
    assert (
        await provider.load(session_id, UUID(state["code_generator"]["active_version_id"]))
        is not None
    )
    # The name is still in the intro sentence: the reply says exactly where, instead of pretending.
    reply = next(m for m in reversed(state["chat"]) if m["kind"] == "message")["body"]
    assert "still appears in hero.intro" in reply


@pytest.mark.asyncio
async def test_ordinary_edits_do_not_restrict_older_versions(db_session, monkeypatch) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    client.plans = [_plan({"op": "remove", "path": "professional_context.organizations[0]"})]
    await _say(db_session, session_id, "drop the first organization")
    state = await _service(db_session).get_state(session_id)
    assert all(not v["restricted"] for v in state["versions"])


@pytest.mark.asyncio
async def test_old_versions_beyond_the_cap_are_pruned_but_never_the_live_one(
    db_session, monkeypatch
) -> None:
    session_id, client = await _ready_session(db_session, monkeypatch)
    monkeypatch.setattr(get_settings().code_generator, "max_versions_per_session", 2)
    for n in range(3):
        client.plans = [_plan({"op": "set", "path": "hero.intro", "value": f"Intro number {n}."})]
        await _say(db_session, session_id, f"edit {n}")
    state = await _service(db_session).get_state(session_id)
    numbers = sorted(v["version_number"] for v in state["versions"])
    assert numbers == [3, 4]
    assert state["code_generator"]["active_version_number"] == 4
