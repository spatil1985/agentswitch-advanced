# Seat 33: Red Team

## Scope
Adversarial testing of the platform and of the other seats' agents: permission boundaries, prompt injection, cross-tenant reads. Read-only on live data, no destructive actions.

## First task
A boundary catalogue: 20 attempts, each with the expected and the actual result, findings in the bug-report format.

## Access
crm, email, support, projects (deliberately low privilege)

## Milestones
- 15 Nov 2026: first task delivered
- 30 Nov 2026: version 1, with a 12-task test suite
- 20 Dec 2026: integration run of all eight seats
- 31 Dec 2026: final

## Working rules
See the top-level README. Put your agent code, tests and notes in this folder; open a pull request for every change.

---

## What this seat delivers

| Deliverable | Location | Status |
|---|---|---|
| Boundary catalogue (25 attempts) | [catalogue/](catalogue/) | Done |
| Findings for Broke results | [findings/](findings/) | BUG-33-001, BUG-33-002 (`new`) |
| Live catalogue replay | [replay/](replay/) | Done (course team re-runs before releases) |
| Scope sweep → suite tasks 11–12 | [docs/scope-sweep.md](docs/scope-sweep.md) | Done |
| 12-task Eval-Harness suite | [suite/](suite/) | 12/12 tasks implemented |
| Seat plan / DoD | [PLAN.md](PLAN.md) | Living doc |

**Team:** Ramesh (lead), Sagar, Padmanabh, csaparna (until 13 Dec 2026).

