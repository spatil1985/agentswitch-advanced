"""Read-only REST access to the platform for the eval harness.

Why REST and not MCP: the instructor said verifiers read data over REST; checking through a different door
from the one the agent uses (MCP) means a fault in that layer cannot hide itself; and plain GET calls cannot
change anything. This class has no method that sends anything other than GET.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from types import TracebackType
from typing import Any, Self

import httpx2

TIMEOUT = httpx2.Timeout(60, read=60)
PAGE_SIZE = 500


class PlatformError(Exception):
    """A read failed. Names the path, the status and the platform's message; never the token."""

    def __init__(self, path: str, status: int | None, detail: str) -> None:
        super().__init__(f"GET {path} -> {status if status is not None else 'no reply'}: {detail[:200]}")
        self.path, self.status, self.detail = path, status, detail


@dataclass(frozen=True)
class Me:
    user_id: str
    server_time: datetime  # from the HTTP Date header: the platform's clock, not ours


class PlatformReader:
    """Use as `async with PlatformReader(base_url, token) as platform:`."""

    def __init__(self, base_url: str, token: str, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        """`transport` is for tests only (a fake platform); runs always use the real network."""
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx2.Response:
        try:
            reply = await self._client.get(path, params=params)
        except httpx2.HTTPError as e:
            raise PlatformError(path, None, type(e).__name__) from None
        if reply.status_code != 200:
            raise PlatformError(path, reply.status_code, _detail(reply))
        return reply

    async def whoami(self) -> Me:
        """The login check: who the token belongs to, and the server's time now."""
        reply = await self._get("/api/auth/me")
        date = reply.headers.get("date")
        server_time = parsedate_to_datetime(date) if date else datetime.now(UTC)
        return Me(user_id=str(reply.json()["id"]), server_time=server_time.astimezone(UTC))

    async def get(self, entity: str, record_id: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._get(f"/api/{entity}/{record_id}")).json()
        return data

    async def list_page(self, entity: str, limit: int, **filters: Any) -> list[dict[str, Any]]:
        """One page, for picking a few targets."""
        page = (await self._get(f"/api/{entity}", {"limit": limit, "offset": 0, **filters})).json()
        rows: list[dict[str, Any]] = page.get("data", [])
        return rows

    async def list_all(self, entity: str, **filters: Any) -> list[dict[str, Any]]:
        """Every matching row, reading page after page until `total` rows are in."""
        rows: list[dict[str, Any]] = []
        while True:
            page = (
                await self._get(f"/api/{entity}", {"limit": PAGE_SIZE, "offset": len(rows), **filters})
            ).json()
            batch = page.get("data", [])
            rows.extend(batch)
            if not batch or len(rows) >= int(page.get("total", 0)):
                return rows


def _detail(reply: httpx2.Response) -> str:
    try:
        body = reply.json()
    except ValueError:
        return reply.text[:200]
    return str(body.get("detail", body)) if isinstance(body, dict) else str(body)[:200]
