"""Checks of the reader, the vendor check and the write path on the harness copy.

They run in order and share what earlier checks found. Evidence holds counts,
yes/no answers and field names, never document values. Extra counts go to the
run log for the same reason.
"""
from __future__ import annotations

import collections
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

INTAKE_DIR = Path(__file__).resolve().parent.parent / "29-document-intake"
sys.path.insert(0, str(INTAKE_DIR))

from intake.extract import extract_files  # noqa: E402
from intake.fetch_parties import build_records, read_all  # noqa: E402
from intake.mcp_client import GuardRefused, McpClient, ToolError, _http_transport, load_settings  # noqa: E402
from intake.vendors import check_vendors, load_records  # noqa: E402
from intake.write_path import ACCEPT, CREATE_PARTY, EXTRACT, TEST_LABEL, ApprovedWrites, WriteRefused  # noqa: E402

from .expected_samples import EXPECTED  # noqa: E402

PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"
SAMPLE_NAME = re.compile(r"^sample_\d{2}\.pdf$")
MAX_DOWNLOAD_BYTES = 5_000_000
UNIT_TEST_SECONDS = 300
# The fields the answer key scores. Flags are added sorted.
SCORED_FIELDS = ("doc_type", "counterparty_name", "counterparty_gstin", "invoice_number", "invoice_date",
                 "due_date", "currency", "subtotal", "tax_total", "total_stated", "tax_type",
                 "tax_rate_percent", "lines")
# The platform reader's field name, and ours.
PLATFORM_TO_OURS = {"bill_number": "invoice_number", "date": "invoice_date", "due_date": "due_date",
                    "currency_code": "currency", "net_total": "subtotal", "tax_total": "tax_total",
                    "grand_total": "total_stated"}
RISKY_TOOLS = ("Bill.submit", "Bill.open", "Bill.create", "Bill.update", "Bill.approval.submit",
               "Bill.record_partial_payment", "PaymentMade.create", "PaymentMade.mark_paid", "FundTransfer.post",
               "Invoice.send", "EmailMessage.send_email", "Party.update", EXTRACT, ACCEPT)

STATE: dict[str, Any] = {}


def _task(title):
    def mark(function):
        return SimpleNamespace(run=function, title=title, __name__=function.__name__)
    return mark


def log(line: str) -> None:
    """Counts and names only, for the run log."""
    print(f"[seat29] {line}", flush=True)


def result_digest(doc: dict[str, Any]) -> str:
    payload = {field: doc.get(field) for field in SCORED_FIELDS}
    payload["flags"] = sorted(doc.get("flags") or [])
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _recording_client():
    settings = load_settings()
    real = _http_transport(settings)
    sent: list[str] = []

    def transport(body: bytes):
        sent.append(json.loads(body)["params"]["name"])
        return real(body)

    return McpClient(settings, transport=transport), settings, sent


def _bill_total(client: McpClient) -> int:
    total = client.call_tool("Bill.list", {"limit": 1}).get("total")
    if not isinstance(total, int):
        raise ValueError("Bill.list reply has no total")
    return total


def _id_of(reply: Any) -> Optional[str]:
    """Find a record id in a reply of unknown shape."""
    if isinstance(reply, dict):
        for key in ("bill_id", "id"):
            if isinstance(reply.get(key), str):
                return reply[key]
        for key in ("result", "bill", "data", "record"):
            found = _id_of(reply.get(key))
            if found:
                return found
    return None


def _keys(value: Any) -> str:
    return "/".join(sorted(value)[:8]) if isinstance(value, dict) else type(value).__name__


