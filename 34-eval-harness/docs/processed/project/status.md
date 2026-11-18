# Status and handoff log

> Newest entry first. Every work session (person or agent) ends by adding an entry here. A new session reads the top entry first, so it can carry on without old chat history.

Entry format: date · who · what changed · what's next · blockers. Keep entries free of platform detail (tool names, counts, record data). Those belong in the local platform notes.

---

## 2026-11-11 · Krishna
**What changed**
- **Abhinav's review of PR #21 (S34-19)**, all 4 comments checked:
  - **Time limit with child processes (real bug, fixed).** A 1 s limit took 6 s when the agent was a wrapper whose child kept the output open. The agent now runs in its own process group, the whole group is stopped on time-out, and the last read is bounded.
  - **Token in `results.json` (real bug, fixed).** A token printed by a failing agent reached the evidence text. Each trial record is now scrubbed once, before it is saved and scored, so `results.json` and the saved record match and a rescore gives the same row.
  - **Environment allowlist:** already done on 10 Nov.
  - **Paging in the "no writes" check:** fair but not urgent (our login has almost no writes). Moved to new card S34-34.
  - Two new run-path tests; 23 tests pass.
- **Checked the team's chat claims** against the seat 31 and 35 channels, their pull requests and our 10 Nov schema dumps:
  - **Seat 35, for 15 Nov:** writes nothing, and the instructor scores their pairs file directly. The platform has no proposal entity. For version 1 the instructor recommends approval requests.
  - **Seat 31:** the mailbox bug was fixed on 10 Nov. Their drafts are still out of our reach, because email is private and a harness run gives the agent our token.
  - **Test data:** the instructor said there are no planted answers, and a harness run writes to a copy.
- **Board:** S34-07 is Abhinav's and S34-08 is Ranjani's. S34-20 is Abhinav's and blocked. S34-21 moved to version 1. S34-34 added. Risks 2, 3, 9 and Q6 updated.

**What's next**
1. Krishna: commit and push the fixes, reply on the #21 threads, and re-request review. Post the chat replies.
2. Abhinav: S34-07 (seat 31 tasks) with the existing graders. Ask the instructor to confirm the 15 Nov plan for both seats.
3. Ranjani: S34-08 (seat 35 tasks) in `suites/seat35/suite.toml`. Agree the agent command with seat 35.

**Blockers:** Q1 (harness file location) and Q2 (how to start seat agents) are unanswered. The instructor's confirmation of our 15 Nov plan is pending. Invoices and received payments wait for the next deploy.

---

## 2026-11-10 · Krishna
**What changed**
- **The instructor's review of PR #21 (S34-19), both points done:**
  - **Harness mode uses only the given token and URLs.** The agent now gets an allowlist of environment variables (the contract variables plus a few operating-system basics), so no password or other key can reach it. The sample agent passes the given model endpoint explicitly and refuses to start without it. The local launcher no longer passes the login settings to the harness. A table in [harness-design.md](../evaluation/harness-design.md) ("Harness mode") lists what a run uses.
  - **Run-path tests:** `tests/test_run_path.py` uses a small fake platform and a fake agent process. It covers:
    - a passing run, with no secrets saved;
    - the method, host and token of every request;
    - no password reaching the agent;
    - a dead token, an agent crash, a time-out, missing model settings and a failed read, each giving infrastructure rows;
    - `results.json` written even when settings are missing;
    - `.env` ignored.

    A guard fails any test in which the harness opens a connection. The tests also found that the run summary line could crash (and wipe the finished rows) when runs are saved outside the seat folder. That is fixed.
- **Read access re-checked live** (both systems, fresh login, read-only GETs). Sales orders, items, parties and payments are readable now. Quotations, invoices, received payments and the audit trail are still refused. Updated: [risks.md](risks.md) row 1 and Q3, the known gaps in harness-design.md, and bug draft BUG-34-003 (narrowed). The probe now also covers quotations and the audit trail.
- **Checks:** ruff, mypy, lint-imports and pytest pass (21 tests). The plumbing task still passes live on both systems, with no secrets in the run files.

**What's next**
1. Krishna: commit and push, reply on #21, and re-request review. Ask Abhinav to submit his pending review comments.
2. Abhinav (proposed): S34-07 (seat 31 suite), then S34-20 (expected-change grader), for 15 Nov.
3. Krishna: post the follow-up to the instructor (Q1, Q2, quotations and the audit trail) if there's still no reply.

**Blockers:** Q1 (harness file location) and Q2 (how to start seat agents) are unanswered. Invoices and received payments wait for the next platform deploy.

---

## 2026-11-08 (later) · Krishna
**What changed**
- **Reviewed Ranjani's early harness PR (#12)** against course session 18, Anthropic's eval guide and our rules. Decision: close it in favour of #21. Its main gaps:
  - stubs reported as failures, not "unevaluated";
  - no agent driver;
  - no before/after snapshot and no saved trial record;
  - a verifier that could write;
  - tasks outside seats 31 and 35's scope.
- **Kept from #12.** Its 12 task titles are now the starting point for S34-07 and S34-08, reshaped to each seat's first task.
- **Checked our own harness against the same rules.** We found three gaps, now backlog cards:
  - S34-31: a grading crash in one task loses the finished rows;
  - S34-32: tasks not reached before the time limit are missing from `results.json`;
  - S34-33: the evidence text doesn't match TASK_FORMAT or our principles page.

