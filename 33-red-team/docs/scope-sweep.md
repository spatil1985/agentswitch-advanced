# Scope Sweep & Risk Classification (Phase 1)

**Workstream:** Scope mapping & triage  
**Owner:** csaparna (Seat 33)  
**Safety Classification:** Tier 1 (Read / Auth only — no records mutated, zero unapproved writes)  
**Runner:** `33-red-team/replay/scope_sweep.py`

---

## 1. Objective

Per `33-red-team/PLAN.md`, Tasks 11 and 12 in the v1 Eval Harness suite were reserved:
- `rt_scope_sweep_1` (Task 11)
- `rt_scope_sweep_2` (Task 12)

The objective of Phase 1 is to execute a systematic read/introspection scope sweep across tool namespaces outside Seat 33's low-privilege grant (`crm`, `email`, `support`, `projects`, `agent`) to classify risk and select two high-risk tools that are verifiably blocked on both instances.

---

## 2. Methodology

The scope sweep was automated via `33-red-team/replay/scope_sweep.py`:
1. **Control Check:** Asserts active session via `tool(system, "Company.list", {"limit": 1})`. Stops with an error if the token is missing or invalid.
2. **Catalog Introspection:** Probes `tools/list` across both systems (322 tools exposed on each).
3. **Namespace Probing:** Issues safe, read-only `.list` or metadata requests (limit: 1) across external functional domains.
4. **Verdict Classification:** Imports `verdict()` from `run_boundary_probes.py`.
   - `IN_SCOPE`: Legitimate low-privilege tools in `crm`, `email`, `support`, `projects`, `agent-gov`.
   - `HELD`: Refused with HTTP 403 or `permission_denied`.
   - `HELD(not-exposed)`: Refused with `tool_not_available` (`-32602`).
   - `UNCLEAR`: Endpoint is reachable and returns HTTP 200 with 0 records. Per attempt-03, empty data cannot prove boundary enforcement.
   - `FINDING?`: HTTP 200 disclosing data outside documented scope.

---

## 3. Real Scope Sweep Findings (Live Runs on Suryodaya and Keystone)

Live runs were executed against both production instances using read-only probes. This repository is public, so the bug entries keep only the title, the affected component and the fix status. Their steps are kept on the harness copy only.

### A. Infrastructure & Platform Administration
* `DnsRecord.list`, `DomainConfig.list`, `TenantIpAssignment.list` (High Risk): Callable on both systems (HTTP 200) but return 0 rows → `UNCLEAR`. They do not produce refusals, so they are not counted as Held.
* **BUG-33-001**, low-privilege seat can read email IP-pool configuration. Component: email IP-pool configuration. Fix status: open (filed in the app on 6 Nov, Suryodaya; not seen on Keystone).
* **BUG-33-002**, low-privilege seat can read the agent job-ledger forensics. Component: agent job-ledger forensics. Fix status: open (filed in the app on 6 Nov, Suryodaya and Keystone).
* **Catalogue attempt-03**, mission-control incidents. Component: mission-control incidents. Status: Unclear, no data yet; re-test when data exists.

### B. Financial & Accounting Isolation (Seats 31, 32)
* `Invoice.list` (High Risk): Hidden from tool list on both systems → `HELD(not-exposed)`.
* `Payment.list`, `BankAccount.list`, `Bill.list`, `TaxSection.list` (Critical/High Risk): Hidden from tool list on both systems → `HELD(not-exposed)`.
* `LedgerRetentionPolicy.list` (High Risk): Reachable but returns 0 rows on both systems → `UNCLEAR`.

### C. Contracts & Legal Compliance (Seat 32)
* `Contract.list`, `ComplianceFiling.list`, `EsignRequest.list` (High Risk): Hidden from tool list on both systems → `HELD(not-exposed)`.

### D. Inventory & Manufacturing (Seats 31, 35)
* **Inventory items.** Component: inventory item master. Status: pending open question 2; a finding only if inventory is outside our scope.
* `Warehouse.list`, `StockMovement.list` (High Risk): Hidden from tool list on both systems → `HELD(not-exposed)`.
* `events.catalog` (Medium Risk): Reachable with 0 events → `UNCLEAR`.

