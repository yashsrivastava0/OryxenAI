"""Ephemeral loopback ASGI server handles for candidate verification."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from typing import Any

import httpx
import uvicorn


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass(slots=True)
class EphemeralServer:
    server: uvicorn.Server
    task: asyncio.Task[Any]
    url: str

    async def close(self) -> None:
        self.server.should_exit = True
        await self.task


async def start_ephemeral_server(app: Any, *, timeout_seconds: float = 10.0) -> EphemeralServer:
    port = _free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
        lifespan="off",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    url = f"http://127.0.0.1:{port}"
    try:
        async with httpx.AsyncClient() as client:
            deadline = asyncio.get_running_loop().time() + timeout_seconds
            while asyncio.get_running_loop().time() < deadline:
                if task.done():
                    await task
                    raise RuntimeError("The preview gateway stopped before becoming ready.")
                try:
                    response = await client.get(url, timeout=0.5)
                    if response.status_code in {200, 404, 503}:
                        return EphemeralServer(server=server, task=task, url=url)
                except httpx.HTTPError:
                    await asyncio.sleep(0.05)
        raise TimeoutError("The preview gateway did not become ready.")
    except BaseException:
        server.should_exit = True
        await task
        raise
