"""results.json in the course format (TASK_FORMAT.md), rewritten atomically after every row.

Atomic: written to a temporary file and then renamed, so a crash or a time-out never leaves a half-written
file, and the rows finished so far always survive.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, StrictBool


class ResultRow(BaseModel):
    id: str
    title: str
    passed: StrictBool
    score: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(max_length=500)


class ResultsFile(BaseModel):
    tasks: list[ResultRow]
    summary: str


class ResultsWriter:
    def __init__(self, path: Path, instance: str) -> None:
        self.path, self.instance, self.rows = path, instance, list[ResultRow]()

    def add(self, row: ResultRow) -> None:
        self.rows.append(row)
        self.write()

    def write(self) -> None:
        passed = sum(r.passed for r in self.rows)
        body = ResultsFile(
            tasks=self.rows, summary=f"{self.instance}: {passed}/{len(self.rows)} tasks passed"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(body.model_dump_json(indent=1))
        os.replace(tmp, self.path)
