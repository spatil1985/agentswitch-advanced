"""Run a suite against the agent under test on one system, and write results.json.

    python -m eval_harness --suite suites/example --out results.json

Reads process environment only (AGENTSWITCH_*, OPENAI_*): the course runner sets these on the platform, and
scripts/run_local.py sets the same ones on your computer. Every problem becomes a row, so results.json is
always written, and the exit code is always 0: the runner scores the file, not the exit code.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from eval_harness.platform import PlatformError, PlatformReader
from eval_harness.results import ResultRow, ResultsWriter
from eval_harness.scorer import row_for, score_trial
from eval_harness.settings import HarnessSettings, SettingsMissing, load_settings
from eval_harness.suite import Suite, load_suite
from eval_harness.trial import SEAT_DIR, TrialRecord, run_trial, save_record, scrub

RUNS_DIR = SEAT_DIR / "runs"


def infrastructure_rows(suite: Suite, instance: str, reason: str) -> list[ResultRow]:
    return [
        ResultRow(
            id=f"{instance}:{t.id}",
            title=t.title,
            passed=False,
            score=0.0,
            evidence=f"infrastructure: {reason}"[:500],
        )
        for t in suite.tasks
    ]


async def run_suite(suite: Suite, settings: HarnessSettings, out: Path) -> None:
    instance = settings.agentswitch_instance
    run_id = settings.agentswitch_run_id or f"local-{instance}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    run_dir, writer, secrets = RUNS_DIR / run_id, ResultsWriter(out, instance), settings.secrets()
    async with PlatformReader(settings.base_url, settings.agentswitch_token.get_secret_value()) as platform:
        try:
            me = (
                await platform.whoami()
            )  # login check before any task: a dead token never looks like a clean run
        except PlatformError as e:
            for row in infrastructure_rows(suite, instance, f"login check failed: {e}"):
                writer.add(row)
            return
        for task in suite.tasks:
            try:
                record = await run_trial(suite, task, settings, platform, me, run_id)
            except Exception as e:
                record = TrialRecord(
                    run_id=run_id,
                    instance=instance,
                    task_id=task.id,
                    task_version=task.version,
                    manifest={},
                    infrastructure=f"harness error: {type(e).__name__}: {e}",
                )
            record = save_record(record, run_dir, secrets)  # saved BEFORE scoring; we score what was saved
            writer.add(row_for(record, task, score_trial(record, task)))
    passed = sum(r.passed for r in writer.rows)
    print(f"{instance}: {passed}/{len(writer.rows)} passed; trial records in {run_dir}")


def with_agent(suite: Suite, agent: str | None) -> Suite:
    """The suite with another agent command (the manifest of each trial records which one ran)."""
    return suite.model_copy(update={"agent": agent}) if agent else suite


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m eval_harness", description=__doc__.split("\n")[0])
    parser.add_argument("--suite", type=Path, required=True, help="suite folder or suite.toml")
    parser.add_argument("--out", type=Path, default=Path("results.json"), help="where to write results.json")
    parser.add_argument(
        "--agent", help="run this command instead of the suite's agent; `true` is the do-nothing baseline"
    )
    args = parser.parse_args()
    suite = with_agent(load_suite(args.suite), args.agent)
    try:
        settings = load_settings()
    except SettingsMissing as e:
        writer = ResultsWriter(args.out, "setup")
        for row in infrastructure_rows(suite, "setup", str(e)):
            writer.add(row)
        print(f"setup problem: {e}", file=sys.stderr)
        return 0
    try:
        asyncio.run(run_suite(suite, settings, args.out))
    except Exception as e:
        writer = ResultsWriter(args.out, settings.agentswitch_instance)
        for row in infrastructure_rows(
            suite, settings.agentswitch_instance, f"harness crashed: {type(e).__name__}"
        ):
            writer.add(row)
        print(scrub(f"harness crashed: {type(e).__name__}: {e}", settings.secrets()), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
