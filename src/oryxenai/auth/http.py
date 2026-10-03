"""Bounded, self-healing HTTP reads for Supabase authentication."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

import httpx

logger = logging.getLogger(__name__)


class AuthHttpClient:
    """Perform bounded requests and refresh an owned client after transport errors."""

    def __init__(
        self,
        *,
        timeout: httpx.Timeout | float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout
        self._owns_client = client is None
        self._client = client or self._new_client()
        self._condition = asyncio.Condition()
        self._active: dict[int, int] = {}
        self._retired: dict[int, httpx.AsyncClient] = {}
        self._closed = False

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=5,
                keepalive_expiry=5.0,
            ),
        )

    async def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """GET once, retrying one transport error or 5xx response."""
        return await self.request("GET", url, headers=headers, retry_transient=True)

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: object | None = None,
        retry_transient: bool = False,
    ) -> httpx.Response:
        """Send a request; retries are restricted to explicitly idempotent GETs."""
        normalized_method = method.upper()
        if retry_transient and normalized_method != "GET":
            raise ValueError("Only GET requests may be retried by the auth HTTP client.")
        attempts = 2 if retry_transient else 1
        for attempt in range(attempts):
            client = await self._acquire()
            response: httpx.Response | None = None
            request_error: httpx.RequestError | None = None
            try:
                response = await client.request(
                    normalized_method,
                    url,
                    headers=headers,
                    json=json_body,
                )
            except httpx.RequestError as exc:
                request_error = exc
                if self._owns_client:
                    await self._replace_after_failure(client)
            finally:
                await self._release(client)

            if request_error is not None:
                error_detail = " ".join(str(request_error).split())[:240]
                logger.warning(
                    "Supabase auth HTTP %s failed on attempt %d (%s) for host %s: %s",
                    normalized_method,
                    attempt + 1,
                    type(request_error).__name__,
                    httpx.URL(url).host,
                    error_detail,
                )
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.2)
                    continue
                raise request_error

            assert response is not None
            if response.status_code >= 500 and attempt + 1 < attempts:
                await asyncio.sleep(0.2)
                continue
            return response

        raise AssertionError("bounded auth request loop exited unexpectedly")

    async def _acquire(self) -> httpx.AsyncClient:
        async with self._condition:
            if self._closed:
                raise RuntimeError("Supabase auth HTTP client is closed.")
            client = self._client
            client_id = id(client)
            self._active[client_id] = self._active.get(client_id, 0) + 1
            return client

    async def _replace_after_failure(self, failed_client: httpx.AsyncClient) -> None:
        async with self._condition:
            if self._closed or self._client is not failed_client:
                return
            self._client = self._new_client()
            self._retired[id(failed_client)] = failed_client

    async def _release(self, client: httpx.AsyncClient) -> None:
        close_client: httpx.AsyncClient | None = None
        async with self._condition:
            client_id = id(client)
            remaining = self._active.get(client_id, 0) - 1
            if remaining > 0:
                self._active[client_id] = remaining
            else:
                self._active.pop(client_id, None)
                close_client = self._retired.pop(client_id, None)
            self._condition.notify_all()
        if close_client is not None:
            await close_client.aclose()

    async def aclose(self) -> None:
        if not self._owns_client:
            return
        async with self._condition:
            if self._closed:
                return
            self._closed = True
            await self._condition.wait_for(lambda: not self._active)
            clients = [self._client, *self._retired.values()]
            self._retired.clear()
        await asyncio.gather(*(client.aclose() for client in clients))