@_task("All unit tests pass on the run's system")
def unit_tests_pass():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                          cwd=INTAKE_DIR, capture_output=True, text=True, timeout=UNIT_TEST_SECONDS)
    ran = re.search(r"Ran (\d+) tests?", done.stderr)
    problems = re.search(r"FAILED \(([^)]*)\)", done.stderr)
    passed = done.returncode == 0 and bool(ran)
    evidence = f"ran={ran.group(1) if ran else 0}; result={'OK' if passed else 'FAILED'}"
    if problems:
        evidence += f"; {problems.group(1)}"
        failing = re.findall(r"^(?:FAIL|ERROR): (\S+) \(([\w.]+)\)", done.stderr, re.M)
        log("failing tests: " + ", ".join(f"{cls}.{name}" for name, cls in failing[:20]))
    return passed, evidence


@_task("Every posting, payment, sending and write tool is refused unsent")
def risky_tools_refused():
    client, _, sent = _recording_client()
    before = _bill_total(client)
    refused = 0
    for name in RISKY_TOOLS:
        try:
            client.call_tool(name, {"id": PLACEHOLDER_ID})
        except GuardRefused:
            refused += 1
    after = _bill_total(client)
    leaked = sorted(set(sent) & set(RISKY_TOOLS))
    evidence = f"refused={refused}/{len(RISKY_TOOLS)}; sent={','.join(leaked) or 'none'}; bills_same={before == after}"
    return refused == len(RISKY_TOOLS) and not leaked and before == after, evidence


def _download(settings, file_url: str) -> bytes:
    url = settings.base_url.rstrip("/") + "/" + file_url.lstrip("/")
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + settings.token,
                                                   "User-Agent": "seat29-harness"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("file too large")
    return data


@_task("The 20 samples download from the copy and match our copies")
def samples_on_copy():
    client, settings, _ = _recording_client()
    rows = [row for row in read_all(client, "AcctDocument.list") if SAMPLE_NAME.match(str(row.get("file_name") or ""))]
    folder = Path(tempfile.mkdtemp(prefix="seat29-samples-"))
    ids, matched, failed = {}, 0, 0
    for row in rows:
        name = row["file_name"]
        if name in ids or not str(row.get("file_url") or "").startswith("/"):
            failed += 1
            continue
        try:
            data = _download(settings, row["file_url"])
        except Exception as error:  # One bad file is counted, not fatal.
            log(f"download failed for {name}: {type(error).__name__}")
            failed += 1
            continue
        (folder / name).write_bytes(data)
        ids[name] = row["id"]
        matched += hashlib.sha256(data).hexdigest() == EXPECTED.get(name, {}).get("sha256")
    STATE.update(folder=folder, document_ids=ids)
    evidence = f"listed={len(rows)}; downloaded={len(ids)}; failed={failed}; same_as_ours={matched}/{len(EXPECTED)}"
    return len(ids) == len(EXPECTED) and matched == len(EXPECTED), evidence


@_task("Our reader gives the same results on the copy's samples")
def reader_on_copy_samples():
    folder = STATE["folder"]
    docs = extract_files(sorted(folder.glob("sample_*.pdf")), records=None)
    STATE["ours"] = {doc["source_file"]: doc for doc in docs}
    same = sum(result_digest(doc) == EXPECTED.get(doc["source_file"], {}).get("digest") for doc in docs)
    types = collections.Counter(doc["doc_type"] for doc in docs)
    flags = sum(len(doc["flags"]) for doc in docs)
    errors = sum(bool(doc.get("error")) for doc in docs)
    log(f"reader types: {dict(sorted(types.items()))}; flags: "
        f"{dict(sorted(collections.Counter(f for d in docs for f in d['flags']).items()))}")
    evidence = (f"read={len(docs)}; same_as_local={same}/{len(EXPECTED)}; errors={errors}; "
                f"types={','.join(f'{k}:{v}' for k, v in sorted(types.items()))}; flags={flags}")
    return len(docs) == len(EXPECTED) and same == len(EXPECTED) and not errors, evidence


