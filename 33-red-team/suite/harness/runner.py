"""Runs the Seat 33 v1 suite and writes results.json
(34-eval-harness/TASK_FORMAT.md, section 3).

    python -m harness.runner --out results.json
"""
import argparse
import importlib
import json
import os
import pkgutil
import urllib.parse

from harness.client import InfraError

ENV_KEYS = ("AGENTSWITCH_BASE_URL", "AGENTSWITCH_TOKEN",
            "AGENTSWITCH_INSTANCE", "AGENTSWITCH_RUN_ID")

# The live systems. A copy-only task never runs against these.
LIVE_HOSTS = {"agentswitch.theschoolofai.in", "class.agentswitch.theschoolofai.in"}


def is_live(env):
    host = urllib.parse.urlparse(env.get("AGENTSWITCH_BASE_URL") or "").hostname or ""
    return host in LIVE_HOSTS


def _load_failed(name, reason):
    """A task file that cannot be used still shows up, as an infrastructure failure."""
    def run(env):
        raise InfraError(f"task file {name}.py {reason}")
    return {"id": name, "title": f"{name} (could not be loaded)", "run": run}


def discover(pkg=None):
    """Every tNN_*.py module in harness/tasks, in file-name order. A module that fails
    to import, or has no valid TASK, is kept as a failing task, never dropped."""
    if pkg is None:
        from harness import tasks as pkg
    found = []
    for m in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if m.name.startswith("_"):
            continue
        try:
            task = getattr(importlib.import_module(f"{pkg.__name__}.{m.name}"), "TASK", None)
        except Exception as e:
            found.append(_load_failed(m.name, f"could not be loaded ({type(e).__name__})"))
            continue
        if not (isinstance(task, dict) and task.get("id") and task.get("title")
                and callable(task.get("run"))):
            found.append(_load_failed(m.name, "has no valid TASK (id, title, run)"))
            continue
        found.append(task)
    return found


def _check(r):
    """Validate what a task returned. Raises InfraError if it is malformed."""
    if not isinstance(r, dict):
        raise InfraError(f"task returned {type(r).__name__}, expected a dict")
    passed = r.get("passed")
    if not isinstance(passed, bool):
        raise InfraError("task returned no true/false 'passed'")
    score = r.get("score")
    if score is None:
        score = 1.0 if passed else 0.0
    elif isinstance(score, bool) or not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
        raise InfraError("task returned a score that is not a number from 0 to 1")
    if (passed and score == 0.0) or (not passed and score == 1.0):
        raise InfraError(f"task returned passed={passed} with score={float(score)}")
    return {"passed": passed, "score": float(score), "evidence": str(r.get("evidence", ""))}


def _fail(task_id, title, reason):
    return {"id": task_id, "title": title, "passed": False, "score": 0.0,
            "evidence": f"infrastructure: {reason}"}


def run_one(task, env):
    """One task's result, or None when a copy-only task is skipped on a local run."""
    instance = env.get("AGENTSWITCH_INSTANCE") or "unknown"
    task_id, title = f"{instance}:{task['id']}", task["title"]
    # A copy-only task (writes, missing or changed tokens) runs only inside a harness
    # run, which is always on a copy (TASK_FORMAT.md section 2), and never against a
    # live system. See README.md and CONTRIBUTING.md.
    if task.get("copy_only"):
        if not env.get("AGENTSWITCH_RUN_ID"):
            return None
        if is_live(env):
            return _fail(task_id, title, "refused: copy-only task, and "
                                         "AGENTSWITCH_BASE_URL is a live system")
    try:
        return {"id": task_id, "title": title, **_check(task["run"](env))}
    except InfraError as e:
        return _fail(task_id, title, str(e))
    except Exception as e:  # a bug in a task must show up, not be dropped
        return _fail(task_id, title, f"{type(e).__name__} in task")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seat 33 v1 suite")
    ap.add_argument("--out", default="results.json")
    args = ap.parse_args(argv)
    env = {k: os.environ.get(k) for k in ENV_KEYS}
    instance = env.get("AGENTSWITCH_INSTANCE") or "unknown"
    results, not_run = [], []
    for task in discover():
        r = run_one(task, env)
        if r is None:
            not_run.append(f"{instance}:{task['id']}")
        else:
            results.append(r)
    passed = sum(1 for r in results if r["passed"])
    summary = f"{instance}: {passed}/{len(results)} tasks passed"
    report = {"tasks": results, "summary": summary}
    if not_run:  # local runs only: a harness run always sets AGENTSWITCH_RUN_ID
        report["summary"] += (f"; {len(not_run)} copy-only task(s) not run "
                              "(local run, not a harness copy)")
        report["not_run"] = not_run
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for r in results:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['id']}  {r['evidence']}")
    for task_id in not_run:
        print(f"SKIP  {task_id}  copy-only task, local run")
    print(report["summary"])


if __name__ == "__main__":
    main()
