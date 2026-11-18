"""Tests for the write checks against a fake platform. Run from the repo root:

    python -m unittest harness.test_intake_checks

The real copy is the only other place these checks can run, so the fake covers
the shapes the platform's replies might take.
"""
import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

from harness import intake_checks as checks

COPY_URL = "https://copy-1234.example.invalid"
ENV = {"AGENTSWITCH_TOKEN": "fake-token", "AGENTSWITCH_BASE_URL": COPY_URL, "AGENTSWITCH_INSTANCE": "suryodaya",
       "AGENTSWITCH_RUN_ID": "run-1"}
LABELS = {"Bill.list": "READ", "Bill.get": "READ", "AcctDocument.get": "READ", "AcctDocument.list": "READ",
          "Bill.submit": "POSTING"}


def bill(name="sample_01.pdf", **changes):
    doc = {"source_file": name, "doc_type": "vendor_bill", "flags": [], "proposed_action": "draft_bill",
           "counterparty_name": "Teal Paper Mills", "invoice_number": "TP/001", "invoice_date": "2026-09-25",
           "due_date": "2026-10-25", "currency": "INR", "subtotal": 500.0, "tax_total": 90.0, "total_stated": 590.0}
    doc.update(changes)
    return doc


class FakePlatform:
    def __init__(self, fields_shape="dict", accept_error=None, repeat_makes_bill=False, extract_error=None):
        self.fields_shape, self.accept_error = fields_shape, accept_error
        self.repeat_makes_bill, self.extract_error = repeat_makes_bill, extract_error
        self.bills, self.events, self.called, self.docs = {}, {}, [], {}

    def fields(self):
        values = {"bill_number": "TP/001", "date": "2026-09-25", "due_date": "2026-10-25", "currency_code": "INR",
                  "net_total": 500, "tax_total": 90, "grand_total": 595, "vendor_name": "Teal Paper Mills"}
        if self.fields_shape == "list":
            return [{"field": key, "value": value, "confidence": 0.9} for key, value in values.items()]
        if self.fields_shape == "string":
            return json.dumps({key: {"value": value} for key, value in values.items()})
        return {key: {"value": value, "confidence": 0.9} for key, value in values.items()}

    def handle(self, name, args):
        if name == "tools.describe":
            return {"results": [{"name": n, "risk_class": LABELS.get(n, "WRITE")} for n in args["names"]]}
        self.called.append(name)
        if name == "Bill.list":
            return {"total": len(self.bills), "data": []}
        if name == "AcctDocument.list":
            rows = [{"id": f"doc-{i}", "file_name": f"sample_{i:02d}.pdf",
                     "file_url": f"/uploads/accounting/intake-samples/sample_{i:02d}.pdf"} for i in (1, 2)]
            return {"total": len(rows), "data": rows}
        if name == checks.EXTRACT:
            if self.extract_error:
                return ("error", self.extract_error)
            self.docs[args["document_id"]] = {"intake_state": "review_required", "intake_fields": self.fields(),
                                              "intake_fingerprint": "fp-" + args["document_id"]}
            return {"status": "ok", "result": {"document_id": args["document_id"]}}
        if name == "AcctDocument.get":
            return {"id": args["id"], **self.docs.get(args["id"], {})}
        if name == "Party.create":
            return {"id": "party-1"}
        if name == checks.ACCEPT:
            if self.accept_error:
                return ("error", self.accept_error)
            event = args["client_event_id"]
            if event not in self.events or self.repeat_makes_bill:
                bill_id = f"bill-{len(self.bills) + 1}"
                self.bills[bill_id] = {"id": bill_id, "status": "draft"}
                self.events[event] = bill_id
                self.docs[args["document_id"]]["intake_bill_id"] = bill_id
            return {"status": "ok", "result": {"bill_id": self.events[event]}}
        if name == "Bill.get":
            return self.bills[args["id"]]
        raise AssertionError(f"unexpected tool {name}")

    def __call__(self, body):
        params = json.loads(body)["params"]
        reply = self.handle(params["name"], params["arguments"])
        if isinstance(reply, tuple):
            return 200, json.dumps({"jsonrpc": "2.0", "id": 1,
                                    "error": {"code": -32000, "message": "refused", "data": {"code": reply[1]}}})
        text = json.dumps(reply)
        return 200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": text}]}})


