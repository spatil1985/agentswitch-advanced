"""Run the Seat 29 setup check and write results.json.

Format: 34-eval-harness/TASK_FORMAT.md. Evidence holds counts, yes/no answers and the
model's short answer about our own test images, never tokens or record contents.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import intake_checks, tasks

SECRET_SETTINGS = ("AGENTSWITCH_TOKEN", "OPENAI_API_KEY")
MAX_EVIDENCE_CHARS = 300


def clean(text: str) -> str:
    """An error message can quote what it was sent, so no setting's secret value may pass through."""
    for name in SECRET_SETTINGS:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, "[hidden]")
    return text[:MAX_EVIDENCE_CHARS]


def run_task(task, instance: str) -> dict:
    try:
        passed, evidence = task.run()
    except Exception as error:  # One task's failure must not lose the others.
        passed, evidence = False, f"infrastructure: {type(error).__name__}: {error}"
    return {
        "id": f"{instance}:{task.__name__}",
        "title": task.title,
        "passed": bool(passed),
        "score": 1.0 if passed else 0.0,
        "evidence": clean(str(evidence)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--only", choices=("setup", "intake"), help="run one group of checks; the harness runs both")
    args = parser.parse_args(argv)

    instance = os.environ.get("AGENTSWITCH_INSTANCE") or "unknown"
    groups = {"setup": tasks.ALL, "intake": intake_checks.ALL}
    chosen = groups[args.only] if args.only else tasks.ALL + intake_checks.ALL
    results = [run_task(task, instance) for task in chosen]
    passed = sum(row["passed"] for row in results)
    with open(args.out, "w", encoding="utf-8") as out:
        json.dump({"tasks": results, "summary": f"{instance}: {passed}/{len(results)} tasks passed"}, out, indent=2)
    print(f"{instance}: {passed}/{len(results)} tasks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
