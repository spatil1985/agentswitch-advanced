"""The sample agent's door to the platform: MCP through the official SDK, read-only tools only.

Every call passes a read-only guard before it is sent, so this agent cannot change a record.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError
from mcp.types import Tool

CALL_TIMEOUT_S = 90
RESULT_CHARS = 4000


class RefusedWrite(Exception):
    """A tool that is not marked read-only was about to be called."""


def is_read_only(tool: Tool) -> bool:
    risk = (tool.meta or {}).get("agentswitch", {}).get("risk")
    hinted = tool.annotations is not None and tool.annotations.read_only_hint is True
    return hinted or risk == "READ"


def function_name(tool_name: str) -> str:
    """OpenAI function names allow only letters, digits, _ and -; MCP names use dots (Party.list)."""
    return re.sub(r"[^A-Za-z0-9_-]", "__", tool_name)


def as_function(tool: Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": function_name(tool.name),
            "description": (tool.description or tool.name)[:1000],
            "parameters": tool.input_schema or {"type": "object", "properties": {}},
        },
    }


class Platform:
    """The tools this agent may use: the allowlist, narrowed to read-only tools the server actually lists."""

    def __init__(self, client: Client, tools: dict[str, Tool]) -> None:
        self._client, self.tools = client, tools
        self.by_function = {function_name(n): n for n in tools}

    async def call(self, function: str, arguments: dict[str, Any]) -> str:
        name = self.by_function.get(function)
        tool = self.tools.get(name or "")
        if tool is None or not is_read_only(tool):
            raise RefusedWrite(f"{function} is not an allowed read-only tool")
        try:
            async with asyncio.timeout(CALL_TIMEOUT_S):
                result = await self._client.call_tool(tool.name, arguments)
        except MCPError as e:  # a refusal arrives inside a successful HTTP reply
            return json.dumps(
                {"error": e.message, "code": (e.data or {}).get("code") if isinstance(e.data, dict) else None}
            )
        except TimeoutError:
            return json.dumps({"error": f"no answer within {CALL_TIMEOUT_S}s"})
        payload: Any = result.structured_content
        if payload is None:
            payload = "".join(getattr(c, "text", "") for c in result.content)
        return (payload if isinstance(payload, str) else json.dumps(payload, default=str))[:RESULT_CHARS]


def _tolerate_schema_mismatches(client: Client) -> None:
    """Some list replies break their own declared output schema (BUG-34-001 draft). Read them anyway."""
    session = client.session
    strict = session.validate_tool_result

    async def tolerant(name: str, result: Any) -> None:
        with suppress(RuntimeError):
            await strict(name, result)

    session.validate_tool_result = tolerant  # type: ignore[method-assign]


@asynccontextmanager
async def open_platform(base_url: str, token: str, allowlist: list[str]) -> AsyncIterator[Platform]:
    headers = {"Authorization": f"Bearer {token}"}
    async with (
        httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(60, read=120)) as http,
        Client(
            streamable_http_client(f"{base_url.rstrip('/')}/api/mcp", http_client=http), mode="legacy"
        ) as client,
    ):
        _tolerate_schema_mismatches(client)
        listed = (await client.list_tools()).tools
        allowed = {t.name: t for t in listed if t.name in allowlist and is_read_only(t)}
        yield Platform(client, allowed)
