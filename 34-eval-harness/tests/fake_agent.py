"""A stand-in agent for the run-path tests: a real separate process, no model and no platform calls.

    python tests/fake_agent.py --mode ok|crash|sleep|leak --prompt "..."

`ok` reports what it received from the harness in its AGENT_RESULT line: the names of its environment
variables, whether its token is the one the test injected, and its model endpoint. Values that would be
scrubbed as secrets are reported as booleans, so the scrubber cannot hide a leak.
`leak` is a careless agent: it prints its token on its last line and fails, as a crashing agent might.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

INJECTED_TOKEN = "tok-injected-for-tests"  # tests/test_run_path.py sets AGENTSWITCH_TOKEN to this


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["ok", "crash", "sleep", "leak"], required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    if args.mode == "crash":
        print("model problem: fake failure", file=sys.stderr)
        return 3
    if args.mode == "leak":
        print(f"login failed with token {os.environ.get('AGENTSWITCH_TOKEN')}", file=sys.stderr)
        return 2
    if args.mode == "sleep":
        time.sleep(30)
    result = {
        "claim": "refused",
        "env_keys": sorted(os.environ),
        "token_is_injected": os.environ.get("AGENTSWITCH_TOKEN") == INJECTED_TOKEN,
        "model_url": os.environ.get("OPENAI_BASE_URL"),
    }
    print("I will not merge these without a person's approval.")
    print("AGENT_RESULT " + json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
