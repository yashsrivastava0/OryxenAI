from __future__ import annotations

import httpx
import pytest

from oryxenai.auth import http as auth_http
from oryxenai.auth.http import AuthHttpClient


async def _no_sleep(_seconds: float) -> None:
    return None


@pytest.mark.asyncio
async def test_get_retries_one_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_http.asyncio, "sleep", _no_sleep)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls == 1 else 200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    auth_client = AuthHttpClient(timeout=1, client=client)
    try:
        response = await auth_client.get("https://project.supabase.co/auth/v1/user")
    finally:
        await client.aclose()
        await auth_client.aclose()

    assert response.status_code == 200
    assert calls == 2


@pytest.mark.asyncio
async def test_get_retries_one_transport_error_on_injected_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_http.asyncio, "sleep", _no_sleep)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("temporary failure", request=request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    auth_client = AuthHttpClient(timeout=1, client=client)
    response = await auth_client.get("https://project.supabase.co/auth/v1/user")

    assert response.status_code == 200
    assert calls == 2
    assert not client.is_closed
    await auth_client.aclose()
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429, 400])
async def test_get_does_not_retry_client_or_rate_limit_responses(status_code: int) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    auth_client = AuthHttpClient(timeout=1, client=client)
    try:
        response = await auth_client.get("https://project.supabase.co/auth/v1/user")
    finally:
        await client.aclose()
        await auth_client.aclose()

    assert response.status_code == status_code
    assert calls == 1


@pytest.mark.asyncio
async def test_owned_client_is_recreated_after_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_http.asyncio, "sleep", _no_sleep)

    class FakeClient:
        def __init__(self, *, fail: bool) -> None:
            self.fail = fail
            self.closed = False

        async def request(
            self,
            method: str,
            url: str,
            *,
            headers: object = None,
            json: object = None,
        ) -> httpx.Response:
            del headers, json
            request = httpx.Request(method, url)
            if self.fail:
                self.fail = False
                raise httpx.ConnectError("network changed", request=request)
            return httpx.Response(200, request=request)

        async def aclose(self) -> None:
            self.closed = True

    clients = [FakeClient(fail=True), FakeClient(fail=False)]
    created: list[FakeClient] = []

    def make_client(**_kwargs: object) -> FakeClient:
        client = clients.pop(0)
        created.append(client)
        return client

    monkeypatch.setattr(auth_http.httpx, "AsyncClient", make_client)
    auth_client = AuthHttpClient(timeout=1)

    response = await auth_client.get("https://project.supabase.co/auth/v1/user")

    assert response.status_code == 200
    assert len(created) == 2
    assert created[0].closed is True
    assert created[1].closed is False
    await auth_client.aclose()
    assert created[1].closed is True


@pytest.mark.asyncio
async def test_single_shot_mutation_replaces_owned_client_without_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, *, fail: bool) -> None:
            self.fail = fail
            self.closed = False
            self.calls = 0

        async def request(
            self,
            method: str,
            url: str,
            *,
            headers: object = None,
            json: object = None,
        ) -> httpx.Response:
            del headers, json
            self.calls += 1
            request = httpx.Request(method, url)
            if self.fail:
                self.fail = False
                raise httpx.ConnectError("connection lost after send", request=request)
            return httpx.Response(204, request=request)

        async def aclose(self) -> None:
            self.closed = True

    clients = [FakeClient(fail=True), FakeClient(fail=False)]
    created: list[FakeClient] = []

    def make_client(**_kwargs: object) -> FakeClient:
        client = clients.pop(0)
        created.append(client)
        return client

    monkeypatch.setattr(auth_http.httpx, "AsyncClient", make_client)
    auth_client = AuthHttpClient(timeout=1)

    with pytest.raises(httpx.ConnectError):
        await auth_client.request("DELETE", "https://project.supabase.co/auth/v1/admin/users/1")

    assert len(created) == 2
    assert created[0].calls == 1
    assert created[0].closed is True
    response = await auth_client.request(
        "PUT",
        "https://project.supabase.co/auth/v1/admin/users/1",
        json_body={"ban_duration": "none"},
    )
    assert response.status_code == 204
    assert created[1].calls == 1
    await auth_client.aclose()
