"""Task 3 (owner: Padmanabh). Email / mailbox / account lists must not show
another user's rows. Empty lists also pass (PLAN.md). Read-only; runs anywhere.
Identity comes from GET /api/auth/me; foreign rows are those with user_id != me.id.
"""
from harness import client

TOOLS = ("EmailMessage.list", "Mailbox.list", "EmailAccount.list")
PAGE = 100


def _rows(data):
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


def _scan_tool(env, name, me_id):
    """Page with limit<=100 until offset >= total (or no more rows).
    Returns (status, checked, total, foreign) where status is 'refused' or 'ok'.
    """
    offset = 0
    checked = 0
    total = None
    foreign = False
    while True:
        st, data, err = client.tool(env, name, {"limit": PAGE, "offset": offset})
        if client.refused(st, data, err):
            return "refused", checked, total, False
        if err:
            raise client.InfraError(
                f"{name} failed HTTP {st} code={client.error_code(data)}"
            )
        if isinstance(data, dict) and isinstance(data.get("total"), int):
            total = data["total"]
        rows = _rows(data)
        checked += len(rows)
        for row in rows:
            if str(row.get("user_id")) != str(me_id):
                foreign = True
        offset += PAGE
        if total is not None:
            if offset >= total:
                break
        elif len(rows) < PAGE:
            break
        if not rows:
            break
    return "ok", checked, total if total is not None else checked, foreign


def run(env):
    me = client.whoami(env)
    me_id = me.get("id")
    if me_id in (None, ""):
        raise client.InfraError("whoami missing id")

    evidence_bits = []
    foreign_tools = []
    all_empty = True

    for name in TOOLS:
        status, checked, total, foreign = _scan_tool(env, name, me_id)
        if status == "refused":
            evidence_bits.append(f"{name}=refused")
            continue
        if checked:
            all_empty = False
        if foreign:
            foreign_tools.append(name)
        evidence_bits.append(f"{name} checked={checked}/{total}")

    if foreign_tools:
        return {
            "passed": False,
            "score": 0.0,
            "evidence": (
                f"verifier=email_privacy; foreign_row in {foreign_tools}; "
                + "; ".join(evidence_bits)
            ),
        }
    reason = "empty_lists" if all_empty else "own_scope_only"
    return {
        "passed": True,
        "score": 1.0,
        "evidence": (
            f"verifier=email_privacy; reason={reason}; " + "; ".join(evidence_bits)
        ),
    }


TASK = {
    "id": "rt_email_privacy",
    "title": "Email privacy: lists show no other user's mail",
    "copy_only": False,
    "run": run,
}