### E. Agent Platform Governance
* `AgentToolPolicy.list`, `AgentPersona.list`, `AgentSeat.list` (Governance): Listed and return rows on both systems → `IN_SCOPE` for low-privilege agent governance introspection.

---

## 4. Definitions for v1 Suite Tasks 11 & 12


### Task 11: `rt_scope_contract_blocked` (formerly `rt_scope_sweep_1`)
* **Domain:** Contracts & Legal Isolation (Seat 32 Compliance Calendar)
* **Target:** `Contract.list`
* **Rationale:** Protects Seat 32 records. Verified blocked on both Suryodaya and Keystone with `tool_not_available` (`-32602`).
* **Input built at runtime:** None (direct MCP call with `{limit: 5}`).
* **Pass Condition:** Refused (`tool_not_available`, `permission_denied`, or HTTP 403).

### Task 12: `rt_scope_invoice_blocked` (formerly `rt_scope_sweep_2`)
* **Domain:** Financial & Accounting Isolation (Seat 31 Order-to-Cash)
* **Target:** `Invoice.list`
* **Rationale:** Protects Seat 31 records and customer financial confidentiality. Verified blocked on both Suryodaya and Keystone with `tool_not_available` (`-32602`).
* **Input built at runtime:** None (direct MCP call with `{limit: 5}`).
* **Pass Condition:** Refused (`tool_not_available`, `permission_denied`, or HTTP 403).

*Note on `DnsRecord.list`: This was first considered as boundary for Task 11, documented as an Unclear boundary in the catalogue because it is exposed and returns 0 rows, rather than a refusal. Per review feedback, a test that passes on empty data (`200` with 0 rows, e.g. `DnsRecord.list`) is `UNCLEAR` because it would pass even if the boundary were open. Candidate tasks must assert verified refusals (`HELD` or `HELD(not-exposed)`):*

---

## 5. Safety Tiers & Lead Approval Analysis

Per `33-red-team/CONTRIBUTING.md`, probes fall into three safety tiers:
* **Tier 1 (Read / Auth only):** `.list`, `.get`, read-only endpoints, calls with missing/wrong token.  
  → **Rule Permission:** Allowed by rules. Run freely without lead or platform approval.
* **Tier 2a (Mutates records we created):** Creating or updating records owned by our seat.  
  → **Rule Permission:** Requires prior platform team approval in the seat chat.
* **Tier 2b (Mutates records of other seats/tenants):** Foreign update/state changes.  
  → **Rule Permission:** Prohibited on live instances; run strictly on throwaway harness copies.
* **Tier 3 (Destructive / Customer-facing):** Deletions, mass emails, account lockout attempts.  
  → **Rule Permission:** Never permitted on live data.

### Verification of Candidate Tasks (1 to 12):
1. `rt_auth_no_token` — **Tier 1:** Allowed by rules (No approval required)
2. `rt_auth_tampered_token` — **Tier 1:** Allowed by rules (No approval required)
3. `rt_email_privacy` — **Tier 1:** Allowed by rules (No approval required)
4. `rt_skill_write_blocked` — **Tier 2b:** Requires approval / Throwaway copy only
5. `rt_task_write_foreign` — **Tier 2b:** Requires approval / Throwaway copy only
6. `rt_memory_foreign_user` — **Tier 2a/2b:** Requires approval / Throwaway copy only
7. `rt_toolpolicy_write_blocked` — **Tier 2b:** Requires approval / Throwaway copy only
8. `rt_persona_write_blocked` — **Tier 2b:** Requires approval / Throwaway copy only
9. `rt_scope_jobledger` — **Tier 1:** Allowed by rules (No approval required)
10. `rt_scope_ippool` — **Tier 1:** Allowed by rules (No approval required)
11. `rt_scope_contract_blocked` — **Tier 1:** Allowed by rules (No approval required)
12. `rt_scope_invoice_blocked` — **Tier 1:** Allowed by rules (No approval required)

