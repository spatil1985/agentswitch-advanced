"""Task 2 (owner: Ramesh). Our token with a few characters changed must be refused with
HTTP 401. Tokens are opaque, not JWTs. Read-only: two tools/list calls. Copy only:
it runs on the harness copy, never against the live systems.

A control call with the real token comes first. If the real token does not work,
a 401 for the changed one proves nothing, so that is reported as infrastructure."""
from harness import client


def tamper(tok):
    """Change 4 characters in the middle. Same length, never equal to the original."""
    if len(tok) < 8:
        raise client.InfraError("AGENTSWITCH_TOKEN is too short to change")
    i = len(tok) // 2 - 2
    mid = "".join("B" if c == "A" else "A" for c in tok[i:i + 4])
    return tok[:i] + mid + tok[i + 4:]


def run(env):
    changed = tamper(client.token(env))
    client.control(env)
    st, body = client.rpc(env, "tools/list", tok=changed)
    return client.auth_check(st, body, "changed token")


TASK = {"id": "rt_auth_tampered_token", "title": "MCP call with a changed token is refused (401)",
        "copy_only": True, "run": run}
