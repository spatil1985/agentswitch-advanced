"""Suites and tasks, read from suites/<name>/suite.toml.

A person writes every graded task by hand (course rule). Only suites with `graded = false` may be written by a
coding agent, and only as plumbing checks.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TaskKind = Literal["normal", "refusal", "integrity", "missing_resource"]


class GraderSpec(BaseModel):
    """Which grader to run, plus its settings (any extra keys are passed to the grader)."""

    model_config = ConfigDict(extra="allow")
    name: str

    @property
    def params(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


class Targets(BaseModel):
    """Records picked at run time from live data, so tasks do not go stale."""

    entity: str
    limit: int = Field(default=1, ge=1, le=20)


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9_.-]+$")
    title: str
    kind: TaskKind
    exercises: list[str]  # what a failure here would reveal (session 18: every property needs a task)
    version: int = Field(ge=1)
    author: str
    targets: Targets | None = None
    prompt: str
    graders: list[GraderSpec] = Field(min_length=1)
    fails_if: str  # the attack: what would make this task fail

    def render_prompt(self, target_ids: list[str]) -> str:
        return self.prompt.replace("{target_ids}", ", ".join(target_ids))


class Suite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    graded: bool
    agent: str  # the agent-under-test command; the harness appends --prompt "<text>"
    task_minutes: float = Field(default=5, gt=0, le=25)
    corrections: list[str] = []  # relabelled tasks are recorded here, never fixed silently
    tasks: list[Task] = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Suite:
        ids = [t.id for t in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError(f"task ids repeat in suite {self.name!r}")
        return self


def load_suite(path: Path) -> Suite:
    """Load a suite file, or a folder holding suite.toml."""
    file = path / "suite.toml" if path.is_dir() else path
    data = tomllib.loads(file.read_text())
    return Suite.model_validate({**data.get("suite", {}), "tasks": data.get("tasks", [])})