**Systems:** [Suryodaya](https://agentswitch.theschoolofai.in) and [Keystone](https://class.agentswitch.theschoolofai.in). Identical tool surface; probes are cross-checked on both where noted.

## Folder layout

```
33-red-team/
  README.md                 this file (course brief + seat guide)
  CATALOGUE_FORMAT.md       course catalogue format
  PLAN.md                   milestones, 12-task matrix, open questions
  CONTRIBUTING.md           workflow, credentials, safety tiers
  catalogue/                attempts.md + attempt-01.md … attempt-25.md
  findings/                 BUG-33-NNN.md (public redacted summaries)
  replay/                   boundary probes + scope sweep (env tokens only)
  suite/                    v1 Eval-Harness suite (harness + tasks + tests)
  docs/                     scope-sweep notes (handover / demo later)
```

## Boundary catalogue

Master table: [catalogue/attempts.md](catalogue/attempts.md). Format: [CATALOGUE_FORMAT.md](CATALOGUE_FORMAT.md) (six headings per attempt file).

**Result tally:** 13 Held · 2 Broke · 10 Unclear.

| Theme | Attempts | Notes |
|---|---|---|
| Over-privilege reads | 01–06 | Includes BUG-33-001 / BUG-33-002 |
| Write / privilege escalation | 07–10 | Live writes need approval; 10 Unclear (no mail target) |
| Cross-tenant | 11–13 | Unclear without same-instance foreign ids |
| Email privacy | 14–16, 21–23 | Lists Held; synthetic get/filter Unclear |
| Auth / tokens | 17–19 | No token, malformed, cross-system — Held |
| Injection canary | 20 | Own `AgentTodo`; Held (canary left behind — no delete tool) |
| Suite-deferred writes | 24–25 | Same as suite tasks 4–5; live check on harness copy only |

This repository is public. Attempts 01–03 keep only title, component and status in-repo; steps/evidence stay in the reports filed with the course team / on the harness copy.

## Findings (bug list)

Statuses must stay in step with [suite/bug-status.json](suite/bug-status.json) (read by suite tasks 9–10) and the bug list in [PLAN.md](PLAN.md).

| ID | Title | Severity | Status | Systems |
|---|---|---|---|---|
| [BUG-33-001](findings/BUG-33-001.md) | Low-privilege seat can read email IP-pool config | Low | `new` (filed 6 Nov; Received) | Suryodaya (Keystone: no data → not confirmed there) |
| [BUG-33-002](findings/BUG-33-002.md) | Low-privilege seat can read job-ledger forensics | Medium | `new` (filed 6 Nov; Received) | Suryodaya and Keystone |

Full steps and evidence are **not** in this public repo. Claim the next `BUG-33-NNN` in the PR title when filing a new finding. Format: root [BUG_REPORT_FORMAT.md](../BUG_REPORT_FORMAT.md).

## Replay (live probes)

Stdlib-only. Tokens from the environment — never from a committed file. Details: [replay/README.md](replay/README.md).

```bash
# Login → token (~7 days). Do not commit the token.
curl -s https://agentswitch.theschoolofai.in/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<you>","password":"<pw>"}'
export AGENTSWITCH_SURYODAYA_TOKEN=<token>
export AGENTSWITCH_KEYSTONE_TOKEN=<token>   # optional

cd 33-red-team/replay
python run_boundary_probes.py                 # read-only + auth
PROBE_SYSTEM=keystone python run_boundary_probes.py
RUN_WRITE_PROBES=1 python run_boundary_probes.py   # only after platform-team approval

# Scope sweep (Tier 1; feeds tasks 11–12)
python scope_sweep.py --system suryodaya
python scope_sweep.py --dry-run
```

- Attempts **01–03** are not in the public replay script.
- Attempts **24–25** are suite tasks 4–5 only (not in replay).
- Write/injection probes need `RUN_WRITE_PROBES=1` and human approval first.
- Raw `results.json` is git-ignored; commit only redacted samples (`sample-results.json`, `sample-scope-sweep-results.json`).

## v1 Eval-Harness suite

12-task suite in Eval-Harness format. Details: [suite/README.md](suite/README.md). Task format: [34-eval-harness/TASK_FORMAT.md](../34-eval-harness/TASK_FORMAT.md).

| # | Task id | Owner | Runs on | Status |
|---|---|---|---|---|
| 1 | `rt_auth_no_token` | Ramesh | Harness copy only | Done |
| 2 | `rt_auth_tampered_token` | Ramesh | Harness copy only | Done |
| 3 | `rt_email_privacy` | Padmanabh | Any (read-only) | Done |
| 4 | `rt_skill_write_blocked` | Padmanabh | Harness copy only | Done |
| 5 | `rt_task_write_foreign` | Padmanabh | Harness copy only | Done |
| 6 | `rt_memory_foreign_user` | Sagar | Harness copy only | Done |
| 7 | `rt_toolpolicy_write_blocked` | Sagar | Harness copy only | Done |
| 8 | `rt_persona_write_blocked` | Sagar | Any (read-only) | Done |
| 9 | `rt_scope_jobledger` (BUG-33-002) | csaparna | Any (read-only) | Done |
| 10 | `rt_scope_ippool` (BUG-33-001) | csaparna | Any (read-only) | Done |
| 11 | `rt_scope_contract_blocked` | csaparna | Any (read-only) | Done |
| 12 | `rt_scope_invoice_blocked` | csaparna | Any (read-only) | Done |

Tasks 11–12 were chosen from the scope sweep: both refused on both systems.

```bash
cd 33-red-team/suite
export AGENTSWITCH_BASE_URL=https://agentswitch.theschoolofai.in
export AGENTSWITCH_INSTANCE=suryodaya
export AGENTSWITCH_TOKEN="$AGENTSWITCH_SURYODAYA_TOKEN"
python -m harness.runner --out results.json
python -m unittest discover -s tests -t .    # offline stub tests; no login
```

Local runs execute only non-`copy_only` tasks; copy-only tasks show as `SKIP`. Do **not** set `AGENTSWITCH_RUN_ID` yourself against live hosts — the runner reserves that for Eval-Harness copy runs.

Checks that stay outside the suite (cross-system token, true cross-tenant ids, injection into other seats) live in `replay/` or the 20 Dec integration run — see [PLAN.md](PLAN.md).

## Safety tiers (summary)

Full rules: [CONTRIBUTING.md](CONTRIBUTING.md).

| Tier | What | Rule |
|---|---|---|
| 1 | Read / auth | Run freely |
| 2a | Write to records we created | Platform-team approval on live; prefer idempotent no-ops; label `[redteam-probe <ID>]` |
| 2b | Write to foreign / other-seat records | **Harness copy only** — never live |
| 3 | Deletes, customer-reaching paths, lockout, flood | Never on live; describe as not exercised |

## Definition of done (31 Dec 2026)

From the instructor brief (interpreted in [PLAN.md](PLAN.md)):

1. Test suite passes on both systems (Suryodaya and Keystone).
2. Demo recording ≤ 5 minutes.
3. A README for the seat (this file).
4. Closed bug list — every `BUG-33-NNN` triaged with status and note; any still open on 31 Dec stays listed here with its ID and status.

**Current progress:** catalogue done; suite 12/12; bugs still `new` / Received; demo and final closeout planned.

## Related docs

- [PLAN.md](PLAN.md) — owners, full task pass conditions, open instructor questions
- [CONTRIBUTING.md](CONTRIBUTING.md) — PRs (`seat33/<topic>`), credentials, evidence redaction
- [CATALOGUE_FORMAT.md](CATALOGUE_FORMAT.md) — attempt file shape
- [suite/README.md](suite/README.md) / [replay/README.md](replay/README.md) — how to run
- [docs/scope-sweep.md](docs/scope-sweep.md) — how tasks 11–12 were chosen
- [BUG_REPORT_FORMAT.md](../BUG_REPORT_FORMAT.md) — course bug format
