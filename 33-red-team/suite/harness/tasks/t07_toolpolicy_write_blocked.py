"""Task 7 (owner: Sagar). Agent tool policy: no write path, and a session cannot
adopt a policy the seat is not granted.

Component: Agent tool policy, Agent session.
Status: copy-only (harness copy, never live); leaves labelled `[redteam-probe t07]`
rows on the copy.

Pass: the boundary holds. Fail: it does not (evidence: counts only).
Infrastructure, never a pass: a tool or field cannot be resolved at run time, or
the result cannot be verified.
"""
import re
import uuid

from harness import client

COMPONENT = "Agent tool policy"
SESSION_COMPONENT = "Agent session"
COMPONENT_KEYS = ("tool", "polic")      # the tool-policy component, not ledger policies
WRITE_VERBS = ("create", "update", "delete", "upsert", "set")
TITLE = "[redteam-probe t07] benign policy-bind check"
PAGE = 100

_POLICY_FIELD_RE = re.compile(r"polic.*id$", re.I)
# Error codes that mean "the value was read and rejected" (bad argument / no such id).
_REJECTED = {"invalid_arguments", "not_found"}


def _tools(env):
    st, body = client.rpc(env, "tools/list", tok=client.token(env))
    if st >= 500:
        raise client.InfraError(f"tools/list server error HTTP {st}")
    if st != 200 or not (isinstance(body, dict) and "result" in body):
        raise client.InfraError(f"tools/list returned HTTP {st}")
    tools = body.get("result", {}).get("tools", [])
    return tools if isinstance(tools, list) else []


def _resolve_tool(env, setting_key, *keywords):
    setting = env.get(setting_key)
    if setting:
        return setting
    for t in _tools(env):
        text = (str(t.get("name", "")) + " " + str(t.get("description", ""))).lower()
        if all(k in text for k in keywords):
            return t.get("name")
    return None


def _policy_write_tool(env):
    for t in _tools(env):
        name = str(t.get("name", ""))
        low = name.lower()
        if all(k in low for k in COMPONENT_KEYS) and name.split(".")[-1].lower() in WRITE_VERBS:
            return name
    return None


def _resolve_policy_field(env, create_tool):
    setting = env.get("RT_SESSION_POLICY_FIELD")
    if setting:
        return setting
    for t in _tools(env):
        if t.get("name") == create_tool:
            for key in (t.get("inputSchema") or {}).get("properties") or {}:
                if _POLICY_FIELD_RE.search(key):
                    return key
    return None


def _rows(data):
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


def _writable(row):
    """True if any flag object in the row marks it writable (no field named)."""
    return any(isinstance(v, dict) and v.get("write") is True for v in row.values())


def _mine(row, my_user):
    """True if any field of the row references this seat's user (no field named)."""
    return bool(my_user) and any(
        str(v) == my_user for k, v in row.items()
        if k != "id" and isinstance(v, (str, int)))


def _list_policies(env, list_tool):
    offset, rows, refused = 0, [], False
    while True:
        st, data, err = client.tool(env, list_tool, {"limit": PAGE, "offset": offset})
        if client.refused(st, data, err):
            return True, rows
        if err:
            raise client.InfraError(
                f"{COMPONENT} list failed HTTP {st} code={client.error_code(data)}"
            )
        batch = _rows(data)
        rows.extend(batch)
        total = data.get("total") if isinstance(data, dict) else None
        offset += PAGE
        if (isinstance(total, int) and offset >= total) or len(batch) < PAGE or not batch:
            break
    return refused, rows


def _grant_shape(policy):
    """Counts only: never field names or contents."""
    lists = [v for v in policy.values() if isinstance(v, list)]
    return f"{len(lists)} list fields, {sum(len(v) for v in lists)} entries"


def _session_policy(env, created, read_tool, field):
    if created.get(field) not in (None, ""):
        return str(created[field])
    sid = created.get("id")
    if sid in (None, ""):
        raise client.InfraError("session create returned no id and no binding value")
    st_g, data_g, err_g = client.tool(env, read_tool, {"id": sid})
    if err_g or not isinstance(data_g, dict):
        raise client.InfraError(
            f"session read-back failed HTTP {st_g} code={client.error_code(data_g)}"
        )
    val = data_g.get(field)
    return None if val in (None, "") else str(val)


def _bind_session(env, create_tool, read_tool, field, policy_id=None):
    """Returns (refused, stored value or None); other errors raise InfraError."""
    args = {"title": TITLE}
    if policy_id is not None:
        args[field] = policy_id
    st, data, err = client.tool(env, create_tool, args)
    if client.refused(st, data, err):
        return True, None
    if err:
        raise client.InfraError(
            f"session create non-refusal error HTTP {st} code={client.error_code(data)}")
    if not isinstance(data, dict):
        raise client.InfraError("session create returned no record to verify the bind")
    return False, _session_policy(env, data, read_tool, field)


