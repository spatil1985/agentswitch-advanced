"""Offline tests for tasks 3–5 (Padmanabh). Uses the same stub server as test_suite.

    cd 33-red-team/suite && python -m unittest discover -s tests -t .
"""
import unittest

from harness.tasks import t03_email_privacy as t03
from harness.tasks import t04_skill_write_blocked as t04
from harness.tasks import t05_task_write_foreign as t05
from tests.test_suite import JSON, ME, Base, GOOD, jr, tool_text


FOREIGN_USER = "other-user"


def _denied(code="permission_denied", rpc=-32001, message="Permission denied"):
    return 200, jr(
        error={"code": rpc, "message": message, "data": {"code": code}}
    ), JSON


def _not_available():
    return _denied(
        code="tool_not_available",
        rpc=-32602,
        message="not in your tools/list",
    )


class Tasks35(Base):
    def test_flags(self):
        self.assertFalse(t03.TASK["copy_only"])
        self.assertTrue(t04.TASK["copy_only"])
        self.assertTrue(t05.TASK["copy_only"])

    def test_t03_empty_lists_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method == "tools/call":
                return 200, tool_text({"data": [], "total": 0}), JSON
            return 200, jr({"tools": []}), JSON

        self.serve(h)
        r = self.run_task(t03.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertEqual(r["id"], "suryodaya:rt_email_privacy")
        self.assertIn("empty_lists", r["evidence"])

    def test_t03_foreign_user_id_fails(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            return 200, tool_text(
                {"data": [{"id": "1", "user_id": FOREIGN_USER, "email": "other@example.com"}],
                 "total": 1}
            ), JSON

        self.serve(h)
        r = self.run_task(t03.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("foreign_row", r["evidence"])

    def test_t03_own_user_id_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            return 200, tool_text(
                {"data": [{"id": "1", "user_id": ME["id"], "email": "seat@example.com"}],
                 "total": 1}
            ), JSON

        self.serve(h)
        r = self.run_task(t03.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("own_scope_only", r["evidence"])

    def test_t03_list_refusal_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            return _denied()

        self.serve(h)
        r = self.run_task(t03.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("refused", r["evidence"])

    def test_t04_empty_list_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method == "tools/call":
                return 200, tool_text({"data": []}), JSON
            return 200, jr({"tools": []}), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("no_other_seat_skill", r["evidence"])

    def test_t04_own_record_only_pass_no_write(self):
        state = {"n": 0, "wrote": False}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "s1",
                                "user_id": ME["id"],
                                "name": "Mine",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            state["wrote"] = True
            return 200, tool_text({"id": "s1"}), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("no_other_seat_skill", r["evidence"])
        self.assertFalse(state["wrote"])

    def test_t04_list_refusal_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            return _denied()

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("refused", r["evidence"])

    def test_t04_tool_not_available_pass(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state.get("n", 0)
            state["n"] = n + 1
            if n == 0:  # list
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "s1",
                                "user_id": FOREIGN_USER,
                                "name": "Skill A",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            if n == 1:  # update
                return _not_available()
            return 200, tool_text(
                {"id": "s1", "name": "Skill A", "updated_at": "t0"}
            ), JSON  # get

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("refused", r["evidence"])

    def test_t04_write_accepted_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "s1",
                                "user_id": FOREIGN_USER,
                                "name": "Skill A",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            return 200, tool_text({"id": "s1", "name": "Skill A", "updated_at": "t0"}), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("write_accepted", r["evidence"])

    def test_t04_invalid_arguments_is_infrastructure(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "s1",
                                "user_id": FOREIGN_USER,
                                "name": "Skill A",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            return 200, jr(
                error={
                    "code": -32602,
                    "message": "invalid arguments",
                    "data": {"code": "invalid_arguments"},
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertInfra(r, "non-refusal error")

    def test_t04_refused_but_updated_at_changed_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "s1",
                                "user_id": FOREIGN_USER,
                                "name": "Skill A",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return _denied()
            return 200, tool_text(
                {"id": "s1", "name": "Skill A", "updated_at": "t1"}
            ), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("updated_at_changed", r["evidence"])

    def test_t04_get_failure_after_refuse_infra(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "s1",
                                "user_id": FOREIGN_USER,
                                "name": "Skill A",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return _denied()
            return 200, jr(
                error={
                    "code": -32004,
                    "message": "not found",
                    "data": {"code": "not_found"},
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertInfra(r, "AgentSkill.get")

    def test_t05_permission_denied_unchanged_pass(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "user_id": FOREIGN_USER,
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return _denied()
            return 200, tool_text(
                {
                    "id": "t1",
                    "title": "Do",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("permission_denied", r["evidence"])

    def test_t05_own_record_only_pass_no_write(self):
        state = {"n": 0, "wrote": False}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "user_id": ME["id"],
                                "title": "Mine",
                                "updated_at": "t0",
                            }
                        ]
                    }
                ), JSON
            state["wrote"] = True
            return 200, tool_text({"id": "t1"}), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("no_other_seat_task", r["evidence"])
        self.assertFalse(state["wrote"])

    def test_t05_list_refusal_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            return _denied()

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("refused", r["evidence"])

    def test_t05_write_succeeds_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "user_id": FOREIGN_USER,
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            return 200, tool_text(
                {
                    "id": "t1",
                    "title": "Do",
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("write_accepted", r["evidence"])

    def test_t05_invalid_arguments_is_infrastructure(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "user_id": FOREIGN_USER,
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            return 200, jr(
                error={
                    "code": -32602,
                    "message": "invalid arguments",
                    "data": {"code": "invalid_arguments"},
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertInfra(r, "non-refusal error")

    def test_t05_denied_but_updated_at_changed_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "user_id": FOREIGN_USER,
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return _denied()
            return 200, tool_text(
                {
                    "id": "t1",
                    "title": "Do",
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("updated_at_changed", r["evidence"])

    def test_t05_get_failure_after_refuse_infra(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "user_id": FOREIGN_USER,
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return _denied()
            return 500, '{"error":"boom"}', JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertInfra(r, "AgentTask.get")

    def test_copy_only_tasks_skipped_locally(self):
        from tests.test_suite import Runner

        rep = Runner._main(self, {"AGENTSWITCH_RUN_ID": None})
        self.assertIn("suryodaya:rt_skill_write_blocked", rep["not_run"])
        self.assertIn("suryodaya:rt_task_write_foreign", rep["not_run"])
        # email privacy is read-only and should run
        ids = [t["id"] for t in rep["tasks"]]
        self.assertIn("suryodaya:rt_email_privacy", ids)


if __name__ == "__main__":
    unittest.main()
