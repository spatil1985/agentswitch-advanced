# Attempt 24 — AgentSkill.update (foreign owner)

1. **Attempt:** Update another seat's skill (`AgentSkill.update`), echoing the current `name`, after selecting a row whose `user_id` is not ours.
2. **Boundary:** (Permission) Only the owning seat may change that skill; the write must be refused and the record left unchanged.
3. **Steps:** Do **not** send this write from `replay/` (live hosts only). The same check is suite Task 4 — `rt_skill_write_blocked` in `../suite/harness/tasks/t04_skill_write_blocked.py` — which the Eval-Harness runner keeps on the throwaway copy (`copy_only`, Tier 2b).
4. **Expected:** Refused (`tool_not_available` or `permission_denied` / HTTP 403); `updated_at` unchanged. Or no foreign row → pass without writing.
5. **Actual:** Not run in the catalogue replay. Exercised by suite Task 4 on the harness copy (PR #28).
6. **Result:** Unclear — see suite Task 4
