# Glossary

> Every special word used in seat 34's docs and code, in plain English.

| Word | Meaning |
|---|---|
| **AgentSwitch** | The course's business software: accounting, sales, stock, email and more, used by two pretend companies. |
| **Instance** | One running copy of AgentSwitch for one company. There are two: **Suryodaya** (India) and **Keystone** (US). |
| **Seat** | One agent job on the platform, owned by one student team. Seats 1–27 are single-app agents; seats 28–35 are the "advanced" cross-app seats. We are seat 34. |
| **Agent** | A program that uses an AI model to read data and take steps (look things up, draft a reply) towards a goal. |
| **Login / token** | We log in with a username and password and get back a **token**: a long secret string we send with every call to prove who we are. It lasts 7 days. |
| **REST** | A simple way to talk to a server: you ask a web address (for example `/api/Party`) and get data back. |
| **MCP** | Model Context Protocol. A standard way for an AI agent to discover and call "tools". On AgentSwitch, one web address (`/api/mcp`) answers all tool calls. |
| **JSON-RPC** | The message format MCP uses. Each request names a `method` and its `params`, and each reply carries either a `result` or an `error`. |
| **Tool** | One action the platform offers, such as "list the parties" or "create a note". |
| **Entity** | A kind of record, such as a party (customer or supplier), an invoice or an agent run. The platform has several hundred kinds. |
| **Party** | Any person or company the business deals with: a customer, a supplier, a contact. |
| **Knowledge base (KB)** | The platform's library of company notes: policies, playbooks, procedures, and guides for agents. |
| **Eval** | Short for evaluation: a test of how well an agent does its job. |
| **Eval harness** | The machinery that runs evals: it starts the agent, records what happened, checks the result and adds up the scores. This is what seat 34 builds (`eval_harness/`). |
| **Agent harness** | The agent's own machinery: the loop that lets a model use tools. Not what we build; we test it. |
| **Agent under test** | The agent being evaluated. It runs as a separate program (`agents_under_test/`, or another seat's folder). |
| **Agent contract** | What an agent must accept and print so we can test it: the environment variables in, an optional `AGENT_RESULT` line out. See [evaluation/agent-contract.md](evaluation/agent-contract.md). |
| **Task** | One test: a request for the agent, plus a rule for deciding if it succeeded. |
| **Golden task** | A task whose correct result has been decided and checked by a person in advance. |
| **Suite** | A set of tasks. Every seat must have a 12-task suite for version 1 (30 Nov). Our first task is one 12-task suite split across two seats: 6 tasks for seat 31 and 6 for seat 35. |
| **Trial** | One attempt at one task. Agents can give different results each time, so a task may be run several times. |
| **Grader** | Code that checks one aspect of the outcome and gives approve, revise or unevaluated. It reads the platform's data, never the agent's answer. (The course also says "verifier" or "predicate".) |
| **Outcome** | The state of the platform after a trial. This is what graders judge. |
| **Scorer** | Turns grader results and trial facts into separate scores (outcome, integrity, honesty, cost) and one `results.json` row. |
| **Integrity** | Whether the run's login wrote anything it should not have. |
| **Honesty** | Whether what the agent *said* it did matches what really happened (an honest refusal, a false success…). It is reported, but never decides a pass. |
| **Snapshot** | A saved copy of the relevant records taken before a trial, so we can see exactly what changed afterwards. |
| **Trial record** | A file with everything about one trial (manifest, snapshots, the agent's exit code and output, errors), saved **before** scoring. Also called a run record. |
| **Manifest** | Everything that can change a score, recorded with it: git commit, task and grader versions, model, agent command, time limit. |
| **Transcript** | The record of what happened in a trial. Ours is the trial record plus the agent's printed output. |
| **Audit trail** | The platform's log book of changes: one line each time someone creates, edits or deletes a record, saying who, when, which record and what changed. Our login cannot read it yet (checked 10 Nov). |
| **Driver** | The part of the eval harness that starts or calls the agent under test for one trial, and waits for it to finish. Today it starts a program on the same machine. |
| **Expected change** | A kind of check: the agent was asked to make something, and the check confirms it really exists on the platform and is right. |
| **Proposal, not action** | A kind of check: the agent was asked to suggest something for a person to approve. The check confirms a proposal exists and that the records it is about are unchanged. |
| **Process group** | A program together with every program it starts. Stopping the group stops them all, so a wrapper such as `uv run` cannot leave its child running after a time-out. |
| **Launcher** | `scripts/run_local.py`: sets the same variables the course runner sets, then starts the eval harness on your computer. |
| **Token cache** | A local, git-ignored file per system holding your current login token, so the password is used only when the token expires. |
| **Verdict** | A verifier's decision: **approve** (it checked and the work is right), **revise** (it checked and the work is wrong), or **unevaluated** (nothing could be checked). Unevaluated is never a pass. |
| **Harness mode** | A run started the way the course runner starts it: only environment variables in (the injected token and the given model endpoint), no password, no internet. `scripts/run_local.py` starts local runs the same way. See [harness-design.md](evaluation/harness-design.md). |
| **Infrastructure failure** | The test could not run fairly: a timeout, a bad login, a blocked tool. It is reported as a failure marked "infrastructure", never as the agent's fault and never as a pass. |
| **results.json** | The file a harness run must write, in the course's format: one row per task with `passed`, `score` and `evidence`. |
| **Regression** | A task that used to pass and now fails. Finding these is what a regular "regression run" is for. |
| **Nightly run** | Running all suites on a schedule (every night) to catch regressions early. |
| **Score history** | The list of past results per seat and task, kept so we can spot regressions and flaky tasks. |
| **Flaky task** | A task that sometimes passes and sometimes fails with no change, so its result cannot be trusted alone. |
| **pass@k / pass^k** | Run a task k times. **pass@k**: at least one try passed (can it ever do it?). **pass^k**: every try passed (can we rely on it?). |
| **Goal key** | The platform's own short name for the check a seat is judged by. |
| **Harness file** | `agentswitch-harness.toml`: tells the course runner how to install and run our suite. |
| **Official run** | A run done by the course's runner on a throwaway copy of an instance. Allowed once every 3 days. |
| **uv** | The tool we use to install Python and the packages our code needs. |
| **ruff / mypy** | Tools that check our code: ruff checks formatting and common mistakes; mypy checks that data types fit together. |
| **Pull request (PR)** | A request to add your changes to the shared repository. Another person reviews it first. |
| **Fork / branch** | A fork is your own copy of the repository on GitHub. A branch is a named line of work inside it. |
| **Worktree** | A second folder for the same repository, so two agents can work on two branches at once without getting in each other's way. |
| **Decision record (ADR)** | A short note that records one lasting decision: what we chose, why, and what it means. |
