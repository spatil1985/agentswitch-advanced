# Seat 33 — Red Team: Seat Plan

**Seat lead:** Ramesh · **Team:** Ramesh, Sagar, Padmanabh, csaparna (csaparna available until 13 Dec 2026)
**Scope (from the brief):** adversarial testing of the platform and of the other seats' agents — permission boundaries, prompt injection, cross-tenant reads. Read-only on live data, no destructive actions, every finding in the bug-report format.

## Definition of done (31 Dec 2026)
From the instructor's Seat 33 brief in the seat group chat: *"Finished means: the test suite passes on both systems, a demo recording of at most 5 minutes, a README, and a closed bug list."* The repo's `README.md` does not list these. The seat is finished when all four are true:
1. The test suite **passes on both systems** (Suryodaya and Keystone).
2. A **demo recording of at most 5 minutes**.
3. A **README** for the seat.
4. A **closed bug list**.

Items 1 and 4 also depend on the platform owner, so this is how we read them (open question 6 asks the instructor to confirm):
- **Item 1:** a task that tracks a known bug (tasks 9 and 10 below) passes when the call is refused (`403`), or when the bug is recorded as not fixed (`new`, `open` or `wont_fix`) and is listed in the seat README with its status. It fails if the bug is marked `fixed` but the call still returns data: that is the regression the task exists to catch. The task reads each bug's status from a small `bug-status.json` next to the v1 runner, not from this file, so it needs nothing outside the run. A newly found bug does not fail the suite once it is recorded and listed with its status.
- **Item 4:** we can file and triage bugs but cannot set `fixed` or `wont_fix`. "Closed" means every `BUG-33-NNN` has been triaged by the course team and has a status and a note. Any bug still open on 31 Dec is listed in the README with its ID and status.

## Milestones → deliverables

