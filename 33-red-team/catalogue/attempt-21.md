# Attempt 21 — EmailMessage.get (synthetic id)

1. **Attempt:** Fetch a single email by a fabricated message id (`EmailMessage.get`).
2. **Boundary:** (Permission) Guessing or knowing another user's message id must not return their mail.
3. **Steps:**
   1. `tools/call` `EmailMessage.get` `{id:"00000000-0000-4000-8000-000000000021"}`.
4. **Expected:** `not_found`, empty, or refused. Never another user's message body.
5. **Actual:** Suryodaya only (replay D4): HTTP 200, isError, `data.code=not_found` ("EmailMessage not found."). That answer is expected whether or not isolation holds — a made-up id does not exist here either way (same limitation as attempts 11–13). Keystone not checked.
6. **Result:** Unclear
