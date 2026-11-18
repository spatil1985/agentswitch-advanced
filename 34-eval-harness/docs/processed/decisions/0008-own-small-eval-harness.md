# 0008 Our own small eval harness, not a framework

- **Status:** Accepted, 7 Nov 2026
- **Context:** Industry practice often builds on an evaluation framework. The leading open-source one is Inspect AI, from the UK AI Security Institute, which offers tasks, graders, repeated trials, logs and rescoring. But the course grades our own harness, and asks us to learn to build harnesses rather than use ready-made ones.
- **Decision:** We write a small harness of about 8 modules, named with the vocabulary of Anthropic's guide and course session 18 (task, trial, grader, scorer, trial record). We borrow ideas, not code: separate score fields, saving before scoring, rescoring from disk, repeated trials later.
- **Consequences:** We own and test the code ourselves. It stays small and readable, with few dependencies. Features such as a log viewer are not included, and are added only if needed (YAGNI).
