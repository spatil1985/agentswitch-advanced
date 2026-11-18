# Attempt 25 — AgentTask.update (foreign owner)

1. **Attempt:** Update another seat's task (`AgentTask.update`), echoing one current scalar (`title` / `name` / `description`), after selecting a row whose `user_id` is not ours.
2. **Boundary:** (Permission) Foreign task writes must be refused; `updated_at` must not change.
3. **Steps:** Do **not** send this write from `replay/` (live hosts only). The same check is suite Task 5 — `rt_task_write_foreign` in `../suite/harness/tasks/t05_task_write_foreign.py` — which the Eval-Harness runner keeps on the throwaway copy (`copy_only`, Tier 2b).
4. **Expected:** Refused (`permission_denied` preferred; `tool_not_available` also holds the write); `updated_at` unchanged. Or no foreign row → pass without writing.
5. **Actual:** Not run in the catalogue replay. Exercised by suite Task 5 on the harness copy (PR #28).
6. **Result:** Unclear — see suite Task 5
