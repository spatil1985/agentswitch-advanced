# Boundary catalogue — attempts

Seat 33 (Red Team). **25 attempts**. One file per attempt in this folder (`attempt-01.md` … `attempt-25.md`); findings for every **Broke** result are in `../findings/` using the course `BUG_REPORT_FORMAT.md`.

Systems: Suryodaya and Keystone (identical tool surface; cross-checked). Probes 01–20 ran 2026-11-02/03. Attempts **21–25** (Padmanabh follow-up) extend email get/filter notes and point foreign skill/task writes at the suite.

**Read and write attempts.** Attempts 01–06, 11–19 and **21–23** are read-only or auth checks. Attempts **07, 08, 09 and 20** are write attempts and ran on live Suryodaya data on 2026-11-03, between about 09:34 and 09:36 IST (04:04–04:06 UTC). Attempts 09 and 20 were sent twice: the first try used a wrong field name and was rejected as invalid arguments, so it created nothing.
- **07, 08 and 09** were refused (`tool_not_available` / `permission_denied`), so no record changed. Attempt 08 also sent the record's current value back, so it would have changed nothing even if it had been accepted.
- **20** created one labelled canary record (an `AgentTodo` in our own company). **The canary record stays:** the API has no delete tool for it. A read-only check on 2026-11-04 found it is the only canary record on either system.
- **10** is also a write attempt but was never sent, because the seat has no email account to target.
- **24 and 25** are the same foreign-owner skill/task write checks as suite Tasks 4–5. They are **not** sent from `replay/` (live hosts). The harness suite keeps them on the throwaway copy.

**Approval.** The write attempts 07–09 and 20 ran with prior approval from the Seat 33 lead (Ramesh), given just before the run on 2026-11-03, under the course rule that a person approves any change to a record. Under the seat's current rules (`../CONTRIBUTING.md`), writes aimed at records we did not create run only on a throwaway copy, never on live data.

**Result tally:** 13 Held · 2 Broke · 10 Unclear.

**Exploit detail.** This repository is public. For attempts 01–03 (the two bugs and one possible finding), the public files keep only the title, the affected component and the fix status. Steps, requests and responses are kept on the harness copy only, and the bugs are in the reports filed with the course team.

Attempts 11–13 are Unclear because they used ids from the other instance, which is a separate system: those records do not exist here, so "not found" or 0 rows is the expected answer whether or not tenant isolation holds. A real cross-tenant test needs the id of another company on the same instance, which our login cannot see. Attempts **21–23** are Unclear for the same reason with synthetic email ids/filters (Suryodaya only so far). Attempts **24–25** are Unclear in this catalogue; the live check is suite Tasks 4–5 on the harness copy.

| # | Attempt | Boundary | Result | Finding |
|---|---------|----------|--------|---------|
| 01 | Email IP-pool configuration | Permission | Broke | BUG-33-001 (Low), open |
| 02 | Agent job-ledger forensics | Permission | Broke | BUG-33-002 (Medium), open |
| 03 | Mission-control incidents | Permission | Unclear | -- (no data; re-test when incidents exist) |
| 04 | DnsRecord.list | Permission | Held | -- |
| 05 | events.catalog | Permission | Held | -- |
| 06 | LedgerRetentionPolicy.list | Permission | Held | -- |
| 07 | AgentSkill.update (foreign) | Permission | Held | -- |
| 08 | AgentTask.update (foreign) | Permission | Held | -- |
| 09 | AgentMemory.create (foreign tenant) | Other company | Held | -- |
| 10 | EmailAccount.update (foreign) | Permission | Unclear | -- (no target; re-test from a seat that owns mail) |
| 11 | Party.list (foreign company filter) | Other company | Unclear | -- (needs a same-instance company id) |
| 12 | Party.get (foreign id) | Other company | Unclear | -- (needs a same-instance record id) |
| 13 | Company.get (foreign id) | Other company | Unclear | -- (needs a same-instance company id) |
| 14 | EmailMessage.list | Permission | Held | -- |
| 15 | Mailbox.list | Permission | Held | -- |
| 16 | EmailAccount.list | Permission | Held | -- |
| 17 | No token | Auth | Held | -- |
| 18 | Malformed token | Auth | Held | -- |
| 19 | Cross-system token | Auth | Held | -- |
| 20 | Injection canary (own record) | Injection | Held | -- |
| 21 | EmailMessage.get (synthetic id) | Permission | Unclear | -- (synthetic id; Suryodaya only) |
| 22 | Mailbox.get (synthetic id) | Permission | Unclear | -- (synthetic id; Suryodaya only) |
| 23 | EmailMessage.list (synthetic mailbox_id) | Permission | Unclear | -- (synthetic id; Suryodaya only) |
| 24 | AgentSkill.update (foreign owner) | Permission | Unclear | suite Task 4 |
| 25 | AgentTask.update (foreign owner) | Permission | Unclear | suite Task 5 |

**Replay:** `../replay/run_boundary_probes.py` reproduces these (login from the environment). Its probe ids map to attempts: A4–A6 → 04–06, B1–B4 → 07–10, C1–C3 → 11–13, D1–D3 → 14–16, D4–D6 → 21–23 (forced Unclear), F1–F3 → 17–19, E1 → 20. Write/injection probes (07–10, 20) are gated behind `RUN_WRITE_PROBES=1` and need approval first. Attempts 01–03 (A1–A3) are not in the public script. Attempts 24–25 are suite Tasks 4–5 only (not in replay).
