"""Small MCP client for the v1 suite. Standard library only.

It reads the instance and token from the harness environment
(34-eval-harness/TASK_FORMAT.md, section 2). It never prints, logs or stores the token.
"""
import json
import urllib.error
import urllib.request

TIMEOUT = 30

# Error codes the platform returns (same as replay/).
DENIED = {"permission_denied"}          # JSON-RPC -32001
NOT_EXPOSED = {"tool_not_available"}    # JSON-RPC -32602, not in this login's tools/list
NOT_FOUND = {"not_found"}               # JSON-RPC -32004


class InfraError(Exception):
    """The check could not be made (missing setting, network error, bad token, wrong URL).
    The runner reports it as an infrastructure failure, never as a pass."""


def api_base(env):
    """Host root for REST paths like /api/auth/me (strips a trailing /api/mcp)."""
    base = (env.get("AGENTSWITCH_BASE_URL") or "").rstrip("/")
    if not base:
        raise InfraError("AGENTSWITCH_BASE_URL is not set")
    if base.endswith("/api/mcp"):
        base = base[: -len("/api/mcp")].rstrip("/")
    if not base:
        raise InfraError("AGENTSWITCH_BASE_URL is not set")
    return base


def mcp_url(env):
    base = (env.get("AGENTSWITCH_BASE_URL") or "").rstrip("/")
    if not base:
        raise InfraError("AGENTSWITCH_BASE_URL is not set")
    return base if base.endswith("/api/mcp") else base + "/api/mcp"


def token(env):
    tok = env.get("AGENTSWITCH_TOKEN")
    if not tok:
        raise InfraError("AGENTSWITCH_TOKEN is not set")
    return tok


def whoami(env):
    """GET /api/auth/me with the seat token. Returns a dict that includes id.
    On non-200, non-dict, or missing id, raises InfraError. Does not log the token."""
    url = api_base(env) + "/api/auth/me"
    headers = {"Accept": "application/json",
               "Authorization": "Bearer " + token(env)}
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            st, raw = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        st, raw = e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        raise InfraError(f"whoami network error ({type(e).__name__})") from None
    if st != 200:
        raise InfraError(f"whoami HTTP {st}")
    try:
        body = json.loads(raw)
    except ValueError:
        raise InfraError("whoami non-JSON body") from None
    if not isinstance(body, dict) or body.get("id") in (None, ""):
        raise InfraError("whoami missing id")
    return body


def rpc(env, method, params=None, tok=None):
    """One JSON-RPC call. tok=None sends no Authorization header.
    Returns (http_status, parsed_body)."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                       "params": params or {}}).encode()
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if tok is not None:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(mcp_url(env), data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, _parse(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError) as e:
        raise InfraError(f"network error ({type(e).__name__})") from None


def tool(env, name, args=None):
    """tools/call with the seat token. Returns (http_status, data, is_error).
    On a JSON-RPC error, data is the error object. On a tool result, data is the
    parsed text content (or the raw result if it has no text), and is_error is
    the result's isError flag."""
    st, resp = rpc(env, "tools/call", {"name": name, "arguments": args or {}}, tok=token(env))
    data, err = resp, False
    if isinstance(resp, dict):
        if "result" in resp:
            res = resp["result"]
            if isinstance(res, dict) and "content" in res:
                items = res.get("content")
                items = items if isinstance(items, list) else []
                txt = "\n".join(str(c.get("text") or "") for c in items
                                if isinstance(c, dict) and c.get("type") == "text")
                if txt:
                    try:
                        data = json.loads(txt)
                    except ValueError:
                        data = txt
                else:
                    data = res
                err = bool(res.get("isError", False))
            else:
                data = res
        elif "error" in resp:
            data, err = resp["error"], True
    return st, data, err


def error_code(data):
    """The platform's error code as a string, e.g. 'permission_denied', or None.
    Checks the JSON-RPC error shape (error.data.code) and a tool result marked
    isError ({"code": ...} or {"error": {"code": ...}})."""
    if not isinstance(data, dict):
        return None
    for holder in (data.get("data"), data, data.get("error")):
        if isinstance(holder, dict) and isinstance(holder.get("code"), str):
            return holder["code"]
    return None


def refused(st, data, is_error):
    """True only for a real refusal: HTTP 403, permission_denied or tool_not_available.
    An empty 200, a bad-argument error or a server error is NOT a refusal."""
    code = error_code(data) if is_error else None
    return st == 403 or code in DENIED or code in NOT_EXPOSED


def control(env):
    """The real token must reach the MCP endpoint: HTTP 200 with a tools/list result.
    If not, no auth check means anything, so it is reported as infrastructure."""
    st, body = rpc(env, "tools/list", tok=token(env))
    if st != 200 or not (isinstance(body, dict) and "result" in body):
        raise InfraError(f"control call with the real token returned HTTP {st} without a "
                         "tools/list result; token expired or wrong URL?")


def auth_check(st, body, what):
    """Verdict for tasks 1-2, after control() passed. 401 passes. An accepted call
    (200 with a result) fails. Anything else did not test the boundary: infrastructure."""
    base = f"verifier=http_status; real token -> HTTP 200 (control); {what} -> HTTP {st}"
    if st == 401:
        return {"passed": True, "score": 1.0, "evidence": base + "; expected 401"}
    if st == 200 and isinstance(body, dict) and "result" in body:
        return {"passed": False, "score": 0.0, "evidence": base + ", call accepted; expected 401"}
    raise InfraError(f"{what} -> HTTP {st}: neither refused with 401 nor accepted")


def _parse(raw):
    """A JSON body, or an SSE stream. In SSE, consecutive data: lines form one event,
    joined by newlines and ended by a blank line. Returns the last JSON-RPC message
    (a dict with "result" or "error"), else the last event, else the raw text."""
    lines = raw.splitlines()
    if not any(line.startswith("data:") for line in lines):
        try:
            return json.loads(raw)
        except ValueError:
            return raw
    events, buf = [], []
    for line in lines + [""]:
        if line == "":
            if buf:
                events.append("\n".join(buf))
                buf = []
        elif line.startswith("data:"):
            value = line[5:]
            buf.append(value[1:] if value.startswith(" ") else value)
    parsed = []
    for e in events:
        if e.strip() == "[DONE]":
            continue
        try:
            parsed.append(json.loads(e))
        except ValueError:
            parsed.append(e)
    for msg in reversed(parsed):
        if isinstance(msg, dict) and ("result" in msg or "error" in msg):
            return msg
    return parsed[-1] if parsed else raw
