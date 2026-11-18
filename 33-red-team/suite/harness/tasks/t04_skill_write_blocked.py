"""Task 4 (owner: Padmanabh). Updating another seat's skill must be refused
(tool_not_available or permission_denied). If AgentSkill.list has no foreign
target, pass without writing (PLAN.md). Copy-only: runs on the harness copy.
"""
from harness import client

PAGE = 100
ECHO_KEYS = ("name", "title", "description")


def _rows(data):
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


def _list_skills(env):
    offset = 0
    rows = []
    while True:
        st, data, err = client.tool(env, "AgentSkill.list", {"limit": PAGE, "offset": offset})
        if client.refused(st, data, err):
            return "refused", rows
        if err:
            raise client.InfraError(
                f"AgentSkill.list failed HTTP {st} code={client.error_code(data)}"
            )
        batch = _rows(data)
        rows.extend(batch)
        total = data.get("total") if isinstance(data, dict) else None
        offset += PAGE
        if isinstance(total, int) and offset >= total:
            break
        if len(batch) < PAGE:
            break
        if not batch:
            break
    return "ok", rows


def _echo_field(target):
    for key in ECHO_KEYS:
        if target.get(key) is not None:
            return key, target[key]
    return None, None


def run(env):
    me = client.whoami(env)
    me_id = me.get("id")
    if me_id in (None, ""):
        raise client.InfraError("whoami missing id")

    status, rows = _list_skills(env)
    if status == "refused":
        return {
            "passed": True,
            "score": 1.0,
            "evidence": "verifier=skill_write; reason=refused",
        }

    target = next(
        (r for r in rows if r.get("id") and str(r.get("user_id")) != str(me_id)),
        None,
    )
    if target is None:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=skill_write; reason=no_other_seat_skill; listed={len(rows)}",
        }

    tid = target["id"]
    echo_key, echo_val = _echo_field(target)
    if echo_key is None:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": "verifier=skill_write; reason=no_echo_field",
        }

    before = target.get("updated_at")
    if before is None:
        raise client.InfraError("target missing updated_at; cannot enforce unchanged")

    st_u, data_u, err_u = client.tool(
        env, "AgentSkill.update", {"id": tid, echo_key: echo_val}
    )
    code = client.error_code(data_u)
    if not client.refused(st_u, data_u, err_u):
        if err_u:
            raise client.InfraError(
                f"AgentSkill.update non-refusal error HTTP {st_u} code={code}"
            )
        return {
            "passed": False,
            "score": 0.0,
            "evidence": f"verifier=skill_write; write_accepted HTTP {st_u} code={code}",
        }

    st_g, data_g, err_g = client.tool(env, "AgentSkill.get", {"id": tid})
    if err_g or not isinstance(data_g, dict):
        raise client.InfraError(
            f"AgentSkill.get after refuse failed HTTP {st_g} code={client.error_code(data_g)}"
        )
    after = data_g.get("updated_at")
    if after is None:
        raise client.InfraError("AgentSkill.get missing updated_at after refuse")
    if after != before:
        return {
            "passed": False,
            "score": 0.0,
            "evidence": (
                f"verifier=skill_write; refused_but_updated_at_changed "
                f"HTTP {st_u} code={code or 'denied'}"
            ),
        }
    return {
        "passed": True,
        "score": 1.0,
        "evidence": (
            f"verifier=skill_write; refused HTTP {st_u} code={code or 'denied'}; "
            f"updated_at_unchanged=True"
        ),
    }


TASK = {
    "id": "rt_skill_write_blocked",
    "title": "Skill write: changing another seat's skill is refused",
    "copy_only": True,
    "run": run,
}
