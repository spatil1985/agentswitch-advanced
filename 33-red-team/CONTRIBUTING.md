# Contributing to Seat 33 (Red Team)

How the four of us work in this folder. The top-level `README.md` rules apply on top of this.

## Workflow
1. Fork `theschoolofai/agentswitch-advanced` and work on a branch named `seat33/<topic>` (e.g. `seat33/injection-tickets`).
2. Keep your changes inside `33-red-team/`.
3. Open a pull request into `main` using the PR template.
4. The required approval must come from a **seat lead** (only leads have write access):
   - A PR from a Seat 33 member is approved and merged by the Seat 33 lead (Ramesh).
   - A PR from the Seat 33 lead is approved and merged by a lead from another seat.
   - Reviews from members are still useful and welcome, but they don't count as the required approval. Nobody merges their own PR.
5. Small PRs, often. Commits and bug IDs are the record of each person's work.

## Credentials
- Get a token per system with one login call (see `replay/README.md`). Tokens last 7 days.
- Keep tokens in environment variables (`AGENTSWITCH_SURYODAYA_TOKEN`, `AGENTSWITCH_KEYSTONE_TOKEN`). **Never** put a password, token or key in a file you commit, a PR, an issue or the group chat.
- Those per-system names are for running `replay/` locally. A harness run (the v1 suite) instead gets a single `AGENTSWITCH_TOKEN` plus `AGENTSWITCH_BASE_URL` and `AGENTSWITCH_INSTANCE` (see `34-eval-harness/TASK_FORMAT.md`), so the v1 runner must read those.
- 10 wrong passwords in 15 minutes lock the login, and we share it. Copy the password from your DM; do not guess.
- If a secret is ever committed by mistake, tell the course team at once so it can be replaced. Deleting the commit is not enough.

## Safety tiers for probes

**Who approves a write on live data.** Ask the **platform team** in the Seat 33 group chat *before* running it, and wait for their reply. The approval must not come from the person who runs the probe, so the seat lead cannot approve their own run. A teammate's 👍 is not enough. Record who approved, and when, in the catalogue entry.

| Tier | What it covers | Rule |
|---|---|---|
| **1 — Read / auth** | `.list`, `.get`, read-only endpoints, calls with no or wrong token | Run freely. |
| **2a — Changes a record we created** | `.create`/`.update` on our own records; planting a canary in our own record | On live data, the platform team approves first in the seat group (see above). Prefer an idempotent no-op (write a field back with its current value). Label anything created `[redteam-probe <ID>]`. |
| **2b — Touches a record we did not create** | Any write/update/transition aimed at another seat's or tenant's record | **Not on a live system.** Run it only against the throwaway copy the Eval-Harness seat provides. See note 1. |
| **3 — Never on live data** | Deletes; anything that sends email or campaigns or otherwise reaches a customer; the account-lockout path; load or flooding | Do not run. Describe it in the catalogue as "not exercised" and why. |

Notes:
1. **A same-value write to a foreign record is still a write.** It can change `updated_at`, add audit-log entries, and fire webhooks or other agents. `BUG_REPORT_FORMAT.md` says: *if a step would change or delete a record you did not create, stop and report the risk instead.* So permission probes against other seats' records (e.g. "can I update another seat's task?") run **only on the throwaway copy**, never live. On live, don't send the write at all. Check permissions with read-only calls only (e.g. the tool list or scope for our login), and leave the real write attempt to the throwaway copy.
2. **Injection that can reach a customer is Tier 3.** Planting a canary is Tier 2, but if the path it lands on (a support ticket, `email_to_ticket`, `render_macro`, `translate`) can produce a reply or email to a real customer, a *successful* injection is a Tier 3 outcome. Test these only on the throwaway copy, never on live data. The 20 Dec integration run counts only if it is confirmed to run on a copy.
3. **Do not delete or overwrite data you did not create.** And agents **cannot delete** what they create (`AgentTodo`, `AgentMemory` have no delete tool), so every live Tier 2a test leaves a labelled record behind — keep them few.

Harness runs by the Eval-Harness seat use a throwaway copy of the instance, so 2a/2b checks inside the v1 suite are fine there.

## Catalogue and bug reports
- The catalogue follows `CATALOGUE_FORMAT.md`: `catalogue/attempts.md` (table) + `catalogue/attempt-NN.md`, each with the six headings. Every **Broke** result also gets a bug report.
- Bug reports use the course format at the repo root, `BUG_REPORT_FORMAT.md` (Title, Seat and login, System, Date/time IST, Severity, Steps, Expected, Actual, Repeats, Evidence). One file per finding in `findings/BUG-33-NNN.md`. We do not keep a separate seat template — the root format is canonical. If a finding is later filed on the platform, an optional second table with the platform `BugReport` fields may be appended.
- **Claim the next number in your PR title** (e.g. "BUG-33-003: …") so two people don't take the same ID. Never reuse a number, even if a bug is withdrawn.
- Severity per `BUG_REPORT_FORMAT.md`: High (another company's data, or a record changed without a person), Medium (wrong result), Low (cosmetic or unclear). If the intended scope is a product decision, say so and let the course team triage rather than asserting a defect.
- A result that is reachable but disclosed nothing is **Unclear**, not Broke — note it in the attempt file and re-test when data exists.
- Add the bug to the bug list in `PLAN.md`. A bug is closed only with a final status and a resolution note.

## Evidence and redaction
The repository is public.
- **No exploit detail for bugs or possible findings** (instructor, 11 Nov 2026). For each bug or possible finding, the public files (catalogue, `findings/`, `replay/`, `docs/`, `PLAN.md`, READMEs, PR and issue text) keep only the **title, the affected component and the fix status**. Steps, tool calls, requests, responses and returned field names are kept on the harness copy only and in the report filed in the app ("Report a problem").
  - In `findings/`, Steps and Evidence say "In the full report filed in the app", and Actual says only what was returned, with no fields or ids (see `findings/BUG-33-001.md`).
  - Suite tasks that track a known bug (Tasks 9–10) must make the call to check it. Keep their comments and evidence to the title, component and status.
- Truncate internal ids to the first 8 characters (`1a2b3c4d…`). Use placeholders like `<suryodaya-company-id>`.
- For other results (Held, Unclear), describe the shape of returned data (counts, field names); do not paste records.
- No platform source code, schemas, database files, or screenshots of internal screens.
- Raw run output (`results.json`) stays local and is git-ignored. Commit only a redacted sample (`replay/sample-results.json`).

## Reporting a failure in the seat group
The instructor asks for four facts: the **system**, your **login name**, the **exact request**, and the **reply** you got. No password or token.