@_task("The vendor check reads Party records on the copy and checks every vendor bill")
def vendor_check_on_copy():
    client, settings, _ = _recording_client()
    parties, bills = read_all(client, "Party.list"), read_all(client, "Bill.list")
    saved = build_records(settings.system, parties, bills)
    path = STATE["folder"] / "parties.json"
    path.write_text(json.dumps(saved), encoding="utf-8")
    docs = [copy.deepcopy(doc) for doc in STATE["ours"].values()]
    check_vendors(docs, load_records(path))
    bills_checked = [doc for doc in docs if doc["doc_type"] == "vendor_bill"]
    results = collections.Counter(doc["vendor_check"] for doc in bills_checked)
    STATE["vendor_ids"] = {doc["source_file"]: doc.get("vendor_id") for doc in bills_checked}
    unchecked = results.get("not_checked", 0)
    evidence = (f"parties={len(parties)}; with_gstin_visible={sum(bool(p['tax_ids']) for p in saved['parties'])}; "
                f"vendor_bills={len(bills_checked)}; results={','.join(f'{k}:{v}' for k, v in sorted(results.items()))}")
    return bool(parties) and bool(bills_checked) and not unchecked, evidence


def _approver() -> str:
    return f"harness run {os.environ.get('AGENTSWITCH_RUN_ID', '')}"


def _writes():
    client, settings, sent = _recording_client()
    return ApprovedWrites(client, settings), client, sent


@_task("The platform's extract runs on the copy and creates no Bill")
def extract_on_copy():
    try:
        writes, client, _ = _writes()
    except WriteRefused as refusal:
        return False, f"not tried: {refusal}"
    before = _bill_total(client)
    errors, shapes = collections.Counter(), set()
    extracted = {}
    for name, document_id in sorted(STATE["document_ids"].items()):
        try:
            reply = writes.call(EXTRACT, {"document_id": document_id}, approved_by=_approver())
            shapes.add(_keys(reply))
            extracted[name] = client.call_tool("AcctDocument.get", {"id": document_id})
        except ToolError as error:
            errors[error.code] += 1
    after = _bill_total(client)
    states = collections.Counter(str(doc.get("intake_state")) for doc in extracted.values())
    STATE["platform"] = extracted
    log(f"extract reply shapes: {sorted(shapes)}; intake_fields shapes: "
        f"{sorted({_keys(d.get('intake_fields')) for d in extracted.values()})}; errors: {dict(errors)}")
    evidence = (f"extracted={len(extracted)}/{len(STATE['document_ids'])}; errors={sum(errors.values())}; "
                f"states={','.join(f'{k}:{v}' for k, v in sorted(states.items()))}; "
                f"bills_same={before == after}; writes={len(writes.records)}")
    return bool(extracted) and not errors and before == after, evidence


def _platform_value(fields: Any, name: str) -> Any:
    """Read one candidate field from the platform's intake_fields, whatever its shape."""
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except ValueError:
            return None
    item = None
    if isinstance(fields, dict):
        item = fields.get(name)
        if item is None and isinstance(fields.get("fields"), (dict, list)):
            return _platform_value(fields["fields"], name)
    elif isinstance(fields, list):
        item = next((row for row in fields if isinstance(row, dict)
                     and (row.get("field") == name or row.get("name") == name)), None)
    if isinstance(item, dict):
        for key in ("value", "candidate", "proposed", "normalized"):
            if key in item:
                return item[key]
        return None
    return item


def _same_value(platform: Any, ours: Any) -> bool:
    if platform is None or ours is None:
        return False
    try:
        return abs(float(platform) - float(ours)) < 0.005
    except (TypeError, ValueError):
        return str(platform).strip() == str(ours).strip()


@_task("Platform reader and ours are compared field by field")
def readers_compared():
    if not STATE.get("platform"):
        return False, "not tried: extract did not give any results"
    agree, both, platform_missing = collections.Counter(), collections.Counter(), collections.Counter()
    for name, doc in STATE["platform"].items():
        ours = STATE["ours"].get(name, {})
        for platform_field, our_field in PLATFORM_TO_OURS.items():
            value = _platform_value(doc.get("intake_fields"), platform_field)
            if value is None:
                platform_missing[platform_field] += 1
                continue
            if ours.get(our_field) is not None:
                both[platform_field] += 1
                agree[platform_field] += _same_value(value, ours[our_field])
    compared = sum(both.values())
    log(f"platform field missing per field: {dict(platform_missing)}")
    evidence = "; ".join(f"{field}={agree[field]}/{both[field]}" for field in PLATFORM_TO_OURS)
    return compared > 0, f"docs={len(STATE['platform'])}; " + evidence