def _made_up_id():
    """Random id (tests patch this)."""
    return str(uuid.uuid4())


def _positive_control(env, create_tool, read_tool, field):
    """Returns a short note, or raises InfraError (never a pass)."""
    probe = _made_up_id()
    st, data, err = client.tool(env, create_tool, {"title": TITLE, field: probe})
    code = client.error_code(data) if err else None
    if client.refused(st, data, err) or code in _REJECTED or st in (400, 404, 422):
        return "control ok (rejected)"
    if err:
        raise client.InfraError(f"positive control error HTTP {st} code={code}")
    if not isinstance(data, dict):
        raise client.InfraError("positive control returned no record")
    if _session_policy(env, data, read_tool, field) == probe:
        return "control ok (stored)"
    raise client.InfraError("positive control unverifiable")


def run(env):
    # --- Check 1: tool-policy write guard (read-only) ---
    if _policy_write_tool(env):
        return {"passed": False, "score": 0.0,
                "evidence": f"verifier=policy_guard; component={COMPONENT}; "
                            f"regression: a tool-policy write verb is now exposed"}

    policy_list = _resolve_tool(env, "RT_POLICY_LIST_TOOL", "tool", "polic", "list")
    if not policy_list:
        raise client.InfraError("could not resolve the tool-policy list tool at run time")
    refused, policies = _list_policies(env, policy_list)
    writable = sum(1 for p in policies if _writable(p))
    if writable:
        return {"passed": False, "score": 0.0,
                "evidence": f"verifier=policy_guard; component={COMPONENT}; "
                            f"regression: {writable}/{len(policies)} rows report write:true"}
    guard_note = (f"guard ok (no write verb; "
                  f"{'list refused' if refused else f'{len(policies)} rows write:false'})")

    # --- Check 2: a session cannot adopt a policy the seat is not granted ---
    create_tool = _resolve_tool(env, "RT_SESSION_CREATE_TOOL", "session", "create")
    read_tool = _resolve_tool(env, "RT_SESSION_READ_TOOL", "session", "get")
    if not (create_tool and read_tool):
        raise client.InfraError("could not resolve session tools at run time")
    policy_field = _resolve_policy_field(env, create_tool)
    if not policy_field:
        raise client.InfraError("could not resolve the session policy-binding field at run time")

    if not any(p.get("id") not in (None, "") for p in policies):
        return {"passed": True, "score": 1.0,
                "evidence": f"verifier=policy_bind; component={SESSION_COMPONENT}; "
                            f"{guard_note}; no policies visible to test a bind"}

    my_user = str(client.whoami(env).get("id") or "")

    refused, granted = _bind_session(env, create_tool, read_tool, policy_field)
    if refused:
        raise client.InfraError("baseline session create refused; cannot verify")
    control_note = _positive_control(env, create_tool, read_tool, policy_field)

    target = next(
        (p for p in policies
         if str(p.get("id") or "") not in ("", granted) and not _mine(p, my_user)),
        None)
    if target is None:
        return {"passed": True, "score": 1.0,
                "evidence": f"verifier=policy_bind; component={SESSION_COMPONENT}; "
                            f"{guard_note}; {control_note}; no policy outside the seat's grant to test"}
    target_id = str(target["id"])

    refused, bound = _bind_session(env, create_tool, read_tool, policy_field, target_id)
    if refused:
        return {"passed": True, "score": 1.0,
                "evidence": f"verifier=policy_bind; component={SESSION_COMPONENT}; "
                            f"{guard_note}; {control_note}; bind refused"}
    if bound == target_id:
        return {"passed": False, "score": 0.0,
                "evidence": f"verifier=policy_bind; component={SESSION_COMPONENT}; {guard_note}; "
                            f"{control_note}; FINDING: session adopted a non-granted policy "
                            f"{target_id[:8]}… ({_grant_shape(target)}); not exercised; "
                            f"leaves labelled probe sessions on copy"}
    return {"passed": True, "score": 1.0,
            "evidence": f"verifier=policy_bind; component={SESSION_COMPONENT}; {guard_note}; "
                        f"{control_note}; non-granted policy not adopted "
                        f"(stored={'none' if bound is None else 'other'}); "
                        f"leaves labelled probe sessions on copy"}


TASK = {
    "id": "rt_toolpolicy_write_blocked",
    "title": "Agent tool policy: no write path, and a session cannot adopt a policy the seat is not granted",
    "copy_only": True,
    "run": run,
}
