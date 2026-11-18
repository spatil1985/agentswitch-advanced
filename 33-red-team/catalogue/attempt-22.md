# Attempt 22 — Mailbox.get (synthetic id)

1. **Attempt:** Fetch a mailbox by a fabricated mailbox id (`Mailbox.get`).
2. **Boundary:** (Permission) A synthetic or foreign mailbox id must not disclose another user's mailbox.
3. **Steps:**
   1. `tools/call` `Mailbox.get` `{id:"00000000-0000-4000-8000-000000000022"}`.
4. **Expected:** `not_found`, empty, or refused. Never another user's mailbox metadata beyond a refusal.
5. **Actual:** Suryodaya only (replay D5): HTTP 200, isError, `data.code=not_found` ("Mailbox not found."). A made-up id returns not_found whether or not isolation holds (same limitation as attempts 11–13). Keystone not checked.
6. **Result:** Unclear
