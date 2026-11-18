# 0007 The example suite is agent-written plumbing, never graded

- **Status:** Accepted, 7 Nov 2026
- **Context:** We needed one task to prove the whole chain works (agent, platform, graders, scorer, results.json). Graded tests must be written by people (decision 0003).
- **Decision:** `suites/example/` holds one task written by a coding agent. It is marked `graded = false`, and its author field says "coding agent (plumbing only, not graded)". It is never copied into a graded suite. Graded suites are written by people, by hand.
- **Consequences:** The example can change freely to test the machinery. A test checks that it stays marked as plumbing only.