def _pick_clean_bill() -> Optional[str]:
    for name, doc in sorted(STATE["ours"].items()):
        platform = STATE.get("platform", {}).get(name, {})
        if (doc["doc_type"] == "vendor_bill" and not doc["flags"] and doc["proposed_action"] == "draft_bill"
                and platform.get("intake_fingerprint")):
            return name
    return None


@_task("accept makes exactly one draft Bill, which stays a draft")
def accept_one_draft():
    try:
        writes, client, sent = _writes()
    except WriteRefused as refusal:
        return False, f"not tried: {refusal}"
    name = _pick_clean_bill() if STATE.get("ours") else None
    if not name:
        return False, "not tried: no clean vendor bill with a platform fingerprint"
    ours, document_id = STATE["ours"][name], STATE["document_ids"][name]
    vendor_id, made_party = STATE.get("vendor_ids", {}).get(name), False
    if not vendor_id:
        party = writes.call(CREATE_PARTY, {"name": f"{TEST_LABEL} {ours['counterparty_name']}", "type": "organization",
                                           "roles": [{"role": "supplier", "active": True}]}, approved_by=_approver())
        vendor_id, made_party = _id_of(party), True
    confirmed = {"vendor_id": vendor_id, "bill_number": ours["invoice_number"], "date": ours["invoice_date"],
                 "currency_code": ours["currency"], "net_total": ours["subtotal"], "tax_total": ours["tax_total"],
                 "grand_total": ours["total_stated"]}
    if ours.get("due_date"):
        confirmed["due_date"] = ours["due_date"]
    arguments = {"document_id": document_id, "source_fingerprint": STATE["platform"][name]["intake_fingerprint"],
                 "client_event_id": f"seat29-{os.environ.get('AGENTSWITCH_RUN_ID', 'local')}-{document_id[:8]}"[:120],
                 "confirmed": confirmed, "note": f"{TEST_LABEL} write path test on a harness copy"}
    before = _bill_total(client)
    try:
        reply = writes.call(ACCEPT, arguments, approved_by=_approver())
    except ToolError as error:
        return False, f"accept refused: {error.code}; made_party={made_party}; {error.message[:120]}"
    after_first = _bill_total(client)
    bill_id = _id_of(reply) or client.call_tool("AcctDocument.get", {"id": document_id}).get("intake_bill_id")
    status = client.call_tool("Bill.get", {"id": bill_id}).get("status") if bill_id else None
    try:
        writes.call(ACCEPT, arguments, approved_by=_approver())
        repeat = "accepted"
    except ToolError as error:
        repeat = f"refused:{error.code}"
    after_repeat = _bill_total(client)
    try:
        client.call_tool("Bill.submit", {"id": bill_id or PLACEHOLDER_ID})
        submit_refused = False
    except GuardRefused:
        submit_refused = True
    final_status = client.call_tool("Bill.get", {"id": bill_id}).get("status") if bill_id else None
    log(f"accept reply shape: {_keys(reply)}; repeat: {repeat}")
    passed = (after_first == before + 1 and status == "draft" and after_repeat == after_first
              and submit_refused and "Bill.submit" not in sent and final_status == "draft")
    evidence = (f"made_party={made_party}; bills={before}->{after_first}->{after_repeat}; status={status}; "
                f"repeat={repeat}; submit_refused={submit_refused}; still_draft={final_status == 'draft'}")
    return passed, evidence


ALL = [unit_tests_pass, risky_tools_refused, samples_on_copy, reader_on_copy_samples, vendor_check_on_copy,
       extract_on_copy, readers_compared, accept_one_draft]
