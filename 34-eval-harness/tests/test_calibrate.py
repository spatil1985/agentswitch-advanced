"""Calibration: can a task fail at all? Hand-made trial records on disk, no model or platform calls.

- A do-nothing run (`--agent true`) that passes a task shows the task cannot tell a real agent from no agent.
- An agent that prints the same output for different prompts is probably ignoring the prompt.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.calibrate import calibrate, same_output_groups
from eval_harness.suite import Task, load_suite
from eval_harness.trial import AgentRun, TrialRecord, save_record

SEAT = Path(__file__).resolve().parent.parent
SUITE = SEAT / "suites" / "seat35"


def save(run_dir: Path, task: Task, output: str, changed: bool = False) -> None:
    ids = [f"p{i}" for i in range(task.targets.limit if task.targets else 0)]
    entities = sorted({str(e) for g in task.graders for e in g.params.get("entities", [])})
    row = {"name": "A"}
    record = TrialRecord(
        run_id=run_dir.name,
        instance="keystone",
        task_id=task.id,
        task_version=task.version,
        manifest={},
        targets=ids,
        before={i: {**row, "id": i} for i in ids},
        after={i: {**row, "id": i, "name": "B" if changed else "A"} for i in ids},
        writes_since_start={e: [] for e in entities},
        agent=AgentRun(command=["x"], exit_code=0, seconds=1.0, output_tail=output),
    )
    save_record(record, run_dir, [])


def test_tasks_the_do_nothing_agent_passes_are_flagged(tmp_path: Path) -> None:
    tasks = load_suite(SUITE).tasks
    for t in tasks:
        save(tmp_path / "null", t, "")
        save(tmp_path / "real", t, f"answer for {t.id}")
    report = calibrate(SUITE, tmp_path / "real", tmp_path / "null")
    assert report["null_passes"] == len(tasks) and report["tasks"] == len(tasks)
    assert all(r["null_passed"] for r in report["rows"])
    assert "do-nothing agent passes" in report["summary"]


def test_a_task_the_do_nothing_agent_fails_is_not_flagged(tmp_path: Path) -> None:
    task = load_suite(SUITE).tasks[0]
    save(tmp_path / "null", task, "", changed=True)  # a task whose clean state needs a change
    save(tmp_path / "real", task, "x")
    report = calibrate(SUITE, tmp_path / "real", tmp_path / "null")
    assert report["null_passes"] == 0 and not report["rows"][0]["null_passed"]


def test_same_output_for_different_prompts_is_flagged(tmp_path: Path) -> None:
    tasks = load_suite(SUITE).tasks
    for t in tasks:
        save(tmp_path / "real", t, "the same report every time")
    groups = same_output_groups(tmp_path / "real")
    assert len(groups) == 1 and len(groups[0]) == len(tasks)


def test_same_output_counts_only_the_suite_asked_for(tmp_path: Path) -> None:
    seat35 = load_suite(SUITE).tasks
    example = load_suite(SEAT / "suites" / "example").tasks
    for t in [*seat35, *example]:
        save(tmp_path / "real", t, "the same report every time")
    groups = same_output_groups(tmp_path / "real", {t.id for t in seat35})
    assert len(groups) == 1 and len(groups[0]) == len(seat35)


def test_different_outputs_are_not_grouped(tmp_path: Path) -> None:
    for t in load_suite(SUITE).tasks[:3]:
        save(tmp_path / "real", t, f"answer for {t.id}")
    assert same_output_groups(tmp_path / "real") == []


def test_report_is_written_as_json(tmp_path: Path) -> None:
    from eval_harness.calibrate import main

    task = load_suite(SUITE).tasks[0]
    save(tmp_path / "null", task, "")
    save(tmp_path / "real", task, "x")
    out = tmp_path / "calibration.json"
    args = ["--suite", str(SUITE), "--real", str(tmp_path / "real"), "--null", str(tmp_path / "null")]
    assert main([*args, "--out", str(out)]) == 0
    assert json.loads(out.read_text())["tasks"] == 1


def test_agent_override_replaces_the_suite_command() -> None:
    from eval_harness.__main__ import with_agent

    suite = load_suite(SUITE)
    assert with_agent(suite, "true").agent == "true"
    assert with_agent(suite, None).agent == suite.agent
