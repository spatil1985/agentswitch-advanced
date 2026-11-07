"""End-to-end tests against a fake platform and a fake model. Run from the repo root:

    python -m unittest harness.test_setup_check
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN, KEY = "fake-seat-token-abc123", "fake-model-key-xyz789"


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        state = self.server.state
        if self.path == "/api/mcp":
            name, arguments = body["params"]["name"], body["params"]["arguments"]
            state["tools"].append(name)
            if name == "tools.describe":
                result = {"results": [{"name": n, "risk_class": state["labels"].get(n, "WRITE")} for n in arguments["names"]]}
            elif name == "Bill.list":
                result = {"total": state["bills"], "items": []}
            else:
                state["bills"] += state["submit_adds"]
                result = {"ok": True}
            self._send(200, {"jsonrpc": "2.0", "id": body["id"],
                             "result": {"content": [{"type": "text", "text": json.dumps(result)}]}})
            return
        has_image = isinstance(body["messages"][0]["content"], list)
        state["model_calls"].append("image" if has_image else "text")
        if has_image and state["image_status"] != 200:
            self._send(state["image_status"], {"error": {"message": "images not supported"}})
        elif not has_image and state["text_status"] != 200:
            self._send(state["text_status"], {"error": {"message": "bad key " + KEY}})
        else:
            self._send(200, {"choices": [{"message": {"content": state["reply"] if has_image else "ok"}}]})


class SetupCheck(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), Fake)
        self.server.state = {"tools": [], "model_calls": [], "bills": 7, "submit_adds": 0, "reply": "Red.",
                             "image_status": 200, "text_status": 200, "labels": {"Bill.list": "READ", "Bill.submit": "WRITE"}}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = Path(folder.name) / "results.json"
        url = f"http://127.0.0.1:{self.server.server_port}"
        self.env = {key: value for key, value in os.environ.items() if not key.startswith(("AGENTSWITCH_", "OPENAI_"))}
        self.env.update(AGENTSWITCH_BASE_URL=url, AGENTSWITCH_TOKEN=TOKEN, AGENTSWITCH_INSTANCE="keystone",
                        AGENTSWITCH_RUN_ID="run-1", OPENAI_BASE_URL=url + "/v1", OPENAI_API_KEY=KEY, OPENAI_MODEL="m")

    def run_check(self):
        done = subprocess.run([sys.executable, "-m", "harness.runner", "--out", str(self.out)], cwd=ROOT, env=self.env,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        results = json.loads(self.out.read_text(encoding="utf-8"))
        return results, {row["id"].split(":")[1]: row for row in results["tasks"]}

    def test_a_healthy_run_follows_the_format(self):
        results, tasks = self.run_check()
        self.assertEqual(results["summary"], "keystone: 5/5 tasks passed")
        for row in results["tasks"]:
            self.assertTrue(row["id"].startswith("keystone:"), row["id"])
            self.assertEqual(set(row), {"id", "title", "passed", "score", "evidence"})
            self.assertEqual(row["score"], 1.0)
        self.assertIn("images=accepted; read_correctly=True", tasks["model_accepts_images"]["evidence"])

    def test_the_prefix_comes_from_the_run(self):
        self.env["AGENTSWITCH_INSTANCE"] = "suryodaya"
        results, _ = self.run_check()
        self.assertTrue(all(row["id"].startswith("suryodaya:") for row in results["tasks"]))

    def test_bill_submit_is_refused_and_never_sent(self):
        _, tasks = self.run_check()
        self.assertTrue(tasks["guard_refuses_posting"]["passed"])
        self.assertIn("refused=True; sent=False", tasks["guard_refuses_posting"]["evidence"])
        self.assertNotIn("Bill.submit", self.server.state["tools"])

    def test_a_posting_call_that_goes_through_fails_the_check(self):
        self.server.state["labels"]["Bill.submit"] = "READ"
        self.server.state["submit_adds"] = 1
        _, tasks = self.run_check()
        self.assertFalse(tasks["guard_refuses_posting"]["passed"])
        self.assertIn("refused=False; sent=True; bills_before=7; bills_after=8", tasks["guard_refuses_posting"]["evidence"])

    def test_a_model_that_refuses_images_is_a_clear_answer(self):
        self.server.state["image_status"] = 400
        _, tasks = self.run_check()
        self.assertTrue(tasks["model_accepts_images"]["passed"])
        self.assertIn("images=refused; http=400", tasks["model_accepts_images"]["evidence"])

    def test_accepting_an_image_without_reading_it_shows(self):
        self.server.state["reply"] = "Blue."
        _, tasks = self.run_check()
        self.assertIn("read_correctly=False", tasks["model_accepts_images"]["evidence"])

    def test_a_broken_model_is_an_infrastructure_failure(self):
        self.server.state["text_status"] = 401
        _, tasks = self.run_check()
        self.assertFalse(tasks["model_accepts_images"]["passed"])
        self.assertIn("infrastructure", tasks["model_accepts_images"]["evidence"])
        self.assertEqual(self.server.state["model_calls"], ["text"])

    def test_missing_settings_are_named_and_the_rest_still_run(self):
        del self.env["OPENAI_API_KEY"]
        results, tasks = self.run_check()
        self.assertEqual(len(results["tasks"]), 5)
        self.assertFalse(tasks["system_and_settings"]["passed"])
        self.assertIn("missing_settings=OPENAI_API_KEY", tasks["system_and_settings"]["evidence"])
        self.assertIn("infrastructure", tasks["model_accepts_images"]["evidence"])
        self.assertTrue(tasks["login_and_read"]["passed"])

    def test_a_dead_platform_costs_only_its_own_tasks(self):
        self.env["AGENTSWITCH_BASE_URL"] = "http://127.0.0.1:9"
        _, tasks = self.run_check()
        self.assertIn("infrastructure", tasks["login_and_read"]["evidence"])
        self.assertTrue(tasks["packages_installed"]["passed"])

    def test_no_secret_reaches_the_results(self):
        self.server.state["text_status"] = 401
        self.run_check()
        text = self.out.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(KEY, text)

    def test_secrets_quoted_in_an_error_are_hidden(self):
        from harness.runner import clean
        os.environ["OPENAI_API_KEY"] = KEY
        self.addCleanup(os.environ.pop, "OPENAI_API_KEY")
        self.assertEqual(clean(f"bad key {KEY}"), "bad key [hidden]")

    def test_the_harness_file_matches_the_format(self):
        with open(ROOT / "agentswitch-harness.toml", "rb") as handle:
            config = tomllib.load(handle)
        self.assertEqual(set(config), {"install", "run", "results", "instances", "timeout_minutes"})
        self.assertLessEqual(config["timeout_minutes"], 30)
        self.assertEqual(config["results"], "results.json")


if __name__ == "__main__":
    unittest.main()
