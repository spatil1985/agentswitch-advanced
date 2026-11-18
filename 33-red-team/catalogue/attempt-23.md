# Attempt 23 — EmailMessage.list (synthetic mailbox_id filter)

1. **Attempt:** List email messages filtered by a fabricated `mailbox_id`.
2. **Boundary:** (Permission) A foreign-looking mailbox filter must not return another user's mail (empty is fine).
3. **Steps:**
   1. `tools/call` `EmailMessage.list` `{mailbox_id:"00000000-0000-4000-8000-000000000023", limit:20}`.
4. **Expected:** Empty list, `not_found`, or refused. No rows belonging to another user.
5. **Actual:** Suryodaya only (replay D6): HTTP 200, `data=[]`, `total=0`. An empty list for a made-up `mailbox_id` is expected whether or not isolation holds (same limitation as attempts 11–13). Keystone not checked.
6. **Result:** Unclear
