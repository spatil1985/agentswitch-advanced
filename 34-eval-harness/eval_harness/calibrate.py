"""Calibration: can our tasks fail at all? Reads saved trial records only: zero model and platform calls.

    python -m eval_harness --suite suites/seat31 --agent true --out runs/null.json   # a do-nothing run
    python -m eval_harness.calibrate --suite suites/seat31 --real runs/<real_run> --null runs/<null_run>

Two checks:
- Do-nothing baseline. `true` is an agent that does nothing. A task it passes cannot tell a real agent
  from no agent, so a pass there says nothing about the agent under test.
- Same output. Different prompts got byte-identical output: the agent probably ignored the prompt.

Time: one pass over the records (a hash each), so O(n) in the number of trial records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from eval_harness.scorer import score_trial
from eval_harness.suite import load_suite
from eval_harness.trial import TrialRecord


def load_records(run_dir: Path) -> list[TrialRecord]:
    return [TrialRecord.model_validate_json(p.read_text()) for p in sorted(run_dir.glob("*__*__t*.json"))]


def passes(run_dir: Path, suite_path: Path) -> dict[tuple[str, str], bool]:
    """(instance, task id) -> passed, rescored from disk with today's graders."""
    tasks = {t.id: t for t in load_suite(suite_path).tasks}
    return {
        (r.instance, r.task_id): score_trial(r, tasks[r.task_id]).passed
        for r in load_records(run_dir)
        if r.task_id in tasks
    }


def same_output_groups(run_dir: Path, task_ids: set[str] | None = None) -> list[list[str]]:
    """Groups of 2+ tasks on one system whose agent output was byte-identical (prompt probably ignored).
    `task_ids` limits it to one suite's tasks when a run folder holds several suites."""
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in load_records(run_dir):
        if task_ids is not None and r.task_id not in task_ids:
            continue
        if r.agent and r.agent.output_tail:
            digest = hashlib.sha256(r.agent.output_tail.encode()).hexdigest()
            groups[(r.instance, digest)].append(f"{r.instance}:{r.task_id}")
    return [sorted(ids) for ids in groups.values() if len(ids) > 1]


def calibrate(suite_path: Path, real_dir: Path, null_dir: Path) -> dict[str, Any]:
    real, null = passes(real_dir, suite_path), passes(null_dir, suite_path)
    rows = [
        {"id": f"{inst}:{task}", "real_passed": ok, "null_passed": null.get((inst, task))}
        for (inst, task), ok in sorted(real.items())
    ]
    null_passes = sum(1 for r in rows if r["null_passed"])
    same = same_output_groups(real_dir, {t.id for t in load_suite(suite_path).tasks})
    summary = (
        f"do-nothing agent passes {null_passes} of {len(rows)} tasks"
        + (" (these tasks cannot tell a real agent from no agent)" if null_passes else "")
        + f"; same output for different prompts: {sum(len(g) for g in same)} tasks in {len(same)} group(s)"
    )
    return {
        "tasks": len(rows),
        "null_passes": null_passes,
        "rows": rows,
        "same_output": same,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m eval_harness.calibrate", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--real", type=Path, required=True, help="run folder of the real agent")
    parser.add_argument("--null", type=Path, required=True, help="run folder of the do-nothing agent")
    parser.add_argument("--out", type=Path, help="also write the report as JSON here")
    args = parser.parse_args(argv)
    report = calibrate(args.suite, args.real, args.null)
    if not report["tasks"]:
        print(f"no trial records for this suite in {args.real}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))
    print(report["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
