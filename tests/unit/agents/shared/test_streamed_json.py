from __future__ import annotations

from types import SimpleNamespace

from oryxenai.agents.shared.providers.opencode_go import _collect_stream, _parse_json_object


async def test_collect_stream_keeps_content_finish_reason_and_usage() -> None:
    async def chunks():
        yield SimpleNamespace(
            id="response-1",
            model="model-1",
            usage=None,
            choices=[SimpleNamespace(delta=SimpleNamespace(content='{"ok":'), finish_reason=None)],
        )
        yield SimpleNamespace(
            id="response-1",
            model="model-1",
            usage=None,
            choices=[SimpleNamespace(delta=SimpleNamespace(content="true}"), finish_reason="stop")],
        )
        yield SimpleNamespace(
            id="response-1", model="model-1", usage={"prompt_tokens": 2}, choices=[]
        )

    response = await _collect_stream(chunks())
    assert response.choices[0].message.content == '{"ok":true}'
    assert response.choices[0].finish_reason == "stop"
    assert response.usage == {"prompt_tokens": 2}
    assert response.model == "model-1"


def test_json_object_accepts_fence_and_leading_text() -> None:
    assert _parse_json_object('Here is the result:\n```json\n{"ok":true}\n```') == {"ok": True}