class WriteCheckTests(unittest.TestCase):
    def run_checks(self, platform, env=ENV, ours=None, names=None):
        checks.STATE.clear()
        ours = [bill(), bill("sample_13.pdf", doc_type="sales_invoice", proposed_action="reject_not_a_bill")]             if ours is None else ours
        names = names or [doc["source_file"] for doc in ours]
        checks.STATE.update(document_ids={name: f"doc-{i}" for i, name in enumerate(names)},
                            ours={doc["source_file"]: doc for doc in ours}, vendor_ids={})
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(checks, "_http_transport", lambda settings: platform):
            return [check.run() for check in (checks.extract_on_copy, checks.readers_compared, checks.accept_one_draft)]

    def test_happy_path(self):
        platform = FakePlatform()
        (extract, compare, accept) = self.run_checks(platform)
        self.assertTrue(extract[0], extract[1])
        self.assertTrue(compare[0], compare[1])
        self.assertIn("bill_number=2/2", compare[1])
        self.assertIn("grand_total=0/2", compare[1])
        self.assertTrue(accept[0], accept[1])
        self.assertIn("source=ours; made_party=True", accept[1])
        self.assertIn("bills=0->1->1", accept[1])
        self.assertNotIn("Bill.submit", platform.called)
        self.assertEqual(platform.called.count(checks.ACCEPT), 2)

    def test_platform_field_shapes(self):
        for shape in ("dict", "list", "string"):
            with self.subTest(shape=shape):
                _, compare, _ = self.run_checks(FakePlatform(fields_shape=shape))
                self.assertIn("bill_number=2/2", compare[1])

    def test_no_writes_when_not_on_a_copy(self):
        for env in ({**ENV, "AGENTSWITCH_RUN_ID": ""},
                    {**ENV, "AGENTSWITCH_BASE_URL": "https://agentswitch.theschoolofai.in"}):
            platform = FakePlatform()
            extract, compare, accept = self.run_checks(platform, env=env)
            self.assertFalse(extract[0])
            self.assertIn("not tried", extract[1])
            self.assertIn("not tried", compare[1])
            self.assertIn("not tried", accept[1])
            self.assertNotIn(checks.EXTRACT, platform.called)
            self.assertNotIn(checks.ACCEPT, platform.called)

    def test_platform_refusing_accept_fails_with_its_code(self):
        _, _, accept = self.run_checks(FakePlatform(accept_error="vendor_required"))
        self.assertFalse(accept[0])
        self.assertIn("vendor_required", accept[1])

    def test_a_second_bill_on_retry_fails(self):
        _, _, accept = self.run_checks(FakePlatform(repeat_makes_bill=True))
        self.assertFalse(accept[0])
        self.assertIn("bills=0->1->2", accept[1])

    def test_extract_errors_fail_and_accept_is_not_tried(self):
        platform = FakePlatform(extract_error="file_unavailable")
        extract, compare, accept = self.run_checks(platform)
        self.assertFalse(extract[0])
        self.assertIn("errors=2", extract[1])
        self.assertIn("not tried", accept[1])
        self.assertNotIn(checks.ACCEPT, platform.called)

    def test_a_flagged_bill_is_never_accepted(self):
        platform = FakePlatform()
        _, _, accept = self.run_checks(platform, ours=[bill(flags=["total_mismatch"])])
        self.assertIn("not tried", accept[1])
        self.assertNotIn(checks.ACCEPT, platform.called)


    def test_without_our_results_extract_runs_and_accept_uses_the_platform_values(self):
        platform = FakePlatform()
        extract, compare, accept = self.run_checks(platform, ours=[], names=["sample_01.pdf", "sample_02.pdf"])
        self.assertTrue(extract[0], extract[1])
        self.assertIn("extracted=2/2", extract[1])
        self.assertFalse(compare[0])
        self.assertIn("ours=0; platform_fields_found=14", compare[1])
        self.assertTrue(accept[0], accept[1])
        self.assertIn("source=platform", accept[1])
        self.assertNotIn("Bill.submit", platform.called)


def http_error(code):
    return urllib.error.HTTPError("https://copy.invalid/x", code, "refused", {}, io.BytesIO(b""))


class DownloadTests(unittest.TestCase):
    def run_samples(self, fetch):
        checks.STATE.clear()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        with mock.patch.dict(os.environ, ENV, clear=True),                 mock.patch.object(checks.tempfile, "mkdtemp", lambda prefix: folder.name),                 mock.patch.object(checks, "_http_transport", lambda settings: FakePlatform()),                 mock.patch.object(checks, "_fetch", fetch):
            return checks.samples_on_copy.run()

    def test_failed_downloads_name_the_status_and_keep_every_document_for_extract(self):
        def fetch(url, token):
            raise http_error(404)
        passed, evidence = self.run_samples(fetch)
        self.assertFalse(passed)
        self.assertIn("listed=2; downloaded=0; failed=2", evidence)
        self.assertIn("why=http_404:2", evidence)
        self.assertEqual(checks.STATE["document_ids"], {"sample_01.pdf": "doc-1", "sample_02.pdf": "doc-2"})

    def test_a_refused_token_is_tried_once_without_it(self):
        tokens = []

        def fetch(url, token):
            tokens.append(token)
            if token:
                raise http_error(401)
            return b"%PDF-1.4"
        _, evidence = self.run_samples(fetch)
        self.assertIn("downloaded=2; failed=0", evidence)
        self.assertEqual(tokens, ["fake-token", None, "fake-token", None])

    def test_both_refusals_are_named(self):
        def fetch(url, token):
            raise http_error(401 if token else 403)
        _, evidence = self.run_samples(fetch)
        self.assertIn("why=http_401>no_token_http_403:2", evidence)


class DigestTests(unittest.TestCase):
    def test_digest_ignores_field_order_and_flag_order(self):
        first = checks.result_digest(bill(flags=["a", "b"]))
        second = checks.result_digest(dict(reversed(list(bill(flags=["b", "a"]).items()))))
        self.assertEqual(first, second)

    def test_digest_changes_with_a_value(self):
        self.assertNotEqual(checks.result_digest(bill()), checks.result_digest(bill(total_stated=591.0)))

    def test_expected_samples_hold_no_document_values(self):
        for name, row in checks.EXPECTED.items():
            self.assertEqual(set(row), {"sha256", "digest"})
            self.assertRegex(name, r"^sample_\d{2}\.pdf$")


if __name__ == "__main__":
    unittest.main()
