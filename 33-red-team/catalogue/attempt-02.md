# Attempt 02 — Agent job-ledger forensics

1. **Attempt:** Read the agent job-ledger forensics as a low-privilege seat.
2. **Boundary:** (Permission) Affected component: agent job-ledger forensics (governance and audit records). The 3 Nov access note lists only agent records (seats, skills, tasks) as readable.
3. **Steps:** Not in this public repository. They are in the report filed with the course team, and are re-tested on the harness copy only.
4. **Expected:** Refused.
5. **Actual:** Data was returned. Details are kept on the harness copy only.
6. **Result:** Broke — BUG-33-002 (Medium). **Fix status:** open; filed in the app on 2026-11-06 (Suryodaya and Keystone), shows Received. See `../findings/BUG-33-002.md`.