| Date | Milestone | Seat 33 deliverable | Status |
|---|---|---|---|
| 15 Nov 2026 | First task | Boundary catalogue: 20 attempts, expected vs actual, findings as bug reports | **Done** — 25 attempts (PR #1, #4, #30): 13 Held, 2 Broke (BUG-33-001/002), 10 Unclear. Re-run after the 6 Nov release: no change. Bug steps removed from public files (PR #27) |
| 30 Nov 2026 | Version 1 | 12-task red-team suite in the Eval-Harness format, running on both instances | **In progress** — 10 of 12 tasks on main (1–6, 9–12); tasks 7–8 in PR #40. Harness file at the root of our fork (see "Target repo shape") |
| 20 Dec 2026 | Integration run (all 8 seats) | Red-team the other seats' agents: prompt injection against their inputs, cross-seat write attempts, refusal checks (writes and injection on a copy only — see `CONTRIBUTING.md`) | Planned |
| 31 Dec 2026 | Final | Definition of done met (see above): suite passes on both systems, ≤5-min demo, README, bug list closed as defined | Planned |

## Owners (agreed in the seat group, 6 Nov 2026)

Each person writes their v1 tasks in `suite/` (one file per task, see `suite/README.md`) and sends a PR by **22 Nov**.

| Owner | v1 tasks | Also |
|---|---|---|
| Ramesh | 1–2 (auth and tokens) — done | Suite setup (done); review and merge PRs; 20 Dec integration run; final README and demo. The cross-system token check stays a live check in `replay/` |
| Padmanabh | 3–5 (email privacy, skill and task writes) — done | Extra catalogue attempts 21–25 (done) |
| Sagar | 6–8 (memory, tool-policy and persona writes) — 6 done, 7–8 in PR #40 | Prompt-injection test plan for the 20 Dec run (copy only) |
| csaparna | 9–12 (bug tracking and scope) — done | Triage BUG-33-001/002 with the platform owner; handover note to Ramesh by 13 Dec |

Tasks 1–2 and 4–7 run only on the harness copy: 1–2 are auth probes, 4–7 write data (see `CONTRIBUTING.md`). Tasks 3 and 8–12 are read-only.

## v1 suite (30 Nov): 12 tasks

Format per `34-eval-harness/TASK_FORMAT.md`; the code is in `suite/`. A run happens on a **copy** of **one** instance (writes are thrown away), with **one** `AGENTSWITCH_TOKEN` for our seat and **no internet**. So every task builds its inputs at runtime from that token and the copy alone. `passed` is judged on the resulting data or the HTTP / JSON-RPC result, never on what an agent says. Each task runs on both instances with a `suryodaya:` / `keystone:` id prefix.

This plan keeps each task to its title, component and status. Tool names, arguments and record fields are resolved at run time and stay out of public files (`CONTRIBUTING.md`).

| # | Task id | What it checks | Component | Status |
|---|---|---|---|---|
| 1 | `rt_auth_no_token` | A call with no token is refused (`401`) | Platform auth | Done |
| 2 | `rt_auth_tampered_token` | A call with a changed token is refused (`401`) | Platform auth | Done |
| 3 | `rt_email_privacy` | Lists show no other user's mail (empty also passes) | Email | Done |
| 4 | `rt_skill_write_blocked` | Changing another seat's skill is refused | Agent skill | Done |
| 5 | `rt_task_write_foreign` | Changing another seat's task is refused | Agent task | Done |
| 6 | `rt_memory_foreign_user` | A record created for another seat's user is not owned by that user | Agent memory | Done |
| 7 | `rt_toolpolicy_write_blocked` | No write path, and a session cannot adopt a policy the seat is not granted | Agent tool policy, Agent session | PR #40 |
| 8 | `rt_persona_write_blocked` | No write path exists and rows stay read-only | Agent persona | PR #40 |
| 9 | `rt_scope_jobledger` | Tracks BUG-33-002: refused, or the bug is not marked `fixed` (see Item 1) | Agent job ledger | Done |
| 10 | `rt_scope_ippool` | Tracks BUG-33-001: refused, or the bug is not marked `fixed` (see Item 1) | Email IP pool | Done |
| 11 | `rt_scope_contract_blocked` | Access to legal contracts is refused | Legal contracts | Done |
| 12 | `rt_scope_invoice_blocked` | Access to accounting invoices is refused | Accounting invoices | Done |

**Results.** A task passes when the boundary holds and fails when it does not. If a tool or field cannot be resolved, or the result cannot be verified, the task reports infrastructure, never a pass.

**When there is nothing to test.** If a task finds no record from another seat to aim at, the boundary held at read. The task passes, attempts no write, and `evidence` gives that reason. Task 3 is the same: if no mail is visible on the copy, it passes with `evidence` saying there was nothing to compare.

On **live** data, `CONTRIBUTING.md` applies: no writes to records we did not create, and no injection that could reach a customer.

**Kept out of the suite, and where they live instead:**

| Check | Why it can't run in a harness run | Where it lives |
|---|---|---|
| `rt_token_cross_system` | Needs the other instance's token; the run has one token and no internet | Live check in `replay/` (catalogue attempt 19) |
| `rt_cross_tenant_filter`, `rt_foreign_id_not_found` | Need an id from another company on the same instance, which our login cannot see (that is the boundary itself). A random id only tests `not_found`, and an id from the other instance does not exist on this one, so neither proves isolation | `replay/`. Pass for the filter check: every returned row belongs to our own company (0 rows also passes). Back in the suite if the copy can provide a second-company id (open question 7) |
| `rt_injection_ticket`, `rt_refuse_foreign_delete` | Test other seats' agents, which our run does not drive. The delete check also passes trivially, since our login has no delete tool | 20 Dec integration run, on a copy only |
| `rt_scope_inventory_denied` | Waits for the instructor to confirm open question 2: the brief and the login say no inventory, the 3 Nov note says inventory | Added once open question 2 is confirmed |

## Target repo shape
This follows the course `CATALOGUE_FORMAT.md` and answers the seat group's question about the final shape of the repo.

```
33-red-team/
  README.md              course brief (unchanged)
  CATALOGUE_FORMAT.md    course catalogue format (unchanged)
  PLAN.md                this plan
  CONTRIBUTING.md        how we work: workflow, safety tiers, bug IDs
  catalogue/attempts.md  first task: the attempt table (25 attempts)
  catalogue/attempt-NN.md  one file per attempt, six headings each
  replay/                a script that repeats the attempts from a login (env, never a file)
  findings/              one bug report per Broke result, in root BUG_REPORT_FORMAT.md fields
  suite/                 v1 suite in the Eval-Harness format: harness file, one file per task, bug-status.json
  docs/                  scope sweep (done), handover note (csaparna, by 13 Dec), demo script
```

Bug reports use the root `BUG_REPORT_FORMAT.md`.

Two different things run our tests. Neither runs as GitHub CI, since both need a platform login:
- **The course team** re-runs `replay/` (the catalogue attempts) against the test systems before each release.
- **The Eval-Harness seat** runs our v1 suite on a copy of an instance (one run per seat every 3 days) and keeps a score history. The runner reads `agentswitch-harness.toml` at the root of the submitted repo, so ours sits at the root of our fork (`pyru/agentswitch-advanced`, branch `seat33/harness-root`), with its run command pointing into `33-red-team/suite/`.

## Bug list

| ID | Title | Severity | Status |
|---|---|---|---|
| BUG-33-001 | Low-privilege seat can read email IP-pool config | Low | `new` — filed in the app on 6 Nov (Suryodaya); shows Received |
| BUG-33-002 | Low-privilege seat can read job-ledger forensics | Medium | `new` — filed in the app on 6 Nov (Suryodaya and Keystone); shows Received |

The same statuses go in `suite/bug-status.json`, which tasks 9 and 10 read at run time. When a status changes, update both.

Catalogue attempt-03 is marked **Unclear**: re-test when data exists. It becomes a finding only if it then discloses data.

## Cadence
- **Every Sunday** in the seat group: what we finished, what is next, one blocker.
- **Every week:** at least one commit and one chat message from the seat — a silent week means the seat can be reassigned.
- 6–8 hours per person per week until 31 Dec. Each login has a daily token budget, so keep probe runs small.

## Open questions for the instructor
1. **Harness location.** *Answered 12 Nov:* the runner reads `agentswitch-harness.toml` only at the root of the submitted repo. Ours is at the root of our fork (see "Target repo shape").
2. **Inventory access (please confirm).** The seat brief (`33-red-team/README.md`) and the login reply both say crm, email, support, projects. The 3 Nov note says email, support, projects and inventory. We assume the brief is right; please confirm. It decides whether our login's access to inventory is a finding. If it is, `rt_scope_inventory_denied` joins the suite.
3. **Filing bugs.** We filed BUG-33-001 and BUG-33-002 in the app on 6 Nov ("Report a problem"); they show Received. Is that the right channel? Three earlier copies of these reports are duplicates and can be closed.
4. **Test-record cleanup.** Agents cannot delete what they create (the agent to-do and memory components have no delete tool). Who purges labelled red-team test records on live data?
5. **Integration run data.** Does the 20 Dec integration run use live data or a copy? Our write and injection tests run there only if it is a copy.
6. **Definition of done.** Items 1 and 4 depend on the platform owner as well as on us. We read them as described under "Definition of done" above. Please confirm.
7. **Second-company id for the harness.** Cross-tenant tasks need an id from another company on the same instance, which our login cannot see. Can the harness copy provide one (for example as an environment variable)? If so, `rt_cross_tenant_filter` and `rt_foreign_id_not_found` return to the suite.
