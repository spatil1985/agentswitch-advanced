"""Run the eval harness on your computer exactly as the course runner would. Read-only on live data.

    uv run python scripts/run_local.py --instance keystone -- --suite suites/example
    uv run python scripts/run_local.py --instance both     -- --suite suites/example --out runs/results.json

For each system it:
  1. gets a token from the local cache (or logs in once) via scripts/local_auth.py;
  2. sets AGENTSWITCH_BASE_URL, AGENTSWITCH_TOKEN, AGENTSWITCH_INSTANCE and a fresh AGENTSWITCH_RUN_ID,
     and passes the OPENAI_* model settings from .env through unchanged;
  3. starts `python -m eval_harness <your arguments>` as a child process, as the course runner does.
The eval harness itself never reads .env and never logs in, so local and platform runs behave the same.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from local_auth import SEAT_DIR, SYSTEMS, LoginFailed, get_token, load_local_settings

PASS_THROUGH_PREFIX = "OPENAI_"  # model settings in .env that the harness and the agent need


def out_path(args: list[str], system: str, run_id: str, many: bool) -> list[str]:
    """Give each system its own results file: default runs/<run_id>/results.json; with --out X and several
    systems, X becomes X-<system>."""
    if "--out" not in args:
        return [*args, "--out", str(Path("runs") / run_id / "results.json")]
    if not many:
        return args
    i = args.index("--out") + 1
    path = Path(args[i])
    return [*args[:i], str(path.with_name(f"{path.stem}-{system}{path.suffix}")), *args[i + 1 :]]


def child_environment(token: str, base_url: str, system: str, run_id: str) -> dict[str, str]:
    # AS_* (email, passwords) are for logging in here only; the harness must never see them.
    env = {k: v for k, v in os.environ.items() if not k.startswith("AS_")}
    for key, value in dotenv_values(SEAT_DIR / ".env").items():
        if key.startswith(PASS_THROUGH_PREFIX) and value and key not in env:
            env[key] = value
    env |= {
        "AGENTSWITCH_BASE_URL": base_url,
        "AGENTSWITCH_TOKEN": token,
        "AGENTSWITCH_INSTANCE": system,
        "AGENTSWITCH_RUN_ID": run_id,
    }
    return env


def main() -> int:
    parser = argparse.ArgumentParser(prog="scripts/run_local.py", description="Run the eval harness locally.")
    parser.add_argument("--instance", choices=[*SYSTEMS, "both"], required=True)
    parser.add_argument("harness_args", nargs=argparse.REMAINDER, help="after --: arguments for eval_harness")
    args = parser.parse_args()
    harness_args = [a for a in args.harness_args if a != "--"]
    settings = load_local_settings()
    if settings is None:
        return 2
    systems = list(SYSTEMS) if args.instance == "both" else [args.instance]
    for system in systems:
        try:
            token = asyncio.run(get_token(settings, system))
        except LoginFailed as e:
            print(f"stopped: {e}. Check AS_EMAIL and AS_{system.upper()}_PASSWORD in .env.", file=sys.stderr)
            return 2
        run_id = f"local-{system}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
        command = [
            sys.executable,
            "-m",
            "eval_harness",
            *out_path(harness_args, system, run_id, len(systems) > 1),
        ]
        env = child_environment(token, settings.url(system), system, run_id)
        print(f"== {system}: run {run_id}", flush=True)
        subprocess.run(command, cwd=SEAT_DIR, env=env, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
