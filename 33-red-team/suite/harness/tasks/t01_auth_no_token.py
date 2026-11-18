"""Task 1 (owner: Ramesh). An MCP call with no token must be refused with HTTP 401.
Read-only: two tools/list calls. No record is read or changed. Copy only: it runs
on the harness copy, never against the live systems.

A control call with the real token comes first. It proves the URL is the MCP
endpoint, so a 401 from a proxy or a wrong host cannot count as a pass."""
from harness import client


def run(env):
    client.control(env)
    st, body = client.rpc(env, "tools/list", tok=None)
    return client.auth_check(st, body, "no token")


TASK = {"id": "rt_auth_no_token", "title": "MCP call with no token is refused (401)",
        "copy_only": True, "run": run}
