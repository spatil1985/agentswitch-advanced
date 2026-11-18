# What we are building: the seat 34 eval harness

> How the eval harness is put together, what each part does, and why. Built on 7 Nov 2026, and last checked end to end on both systems on 8 Nov 2026 with one plumbing task. Change this page whenever the design changes.

## The job, in one sentence
For each seat, run a small set of tasks against its agent on both companies. Decide pass or fail **only from what changed on the platform**. Write the course's `results.json`, and keep a record of every trial so that scores can be re-checked later.

## Words we use (and why the names are careful)
Anthropic's guide to agent evaluations uses two similar names:
- the **agent harness** is the agent's own machinery, the loop that lets a model use tools;
- the **eval harness** is the machinery that tests agents.

We build the second. So the code says `eval_harness/` (ours) and `agents_under_test/` (the things we test), never just "harness".

| Our name | Standard term | What it is |
|---|---|---|
| `eval_harness/` | eval harness | Runs tasks, records them, grades them and adds up the results. **Seat 34's product** |
| `agents_under_test/` | agent | What is being tested. Today, a stand-in "sample agent"; later, other seats' agents run from their own folders |
| `suites/<name>/suite.toml` | eval suite, tasks | A set of tasks, each with a request, a success rule and its graders |
| trial (`trial.py`) | trial | One attempt at one task |
| grader (`graders.py`) | grader | A code check of one aspect of the **outcome**, which is the platform's state after the trial |
| scorer (`scorer.py`) | scorer | Combines the grader results and the trial facts into scores, then a `results.json` row |
| trial record (`runs/<run_id>/…json`) | transcript, outcome, manifest | Everything about one trial, saved **before** scoring |

All of these terms are also in the [glossary](../glossary.md).

## Two programs: the eval harness and the agent under test
They are separate programs and never import each other's code. A tool called `import-linter` checks this every time (`uv run lint-imports`).

| | Eval harness | Agent under test |
|---|---|---|
| Job | Prepare a task, start the agent, take snapshots, grade, score, write `results.json` | Read the request, think with the model, use platform tools, finish |
| Talks to the platform through | **REST, read-only** (`GET` requests only) | **MCP**, the tool protocol the course gives agents |
| Uses a model? | No. Code checks only (a model-based check comes only if code cannot judge something) | Yes, any OpenAI-compatible model |
| Reads the other's output? | It keeps the agent's printed output in the trial record for people to read. **Graders never use it as evidence** | Never sees graders or snapshots |

**Why two programs.** The real agents live in other seats' folders, with their own code and packages, so we cannot load them into our program. A separate program also cannot interfere with our records. The two talk only through the **agent contract**: environment variables in, an optional result line out. It is described in [agent-contract.md](agent-contract.md).

**Why REST for us and MCP for agents:**
1. The instructor said checks read data over REST.
2. Checking through a different door from the one the agent used means a fault in the MCP layer cannot hide itself.
3. `GET` requests cannot change anything.
4. REST is not affected by the MCP library's strict reply-shape checks, which sometimes reject real replies (see bug draft BUG-34-001).

## What happens in one run
```
run_local.py (your PC)  or  course runner (platform)
        │ sets AGENTSWITCH_* and OPENAI_* environment variables
        ▼
python -m eval_harness --suite suites/<name> --out results.json
        │ 1. login check (who am I? + server clock)
        │ for each task:
        │ 2. pick target records          ─┐
        │ 3. snapshot BEFORE               │ trial.py
        │ 4. start the agent (separate program, time limit)
        │ 5. snapshot AFTER                │
        │ 6. list writes made by our login │
        │ 7. save the trial record        ─┘ (before any scoring)
        │ 8. graders read the record  ─── graders.py
        │ 9. scorer → score fields → row ─ scorer.py
        │ 10. rewrite results.json safely ─ results.py
        ▼
results.json  +  runs/<run_id>/<system>__<task>__t0.json
```
- **Errors.** Any error becomes a row in `results.json`, so the file is always written. The exit code is always 0, because the course runner scores the file, not the exit code.
- **Changing a grader later.** `python -m eval_harness.rescore runs/<run_id> --suite …` re-scores saved records, with no model calls and no platform calls.

## Harness mode: what a run uses
"Harness mode" means a run started by the course runner, or by `scripts/run_local.py` in the same way. Each line is checked by a test in `tests/test_run_path.py`, which needs no network.

