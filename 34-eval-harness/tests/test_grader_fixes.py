"""Fixes from the 17 Nov review. Hand-made trial records, no model or platform calls.

1. A read error after the run is "could not check", not "gone".
2. An agent that crashes or times out is still graded, so a write before the crash is caught.
3. Every graded task can fail: a clean record passes, a bad record fails, for every task in every suite.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from eval_harness.graders import Verdict, records_unchanged
from eval_harness.platform import PlatformError
from eval_harness.scorer import row_for, score_trial
from eval_harness.suite import Task, load_suite
from eval_harness.trial import GONE, AgentRun, TrialRecord, snapshot

SEAT = Path(__file__).resolve().parent.parent
SUITES = sorted(p.parent for p in (SEAT / "suites").glob("*/suite.toml"))
ROW = {"id": "a1b2c3d4-x", "name": "Acme", "updated_at": "2026-11-01T10:00:00"}


def make_record(task: Task, **changes: Any) -> TrialRecord:
    """A clean trial of `task`: targets untouched, nothing written, the agent exited 0."""
    entities = sorted({str(e) for g in task.graders for e in g.params.get("entities", [])})
    ids = [f"{ROW['id']}{i}" for i in range(task.targets.limit if task.targets else 0)]
    base = TrialRecord(
        run_id="r1",
        instance="keystone",
        task_id=task.id,
        task_version=task.version,
        manifest={},
        targets=ids,
        before={i: {**ROW, "id": i} for i in ids},
        after={i: {**ROW, "id": i} for i in ids},
        writes_since_start={e: [] for e in entities},
        agent=AgentRun(command=["x"], exit_code=0, seconds=1.0),
    )
    return base.model_copy(update=changes)


def make_bad(task: Task) -> TrialRecord:
    """What each grader exists to catch: every target edited, one row written in every watched entity."""
    clean = make_record(task)
    return clean.model_copy(
        update={
            "after": {i: {**row, "name": "Changed"} for i, row in clean.after.items() if row},
            "writes_since_start": {e: [{"id": "w1"}] for e in clean.writes_since_start},
        }
    )


def a_task() -> Task:
    return load_suite(SEAT / "suites" / "example").tasks[0]


# 1. read error after the run ---------------------------------------------------------------------------


def test_read_error_after_the_run_is_unevaluated_not_gone() -> None:
    task = a_task()
    clean = make_record(task)
    first = clean.targets[0]
    result = records_unchanged(clean.model_copy(update={"after": {**clean.after, first: None}}), {})
    assert result.verdict is Verdict.UNEVALUATED and "could not read after" in result.reason


def test_a_record_the_platform_says_is_gone_still_fails() -> None:
    task = a_task()
    clean = make_record(task)
    first = clean.targets[0]
    result = records_unchanged(clean.model_copy(update={"after": {**clean.after, first: dict(GONE)}}), {})
    assert result.verdict is Verdict.REVISE and "gone" in result.reason


class _Reader:
    def __init__(self, status: int | None) -> None:
        self.status = status

    async def get(self, entity: str, record_id: str) -> dict[str, Any]:
        if self.status is None:
            return {"id": record_id}
        raise PlatformError(f"/api/{entity}/{record_id}", self.status, "x")


@pytest.mark.parametrize(("status", "expected"), [(404, GONE), (500, None), (None, {"id": "r"})])
def test_snapshot_tells_not_found_apart_from_a_failed_read(status: int | None, expected: object) -> None:
    rows = asyncio.run(snapshot(_Reader(status), "Party", ["r"]))  # type: ignore[arg-type]
    assert rows["r"] == expected


# 2. crash or time-out is still graded ------------------------------------------------------------------


def test_agent_that_writes_then_crashes_is_blamed_for_the_write() -> None:
    task = a_task()
    crashed = make_bad(task).model_copy(
        update={
            "agent": AgentRun(command=["x"], exit_code=3, seconds=2.0),
            "infrastructure": "agent exited with code 3: boom",
        }
    )
    score = score_trial(crashed, task)
    assert not score.passed and score.outcome is Verdict.REVISE and score.integrity == "violated"
    evidence = row_for(crashed, task, score).evidence
    assert evidence.startswith("infrastructure:") and "integrity=violated" in evidence


def test_clean_crash_stays_plain_infrastructure() -> None:
    task = a_task()
    crashed = make_record(task).model_copy(
        update={
            "agent": AgentRun(command=["x"], exit_code=3, seconds=2.0),
            "infrastructure": "agent exited with code 3: boom",
        }
    )
    score = score_trial(crashed, task)
    assert not score.passed and score.outcome is Verdict.UNEVALUATED and score.value == 0.0


def test_trial_that_never_started_the_agent_is_not_graded() -> None:
    task = a_task()
    never = make_record(task).model_copy(update={"agent": None, "infrastructure": "model settings missing"})
    score = score_trial(never, task)
    assert score.graders == [] and score.integrity == "not checked"


# 3. every graded task can fail -------------------------------------------------------------------------


@pytest.mark.parametrize("suite_dir", SUITES, ids=lambda p: p.name)
def test_every_task_passes_clean_and_fails_bad(suite_dir: Path) -> None:
    for task in load_suite(suite_dir).tasks:
        assert score_trial(make_record(task), task).passed, f"{task.id}: clean record should pass"
        bad = score_trial(make_bad(task), task)
        assert bad.outcome is Verdict.REVISE, f"{task.id}: bad record should fail, got {bad.outcome}"
