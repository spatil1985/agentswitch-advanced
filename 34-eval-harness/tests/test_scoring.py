"""Graders, scorer and results.json. Hand-made trial records, no model or platform calls."""

import json
from pathlib import Path

import pytest

from eval_harness.graders import Verdict, records_unchanged, worst
from eval_harness.results import ResultsWriter
from eval_harness.scorer import row_for, score_trial
from eval_harness.suite import Suite, Task, load_suite
from eval_harness.trial import AgentRun, TrialRecord, infrastructure_problem, parse_reported

SEAT = Path(__file__).resolve().parent.parent


@pytest.fixture
def task() -> Task:
    return load_suite(SEAT / "suites" / "example").tasks[0]


def record(**changes: object) -> TrialRecord:
    row = {"id": "a1b2c3d4-x", "name": "Acme", "updated_at": "2026-11-01T10:00:00"}
    base = TrialRecord(
        run_id="r1",
        instance="suryodaya",
        task_id="example.merge_two_parties_refused",
        task_version=1,
        manifest={},
        targets=[row["id"]],
        before={row["id"]: row},
        after={row["id"]: dict(row)},
        writes_since_start={"Party": []},
        agent=AgentRun(
            command=["x"], exit_code=0, seconds=3.0, reported={"claim": "refused", "steps": 2, "tokens": 900}
        ),
    )
    return base.model_copy(update=changes)


def test_worst_prefers_revise_then_unevaluated() -> None:
    assert worst([Verdict.APPROVE, Verdict.UNEVALUATED]) is Verdict.UNEVALUATED
    assert worst([Verdict.UNEVALUATED, Verdict.REVISE]) is Verdict.REVISE
    assert worst([]) is Verdict.UNEVALUATED


def test_untouched_records_pass_with_honest_refusal(task: Task) -> None:
    score = score_trial(record(), task)
    assert score.passed and score.integrity == "clean" and score.honesty == "honest_refusal"
    row = row_for(record(), task, score)
    assert row.id == "suryodaya:example.merge_two_parties_refused" and row.score == 1.0


def test_changed_record_fails_and_names_the_field(task: Task) -> None:
    changed = record(
        after={"a1b2c3d4-x": {"id": "a1b2c3d4-x", "name": "Merged", "updated_at": "2026-11-07T10:00:00"}}
    )
    result = records_unchanged(changed, {})
    assert result.verdict is Verdict.REVISE and "name" in result.reason


def test_write_by_our_login_breaks_integrity(task: Task) -> None:
    score = score_trial(record(writes_since_start={"Party": [{"id": "z"}]}), task)
    assert not score.passed and score.integrity == "violated"


def test_unreadable_writes_are_unevaluated_never_a_pass(task: Task) -> None:
    score = score_trial(record(writes_since_start={"Party": None}), task)
    assert score.outcome is Verdict.UNEVALUATED and not score.passed


def test_agent_crash_is_infrastructure_not_an_agent_result(task: Task) -> None:
    crashed = AgentRun(command=["x"], exit_code=3, output_tail="model problem: NotFoundError")
    reason = infrastructure_problem(crashed)
    assert reason and "code 3" in reason
    row = row_for(record(infrastructure=reason), task, score_trial(record(infrastructure=reason), task))
    assert not row.passed and row.evidence.startswith("infrastructure:") and row.score == 0.0


def test_agent_result_line_is_parsed_from_the_end() -> None:
    out = 'thinking...\nAGENT_RESULT {"claim": "done", "steps": 3}\n'
    assert parse_reported(out) == {"claim": "done", "steps": 3}
    assert parse_reported("no line here") is None


def test_results_file_is_course_format_and_atomic(tmp_path: Path, task: Task) -> None:
    writer = ResultsWriter(tmp_path / "results.json", "keystone")
    writer.add(row_for(record(), task, score_trial(record(), task)))
    data = json.loads((tmp_path / "results.json").read_text())
    assert set(data) == {"tasks", "summary"} and data["summary"] == "keystone: 1/1 tasks passed"
    assert set(data["tasks"][0]) == {"id", "title", "passed", "score", "evidence"}
    assert not list(tmp_path.glob("*.tmp"))


def test_example_suite_is_marked_plumbing_only() -> None:
    suite: Suite = load_suite(SEAT / "suites" / "example")
    assert suite.graded is False and all("plumbing" in t.author for t in suite.tasks)
