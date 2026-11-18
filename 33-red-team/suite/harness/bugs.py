"""Reads ../bug-status.json, used by tasks 9 and 10 (PLAN.md, Definition of done, item 1)."""
import json
import os

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bug-status.json")
STATUSES = {"new", "open", "fixed", "wont_fix"}


def status(bug_id):
    """The recorded status of a bug, e.g. status("BUG-33-001") -> "new"."""
    with open(PATH, encoding="utf-8") as f:
        bugs = json.load(f)
    s = bugs[bug_id]["status"]
    if s not in STATUSES:
        raise ValueError(f"{bug_id}: unknown status {s!r}")
    return s