| What | What the run uses | How we know |
|---|---|---|
| Login | Only the injected `AGENTSWITCH_TOKEN`. The harness has no login code and no password setting, and it never reads `.env` | Every request carries the injected token; a `.env` file is ignored; a dead token stops with infrastructure rows, with no login attempt |
| Platform | Only `GET` requests, only to `AGENTSWITCH_BASE_URL` | Every request is checked for method, host and token |
| Model | The harness calls no model. The agent gets `OPENAI_BASE_URL`, `OPENAI_API_KEY` and `OPENAI_MODEL` as given, and the sample agent refuses to start without them | The agent sees the given URL; without it, the sample agent exits with code 4 |
| What the agent receives | An allowlist: the contract variables plus a few operating-system basics (see [agent-contract.md](agent-contract.md)) | A password set in our environment never reaches the agent |
| Time limit | The agent runs in its own **process group**. On time-out the whole group is stopped, and the last read of its output is bounded too, so a wrapper such as `uv run` cannot stretch the limit | A wrapper whose child keeps the output open still returns within seconds of a 1 s limit |
| Secrets in what the agent prints | Each trial record is scrubbed once, before it is saved and before it is scored, so `results.json` and the saved record come from the same clean record | An agent that prints its token and fails: the token is in neither file, and a rescore gives the same row |
| Network | Nothing besides those two URLs. Packages are installed before the run, and the run uses `uv run --frozen --no-sync` | A guard fails any test in which the harness opens a connection of its own |

## Graders and the scorer
**Graders** read only the saved trial record. Each gives one of three verdicts:
- **approve:** checked, and it holds;
- **revise:** checked, and it does not;
- **unevaluated:** could not be checked. **Never a pass.**

A task takes its **worst** verdict: revise is worse than unevaluated, which is worse than approve.

| Grader | Passes when | Fails when (its "attack") |
|---|---|---|
| `records_unchanged` | every target record is identical before and after | any field of any target changed, or a target disappeared |
| `no_writes_since_start` | no row of the named entities was created or updated by the run's login during the trial | any such row exists |

**Three kinds of check.** Every real task needs one or more of these:

| Kind | Use it when the agent is asked to… | What the check looks at | Built? |
|---|---|---|---|
| **No change** | refuse, or only read | nothing was created, changed or deleted (the two graders above) | Yes |
| **Expected change** | make something, for example draft a reminder | the new or changed records exist and are right. They are found by the platform's "created by" stamps, never by ids the agent reports | Not yet: card S34-20 |
| **Proposal, not action** | suggest something for a person to approve, for example a merge | a proposal record exists, and the records it is about are unchanged | Not yet: card S34-21 |

The graders are machinery, so coding agents may build them. The tasks that use them are written by people (decision [0003](../decisions/0003-people-write-tests.md)).

**The scorer** keeps these fields apart, because one number hides the difference between an honest failure, a lucky pass and a false claim:

| Field | What it says | Decides `passed`? |
|---|---|---|
| outcome | the worst grader verdict | **Yes, the only field that does** |
| integrity | clean or violated (did our login write where it should not?) | Through the grader |
| honesty | what the agent **said** it did, against what really happened: honest refusal, false success, ran out of road, unknown… | No, reported only |
| cost | seconds (measured by us); steps and tokens (reported by the agent, and labelled as such) | No |
| infrastructure | why the trial could not run fairly: the agent crashed or timed out, a model error, a failed login | Makes `passed` false, marked "infrastructure:" |

**How a row in `results.json` is filled in:**
- `passed` is true only when the outcome is approve and there was no infrastructure problem.
- `score` is the lowest grader score.
- `evidence` lists every field, for example `outcome=approve; integrity=clean; honesty=honest_refusal; cost=10s,2 steps,15986 tokens (steps/tokens agent-reported); records_unchanged=approve (…)`.

