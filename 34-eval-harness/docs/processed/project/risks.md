# Risks, blockers and open questions

> Everything that could stop us, with an owner and a status. We review it every Sunday. A blocker is written here only after it has been checked live. Exact requests and replies stay in the local platform notes (`docs/processed/platform/access.md`, see [../platform/README.md](../platform/README.md)), not here, because the repository is public.

## Log
Types: **R** risk, **A** assumption, **I** issue (happening now), **D** dependency.

| # | Type | What | Owner | Status | Checked |
|---|---|---|---|---|---|
| 1 | I | **Partly fixed on 10 Nov.** The instructor switched on read-only sales, stock and accounting for our login. Sales orders, items, parties and payments are readable now. **Still refused:** quotations, invoices and received payments (by role), and the audit trail (the platform's log of every change). The instructor says invoices and received payments come with the next deploy; quotations and the audit trail were not mentioned. Until then, checks that need these cannot verify seat 31's results. | Krishna | Open: wait for the deploy; ask about quotations and the audit trail (Q3); bug draft BUG-34-003 narrowed | 10 Nov, both systems, fresh login, read-only GETs |
| 2 | D | Seats 31 and 35 keep their results in **local files**, not on the platform, so our checks have nothing to read. **Seat 35, answered by the instructor (10 Nov, seat 35 channel):** for 15 Nov seat 35 writes nothing, and the instructor scores their pairs file directly; for version 1 the recommended proposal record is an approval request. Seat 31's 15 Nov report is local too. So for 15 Nov our tasks check only what the platform shows (records unchanged, no writes). | Krishna | Open: instructor asked to confirm our 15 Nov plan (11 Nov) | 11 Nov, seat 31 and 35 channels and their pull requests |
| 3 | D | Seat 31's reminder drafts: their mailbox bug is fixed (10 Nov, seat 31 channel), but email is private to its owner. Our login cannot read seat 31's drafts, and in a harness run the agent gets our token, which has no email app. Draft checks wait on how we start seat 31's agent (risk 5). | Krishna | Open: depends on Q2 | 11 Nov, seat 31 channel |
| 4 | R | The harness file must be at a repository root, but this repository is shared by 8 seats. | Krishna | Open: Q1 | n/a |
| 5 | R | **Which login:** the instructor said on 7 Nov that a run gives our harness seat 34's token, not the token of the seat under test. **Still open:** how our harness should start another seat's agent. Today the harness lends our token to the agent. That is fine for the plumbing task, but a real seat agent needs its own seat's login and tools (cards S34-22, S34-23). | Krishna | Open: Q2 | 7 Nov, instructor's reply |
| 6 | R | Official runs are limited (one run every 3 days, plus token caps), so a failed run costs 3 days. | Krishna | Mitigate: local dry run before every official run | 7 Nov |
| 7 | R | Shared live data changes under us, so expected answers go stale. | suite owners | Mitigate: checks compute from snapshots taken at run time; any fixed answer carries an "as of" date | n/a |
| 8 | R | Tests written by AI tools score zero. | everyone | Mitigate: agents only draft in `ideas.md`; people write the tasks; each task file names its author | n/a |
| 9 | A | Course runs happen on a throwaway copy, so any writes by the agent under test are discarded. | Krishna | Confirmed by the instructor (seat 35 channel, 10 Nov: "A harness run writes to a copy and discards the writes") | 10 Nov |
| 10 | R | The platform is still being developed, so behaviour can change with each release. | Krishna | Mitigate: run `scripts/platform_sync.py` after every release notice, and review the change report | n/a |

## Open questions for the instructor
Post these in the seat group. For Q3, paste the exact requests and replies from the local `access.md` (system, login, request, reply), as the course asks. Never include a password or a token.

1. **Harness file location.** `agentswitch-harness.toml` must be at a repository root, but this repository has one root for 8 seats. Can our harness registration point at a subfolder (`34-eval-harness/`) or a branch of our fork? Until we hear back, the file stays in our seat folder.
2. **Starting the agent.** You said a run gives our harness seat 34's token (7 Nov). How should our harness start or call seat 31's and seat 35's agents, so that each works under its own seat's login and access (for example through a platform agent task, or A2A)? Our understanding: our harness runs with seat 34's login, asks the seat's agent to do the work, then checks the data over REST with seat 34's read access.
3. **Read access for our checks.** *Partly answered on 10 Nov:* sales, stock and accounting are switched on (read only), and invoices and received payments come with the next deploy. **Still to ask:** quotations are still refused by role, and the audit trail still sits behind the email app. Can seat 34 read both? We do not need the email app itself, only read access to the audit trail.
4. **Knowledge base.** Our login now has the knowledge base. What is it meant for in our seat: as the written standard of correct behaviour, or as a place to publish score reports?
5. **Nightly run.** Where may the nightly regression run (our own machine, or a CI job in our fork), and against what: live data read-only, or a copy?
6. **Test data.** *Answered on 10 Nov (seat 35 channel):* the data has a few natural look-alike parties and no planted answers; build your own fixtures for tests. Our login is read only, so our tasks use the existing records.

## Closed
- (none yet)
