# Current Status

**The single place to see where Seat 29 stands.** Update it after every run: change "Right now" and any tables that moved, and add one line to the run log.

**Last updated:** 6 Nov 2026, 16:50 IST

## Right now

| | |
|---|---|
| **Phase** | First task, due 15 Nov 2026 |
| **Overall** | On track, as long as we get the two approvals listed under Blockers |
| **Active branch** | `seat29/document-reader`, committed locally, not pushed. `Issues.md` is held back |
| **In review** | [PR #11](https://github.com/theschoolofai/agentswitch-advanced/pull/11), read-only client and write guard |
| **Accuracy** | **Fair test on samples 15 to 20: 12 of 13 fields at 6/6, `total_stated` at 3/6, flags 5/6.** Rules frozen at commit `b4fe528` |
| **Known cause** | All 3 misses were credit notes labelled `CREDIT TOTAL`, which the frozen rules could not read. They left the total empty and went to a person |
| **Version 2** | Commit `61b1f48` reads that label. All 20: 13 of 13 fields at 20/20, flags 19/20. **Not a fair test**, because the fix came after seeing the result |
| **First task** | Reader and scores are done. Still missing: draft Bills on the platform, which need Rohan's permission |
| **Report** | "Seat 29 First Task Accuracy Report" is drafted in Claude Docs. Confirm it was shared and sent |
| **Next action** | Send Rohan the report, and ask Priye for a new held-back set that includes vendor bills |

## Milestones

| Date | Milestone | Status |
|---|---|---|
| 15 Nov 2026 | Classify and extract 20 PDFs, report accuracy per field | **In progress** |
| 30 Nov 2026 | Version 1 and 12-task suite | Not started |
| 20 Dec 2026 | Integration run of all 8 seats | Not started |
| 31 Dec 2026 | Final: suite passes on both systems, demo, README, closed bug list | Not started |

## What exists

| Part | Status | Where |
|---|---|---|
| Platform client, read-only write guard | Built, in PR #11 | `intake/mcp_client.py` |
| Live login check | Built, in PR #11 | `intake/probe.py` |
| Document reader | Built, committed locally | `intake/reader.py` |
| Local extract command | Built, committed locally | `intake/extract.py` |
| Accuracy scorer | Built, committed locally, scores flags | `intake/score.py` |
| Docs | `Issues.md` is uncommitted and held back. This page and the guide have uncommitted updates | `docs/` |
| Accuracy report for Rohan | Drafted, private until shared | Claude Docs |
| Collect from Drive, email and forms | **Not built** | |
| Create drafts on the platform | **Not built**, needs approval | |
| Review queue connection | **Not built** | |
| Handling for scans and photos | **Not built** | |
| 12-task suite and harness file | **Not built** | |
| Seat skill record: procedures, knowledge, examples | **Not written** | On the platform |
| Demo recording | **Not made** | |

## Latest results

**Unit tests:** 86 of 86 passed on Python 3.12 (6 Nov).

**Version 2 on all 20 samples (commit `61b1f48`, not a fair test):** all 13 fields at 20/20, flags 19/20. The one flag difference is the extra `ambiguous_date_order`, which we keep on purpose. Proposed actions: 11 draft bills, 1 duplicate rejected, 5 rejected as not a bill, 3 credit notes for review.

**Reader on samples 01 to 14:**

| Measure | Result |
|---|---|
| Documents read | 14 of 14 |
| Types found | 12 vendor bills, 2 sales invoices |
| Flags raised | 1 discount line, 1 duplicate, 1 foreign currency, 1 no due date, 1 tax exempt, 1 total mismatch |
| Key fields produced | 14 of 14 |
| Check method | Exact match against the answer key. The scorer printed totals only |

**Accuracy per field (exact match, rules frozen at commit `b4fe528`):**

| Field | Samples 01–14 (tuning set) | Samples 15–20 (fair test, one run) | All 20 |
|---|---|---|---|
| `counterparty_gstin` | 14/14 | 6/6 | 20/20 |
| `counterparty_name` | 14/14 | 6/6 | 20/20 |
| `currency` | 14/14 | 6/6 | 20/20 |
| `doc_type` | 14/14 | 6/6 | 20/20 |
| `due_date` | 14/14 | 6/6 | 20/20 |
| `invoice_date` | 14/14 | 6/6 | 20/20 |
| `invoice_number` | 14/14 | 6/6 | 20/20 |
| `lines` | 14/14 | 6/6 | 20/20 |
| `subtotal` | 14/14 | 6/6 | 20/20 |
| `tax_rate_percent` | 14/14 | 6/6 | 20/20 |
| `tax_total` | 14/14 | 6/6 | 20/20 |
| `tax_type` | 14/14 | 6/6 | 20/20 |
| **`total_stated`** | 14/14 | **3/6** | **17/20** |
| `flags`, exact set per document | 14/14 | 5/6 | 19/20 |

**Flags found across all 20:** duplicate 1 of 1, foreign currency 1 of 1, discount line 1 of 1, no due date 2 of 2, tax exempt 1 of 1, total mismatch 1 of 1. One extra flag was raised that is not in the key: `ambiguous_date_order`.

**How to read this:**

- The fair test is the honest number, but it is only 6 documents, all sales invoices and credit notes. No vendor bills were in it.
- The tuning scores come from documents the rules were built on, so they do not predict accuracy on new documents.
- `total_stated` missed on all 3 credit notes, which label their total `CREDIT TOTAL`. The total was left empty, confidence went to 0, and they went to a person. No value was invented.
- The extra flag came from one document whose two dates can each be read day-first or month-first. Our reader flags that for a person. The key does not list it, so that document's flag set does not match exactly.
- A different held-back set may be used at review.

## Platform facts

| Fact | Suryodaya | Keystone |
|---|---|---|
| Accounting documents | 120 | 20 |
| Intake samples stored | 20, since 10:18 UTC on 6 Nov | 20, since 10:18 UTC on 6 Nov |
| Sample files match our copies by size | 20 of 20 | 20 of 20 |
| Samples extracted so far | 0 | 0 |
| Our records on the platform | 1 Drive file, labelled `[seat29-upload-test]` | None |
| Bills | 356 as of 5 Nov | 104 as of 5 Nov |
| Harness link set | No | No |

Release 16 was not announced as live at the last update, but the samples are already stored. Recheck the tool list when the release is announced.

API tokens were issued on 5 Nov and last 7 days, so they need renewing around 12 Nov.

## Blockers

| Blocker | Needs | Owner | Since |
|---|---|---|---|
| Permission to run `extract` and `accept` on live data | Rohan's answer | Sudip to ask | 5 Nov |
| Can Priye merge PRs? No GitHub username as of 3 Nov | Priye to confirm | Sudip to ask | 5 Nov |

## Open questions

| Question | Asked? | Answer |
|---|---|---|
| Where are the 20 sample PDFs? | Yes | **Answered 6 Nov:** zip supplied, and now stored on the platform |
| Why do seeded files return `file_unavailable`? | Yes | **Answered 6 Nov:** they have records but no stored files |
| Test one upload and report the result | Asked by Rohan | **Done.** Reply drafted. Confirm it was sent |
| How does an uploaded file reach bill intake? | In the drafted reply | Waiting |
| May we run `extract` and `accept` on live data? | Yes | Not answered in what we have seen |
| Why does `Bill.submit` preview as allowed? | Yes | Not answered in what we have seen |
| May the harness file live on a separate fork branch? | Yes | Not answered in what we have seen |

## Next actions

| # | Action | Owner |
|---|---|---|
| 1 | ~~Run `--describe` on the key~~ Done 6 Nov: 20 documents, 14 fields | Claude, at Sudip's request |
| 2 | Tell Rohan the samples are already visible, and ask if `extract` may run on them | Sudip |
| 3 | Submit the bugs in [Issues.md](Issues.md) | Sudip, with Priye |
| 4 | ~~Align the reader with the key and score 01 to 14~~ Done 6 Nov: 13 of 13 fields at 14/14 | Claude, at Sudip's request |
| 5 | ~~Add flag scoring and freeze the rules~~ Done 6 Nov, commit `b4fe528` | Claude |
| 6 | ~~Run 15 to 20 once, and score it~~ Done 6 Nov | Claude |
| 6a | ~~Fix `CREDIT TOTAL` as version 2~~ Done 6 Nov, commit `61b1f48` | Claude |
| 6b | Ask Priye for a new held-back set, including vendor bills, to test version 2 fairly | Sudip |
| 7 | Share the accuracy report and send it to Rohan before 15 Nov. It discloses that our coding assistant ran the scorer | Sudip, with Priye |
| 8 | Post the Sunday update, first due 8 Nov | Sudip |

## How to score

Run these from `29-document-intake`. They print field names and totals only, never answers.

```
.venv\Scripts\python.exe -m intake.score --describe --key "PATH\TO\KEY.zip"
.venv\Scripts\python.exe -m intake.score --labels --key "PATH\TO\KEY.zip"
.venv\Scripts\python.exe -m intake.score local\predictions_tuning.json --key "PATH\TO\KEY.zip"
```

## Run log

Newest first. Keep each entry to one line, with counts only.

| When (IST) | Run | Result |
|---|---|---|
| 6 Nov, 16:50 | Docs updated with the solution details. No new run | The guide now covers fields, rules, flags, confidence, testing and lessons |
| 6 Nov, 16:45 | Accuracy report drafted for Rohan | Fair-test numbers first, with the limits and the scorer disclosure |
| 6 Nov, 16:35 | Version 2 on all 20 samples, commit `61b1f48`, not a fair test | All 13 fields at 20/20, flags 19/20. 86 of 86 tests passed |
| 6 Nov, 16:32 | **Fair test on samples 15 to 20, one run, rules at `b4fe528`** | 12 of 13 fields at 6/6, `total_stated` 3/6, flags 5/6. All 20: `total_stated` 17/20, flags 19/20, other fields 20/20 |
| 6 Nov, 16:30 | Flag scoring added, samples 01 to 14 rescored | All 13 fields at 14/14, flags 14/14. 84 of 84 tests passed |
| 6 Nov, 16:25 | First score on samples 01 to 14, at Sudip's request | 13 of 13 scored fields at 14/14. Tuning set, flags not scored |
| 6 Nov, 16:23 | Reader aligned with the key, samples 01 to 14 re-run | 82 of 82 tests passed, 14 of 14 key fields produced. Not scored yet |
| 6 Nov, 16:22 | Scorer `--labels` on the answer key, at Sudip's request | Label lists only, nothing per document. 1 flag label withheld by the safeguard |
| 6 Nov, 16:19 | Scorer `--describe` on the answer key | 20 documents, 14 fields. Names and types only, no answers printed, key not extracted |
| 6 Nov, 16:13 | Intake queue state check, both systems | `review_required` returned 72 and 20 documents that were never extracted. Became BUG-29-006 |
| 6 Nov, 16:11 | Read-only bug checks, both systems | 15 findings written up in Issues.md. No record changed |
| 6 Nov, ~15:55 | Reader on samples 01 to 14 | 14 read, 12 bills and 2 sales invoices, all known traps in that range flagged |
| 6 Nov, ~15:50 | Unit tests | First run: 9 failed and found the "Rs." bug. After the fix: 71 of 71 passed |
| 6 Nov, 15:35 | One upload to Suryodaya, requested by Rohan | Stored correctly in Drive, did not reach the intake queue |
| 5 Nov | Live login check, both systems | Logins fine, `Bill.submit` refused by the guard without being sent |
| 5 Nov | Unit tests for the client | 27 of 27 passed on Python 3.14 |
| 5 Nov | First read-only look at both systems | Found built-in bill intake, no sample PDFs at that time |