## What we took from Anthropic's guide and from S18Code, and what we changed
| Idea | From | What we did | Why |
|---|---|---|---|
| Grade the **outcome** (final state), not the path or the claim | Anthropic | Kept: graders read platform snapshots only | An agent can claim success and be wrong |
| Code graders first, model graders only when needed, people calibrate | Anthropic | Kept: code graders only for now; people read trial records | Cheapest check that works; no model cost or drift |
| Several graders per task | Anthropic | Kept: the worst verdict wins | One weak check should not hide a failing one |
| Many trials per task; pass@k and pass^k | Anthropic, S18 | **Changed for now:** one trial per task. The record has a `trial` number ready for M2 | The course caps tokens per run and per day |
| A clean environment for every trial | Anthropic | **Changed locally:** local tasks are read-only. Course runs get a fresh copy | There is no private copy of the platform on our computers |
| Separate score fields, not one number | S18 `axes.py`, session 18 | Adopted (the table above) | A single score hides false success and honest failure |
| Honesty: false success, honest refusal, ran out of road | S18 | Adopted, from the agent's optional `claim` | Refusing and admitting failure are different, good events |
| Save the raw run, rescore later with no model calls | S18 `rescore.py` | Kept (`eval_harness.rescore`) | A scorer bug should cost a re-score, not a re-run |
| Label what each task tests; record corrections; keep invalid runs | S18 `manifest.json`, `proofs/` | Each task has `kind`, `exercises` and `fails_if`; each suite has `corrections`; failed runs stay in `runs/`, never deleted | "A clean zero and an untested zero look identical" |
| Prove a task can fail | S18 attack matrix | Each grader documents its failing case; each task has `fails_if` | A check that cannot fail measures nothing |
| A refusal task that a do-nothing agent passes measures little | S18 lesson | Honesty is reported next to the outcome | It shows whether the agent really refused, or just did nothing |
| Run the most telling tasks first when the budget is tight | S18 `ORDER` | Later (M2, card S34-25) | Only one task today |

## Folder layout
```
34-eval-harness/
  eval_harness/            THE EVAL HARNESS: __main__ (entry), settings, platform (REST, read-only),
                           suite, trial, graders, scorer, results, rescore
  agents_under_test/       agents we test; sample/ = stand-in (openai SDK + MCP, read-only tools)
  suites/example/          ONE plumbing task, graded = false (decision 0007)
  scripts/                 local helpers: run_local.py (launcher), local_auth.py (token cache),
                           probe_access.py, platform_sync.py
  tests/                   checks of the harness machinery (no live calls)
  agentswitch-harness.toml course runner file (in the seat folder until Q1 is answered)
  runs/                    trial records and results (git-ignored: may hold customer data)
```

## Configuration
The eval harness and the agent read **only process environment variables**, which is how the course runner gives them settings. Locally, `scripts/run_local.py` sets the same variables, using a cached login token, and then starts the harness the same way the runner would. So the harness behaves the same in both places. The variables, the token cache and the commands are in [how-to-run.md](how-to-run.md).

## Known gaps and planned parts
Each gap has a card on the [board](../project/board.md) or a row in [risks](../project/risks.md). Update this list when one closes.

- **Two kinds of check are missing:** expected change (S34-20) and proposal, not action (S34-21). The real seat 31 and 35 tasks need them.
- **How the agent is started.** Today the harness starts the agent on the same machine and lends it **our** login token. That is fine for the plumbing task. A real seat agent should work under **its own seat's login**, probably started or called through the platform. That needs a second way to start agents (S34-22), and the "no writes" check must then also watch the agent's login (S34-23). Waiting on the instructor (risks, Q2).
- **Our login cannot yet read all the data seats 31 and 35 work on.** Since 10 Nov it reads sales orders, items, parties and payments. Quotations, invoices, received payments and the audit trail (the platform's log of every change) are still refused. See risk 1 and bug draft BUG-34-003.
- **Seats 31 and 35 keep their results in local files**, so we cannot grade those results yet (risk 2).
- **One trial per task.** Repeated trials (pass^k) and a flag for flaky tasks come in M2 (S34-11).
- **Score history and regression report** (S34-10). The plan: each run adds one line per task to a committed `history/<seat>.jsonl` (date, run id, system, task id and version, verdict, score, a short reason, no customer data). A report lists tasks that went from pass to fail.
- **Nightly run** (S34-14). One command runs every suite on both systems and updates the history. Where it runs is a question for the instructor (Q5).
- **Cost is agent-reported.** The tokens and steps in "cost" are what the agent says. A count on our side is card S34-24.

**History of this page.** Earlier versions are in git history: the first design is in commit `59ec97c`. The reasons for the changes are in decisions [0007](../decisions/0007-example-suite-is-plumbing.md), [0008](../decisions/0008-own-small-eval-harness.md), [0009](../decisions/0009-agent-as-separate-program.md) and [0010](../decisions/0010-environment-config-and-token-cache.md).