**What's next**
1. Krishna: post the review on #12 and close it, comment on #21, and message Ranjani.
2. The team: agree owners for S34-31 to S34-33. S34-31 and S34-32 should land before the 12-task suites run (S34-27).

**Blockers:** unchanged.

---

## 2026-11-08 · Krishna
**What changed**
- **Checked live again on both systems:**
  - the plumbing task still passes end to end (`outcome=approve`, `integrity=clean`);
  - rescoring gives identical rows;
  - no secrets appear in the run files.
- **Abhinav's access findings confirmed.** Our login still cannot read the sales, accounting and audit-trail data that seats 31 and 35 work on. [risks.md](risks.md) rows 1 and 5 and questions Q2 and Q3 are updated, and bug draft BUG-34-003 is written.
- **The instructor's answer on logins (7 Nov):** a run gives our harness seat 34's token. Still open: how our harness should start the seats' own agents (Q2).
- **New backlog cards S34-20 to S34-30** on the [board](board.md), for parts found missing. S34-20 to S34-26: two kinds of check, a driver for agents that work under their own login, a "no writes" check that also watches the agent's login, a cost count on our side, task ordering, and the demo recording. S34-27 to S34-30: the dry run and first official run, the final README, the integration run, and closing the bug list.
- **Board rule: never delete a card.** S34-04, S34-05, S34-06 and S34-09 are back on the board, under Review, marked as built inside S34-19. Every number from S34-01 to S34-30 now appears exactly once.
- **[harness-design.md](../evaluation/harness-design.md)** sections brought up to date, with the three kinds of check and the known gaps. `AGENTS.md` has two new rules: add a backlog card when something is missing, and keep doc sections current.
- **Wording:** status entries now name people by first name.

**What's next**
1. Krishna: commit the scaffold and these docs on branch `seat34/eval-harness-scaffold`, and open the pull request. Ask Ranjani or Abhinav to review it.
2. Krishna: post the message about how a harness run works (Q2, Q3) in the seat group. Verify BUG-34-003 and file it if the course team wants it filed.
3. The team: agree owners for S34-07, S34-08 and S34-20 to S34-30.

**Blockers:** risks 1 and 5 (read access; how to start another seat's agent), and Q1 for official runs.

---

## 2026-11-07 (evening) · Krishna
**What changed**
- **The eval-harness scaffold (S34-19):**
  - `eval_harness/` (settings, a REST reader, suite, trial, graders, scorer, results, rescore);
  - `agents_under_test/sample/` (an openai SDK + MCP stand-in agent, read-only);
  - `suites/example/` (one plumbing task, `graded = false`);
  - `agentswitch-harness.toml`.
- **Local runs.** `scripts/run_local.py` is the launcher, and `scripts/local_auth.py` holds the token cache. The probe and sync scripts use the same cache now.
- **Checked live on both systems:**
  - the plumbing task passes (`outcome=approve`, `integrity=clean`, `honesty=honest_refusal`);
  - a bad model and a dead token each give a clear `infrastructure:` row;
  - rescoring reproduces the rows with zero model calls;
  - no secrets appear in any run file.
- **Docs:**
  - [harness-design.md](../evaluation/harness-design.md) rewritten;
  - new [agent-contract.md](../evaluation/agent-contract.md) and [how-to-run.md](../evaluation/how-to-run.md);
  - decisions 0007–0010;
  - glossary terms.

**What's next**
1. Krishna: commit the scaffold on its own branch (see the handover), open the pull request, and ask a teammate to review it.
2. Open M0 items: instructor questions Q1–Q6; seats 31 and 35 (where results land, plus the [agent contract](../evaluation/agent-contract.md)); team meeting; checking the bug drafts.
3. People write the first real tasks for seats 31 and 35 (S34-07, S34-08).

**Blockers:** unchanged (risks 1 and 2; Q1 blocks official runs).

---

## 2026-11-07 · Krishna
**What changed**
- **Seat foundations:**
  - `.gitignore` keeps raw notes, platform data, local platform notes, full bug reports, run output, `.env` and personal files out of git;
  - a uv project (`pyproject.toml`, `uv.lock`: Python 3.11, mcp, httpx2, pydantic, ruff, mypy, pytest);
  - `AGENTS.md` and `CLAUDE.md`.
- **Platform scripts:**
  - `scripts/probe_access.py`: a read-only live access check;
  - `scripts/platform_sync.py`: re-reads the platform after a release and reports what changed.
- **Docs:**
  - this wiki, the plan, the board, risks and decision records;
  - the bug workflow and template in [../../bugs/](../../bugs/README.md).
- **Live findings that corrected earlier beliefs** (details in the local platform notes):
  - our tool list is not empty;
  - the knowledge base is reachable;
  - sales, accounting and item data are not readable by our login.

**What's next**
1. Krishna: create `.env.example` and add the two address lines to `.env` (see `AGENTS.md`). Then commit on branch `seat34/foundations` in the fork, and open the pull request.
2. Krishna: post instructor questions Q1–Q6 from [risks.md](risks.md), and talk with seats 31 and 35 about where their results land (risk 2).
3. Krishna: verify the seed bug drafts and file the real ones (S34-17).
4. Krishna: share this plan with Ranjani and Abhinav, and meet to agree who looks after what. Every owner in the docs is a proposal until then.
5. Then the M1 cards, S34-04 to S34-09, on the [board](board.md).

**Blockers**
- Risk 1: some data our checks need is not readable.
- Risk 2: seat results are not on the platform.
- Q1: where the harness file may live. No official run can be submitted until it is answered.
