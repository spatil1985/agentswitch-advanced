"""Re-grade and re-score saved trial records. Zero model calls, zero platform calls.

    python -m eval_harness.rescore runs/<run_id> --suite suites/example --out runs/<run_id>/rescored.json

Use it after changing a grader or the scorer: the trial records are the evidence, and the score is one reading
of them (session 18: "the raw run survives the score"). A record whose task version differs from the suite's
is still rescored, and the mismatch is printed so nobody mistakes it for a like-for-like comparison.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eval_harness.results import ResultsWriter
from eval_harness.scorer import row_for, score_trial
from eval_harness.suite import load_suite
from eval_harness.trial import TrialRecord


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m eval_harness.rescore", description=__doc__.split("\n")[0]
    )
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    tasks = {t.id: t for t in load_suite(args.suite).tasks}
    records = [
        TrialRecord.model_validate_json(p.read_text()) for p in sorted(args.run_dir.glob("*__*__t*.json"))
    ]
    if not records:
        print(f"no trial records in {args.run_dir}", file=sys.stderr)
        return 1
    writer = ResultsWriter(args.out, records[0].instance)
    for record in records:
        task = tasks.get(record.task_id)
        if task is None:
            print(f"skipped {record.task_id}: not in this suite", file=sys.stderr)
            continue
        if task.version != record.task_version:
            print(f"note: {record.task_id} recorded at v{record.task_version}, suite has v{task.version}")
        writer.add(row_for(record, task, score_trial(record, task)))
    print(f"rescored {len(writer.rows)} trial record(s) from disk, 0 model calls -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
