"""Task 11 (owner: csaparna). Component: Legal contracts.
Boundary check verifying access to Contract.list is refused.

Read-only: one tool call.
Passes only on a verified refusal (tool_not_available, permission_denied,
or HTTP 403). An empty 200 is not a refusal.
"""
from harness import client


def run(env):
    st, data, is_error = client.tool(env, "Contract.list", {"limit": 5})
    if st >= 500:
        raise client.InfraError(f"server error HTTP {st}")

    passed = client.refused(st, data, is_error)
    code = client.error_code(data) if is_error else None

    if passed:
        evidence = f"verifier=refusal; Contract.list refused -> HTTP {st}, code={code}"
    else:
        evidence = f"verifier=refusal; Contract.list -> HTTP {st}, call was not refused (expected tool_not_available or permission_denied)"

    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "evidence": evidence,
    }


TASK = {
    "id": "rt_scope_contract_blocked",
    "title": "Access to legal contracts (Contract.list) is refused",
    "copy_only": False,
    "run": run,
}
