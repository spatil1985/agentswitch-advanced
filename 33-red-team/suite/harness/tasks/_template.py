"""Template for a new task. Copy it to tNN_<short_name>.py, where NN is the task number
in PLAN.md (for example t11_scope_contract_blocked.py), then fill in run().
Files starting with "_" are not run.

Rules (34-eval-harness/TASK_FORMAT.md section 3, PLAN.md, CONTRIBUTING.md):
- Return {"passed": bool, "score": 0-1 (optional, follows passed if left out), "evidence": str}.
- Decide `passed` from the HTTP / JSON-RPC result or the data, never from what an agent says.
- Build inputs at run time from AGENTSWITCH_TOKEN and the copy. There is no internet and
  no other files, except bug-status.json (use harness.bugs.status).
- If the check cannot be made, raise client.InfraError. The runner reports it as an
  infrastructure failure, not as a pass.
- A refusal check passes only on a real refusal: use client.refused(). An empty 200 is not
  a refusal.
- A task that writes data, or sends a missing or changed token, must set "copy_only": True.
  The runner then runs it only inside a harness run on a copy (AGENTSWITCH_RUN_ID set),
  never against the live systems.
- Put codes and counts in `evidence`. Never the token, and never record contents.
"""
from harness import client


def run(env):
    st, data, is_error = client.tool(env, "Contract.list", {"limit": 5})
    passed = client.refused(st, data, is_error)
    code = client.error_code(data) if is_error else None
    return {"passed": passed, "score": 1.0 if passed else 0.0,
            "evidence": f"verifier=refusal; Contract.list -> HTTP {st}, code={code}"}


TASK = {"id": "rt_example", "title": "Example: a tool our login should not reach is refused",
        "copy_only": False, "run": run}
