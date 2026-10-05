"""Render visitor addresses must not come from a caller's forged XFF prefix."""

from starlette.requests import Request
from starlette.types import Scope

from oryxenai.main import RateLimitMiddleware


async def _app(_scope: Scope, _receive: object, _send: object) -> None:
    return None


def _request(*headers: tuple[bytes, bytes]) -> Request:
    return Request(
        {
            "type": "http",
            "scheme": "http",
            "method": "GET",
            "path": "/api/v1/me",
            "query_string": b"",
            "headers": list(headers),
            "client": ("10.0.0.1", 12345),
            "server": ("localhost", 8000),
        }
    )


def test_render_client_ip_uses_valid_connecting_ip() -> None:
    limiter = RateLimitMiddleware(_app, trusted_client_ip_header="cf-connecting-ip")
    request = _request(
        (b"x-forwarded-for", b"203.0.113.200, 198.51.100.2"),
        (b"cf-connecting-ip", b"198.51.100.2"),
    )
    assert limiter._client_ip(request) == "198.51.100.2"


def test_render_client_ip_rejects_invalid_header() -> None:
    limiter = RateLimitMiddleware(_app, trusted_client_ip_header="cf-connecting-ip")
    assert (
        limiter._client_ip(_request((b"cf-connecting-ip", b"spoofed, 198.51.100.2"))) == "10.0.0.1"
    )
