"""The five setup checks. Each returns (passed, evidence). An exception is reported as an infrastructure failure."""
from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import platform
import re
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "29-document-intake"))

from intake.mcp_client import GuardRefused, McpClient, _http_transport, load_settings  # noqa: E402

PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"
MODEL_TIMEOUT_SECONDS = 60
MODEL_REPLY_TOKENS = 200
IMAGE_COLOURS = {"red": (255, 0, 0), "blue": (0, 0, 255)}
REQUIRED_SETTINGS = ("AGENTSWITCH_BASE_URL", "AGENTSWITCH_TOKEN", "AGENTSWITCH_INSTANCE", "AGENTSWITCH_RUN_ID",
                     "OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL")


def _task(title):
    def mark(function):
        function.title = title
        return SimpleNamespace(run=function, title=title, __name__=function.__name__)
    return mark


def _bill_total(client: McpClient) -> int:
    total = client.call_tool("Bill.list", {"limit": 1}).get("total")
    if not isinstance(total, int):
        raise ValueError("Bill.list reply has no total")
    return total


@_task("Python, operating system and run settings")
def system_and_settings():
    child = subprocess.run([sys.executable, "-c", "print('ok')"], capture_output=True, text=True, timeout=30)
    missing = [name for name in REQUIRED_SETTINGS if not os.environ.get(name)]
    evidence = (f"python={platform.python_version()}; system={platform.system()}; machine={platform.machine()}; "
                f"cpus={os.cpu_count()}; child_process={'ok' if child.stdout.strip() == 'ok' else 'failed'}; "
                f"resource_module={'yes' if importlib.util.find_spec('resource') else 'no'}; "
                f"missing_settings={','.join(missing) or 'none'}")
    return sys.version_info >= (3, 9) and child.stdout.strip() == "ok" and not missing, evidence


@_task("Packages from requirements.txt install and work")
def packages_installed():
    import pypdf

    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = io.BytesIO()
    writer.write(buffer)
    pages = len(pypdf.PdfReader(io.BytesIO(buffer.getvalue())).pages)
    return pages == 1, f"pypdf={pypdf.__version__}; round_trip_pages={pages}"


@_task("Seat token logs in and a read works on the copy")
def login_and_read():
    total = _bill_total(McpClient(load_settings()))
    return True, f"bills={total}"


@_task("The client refuses Bill.submit, sends nothing and changes nothing")
def guard_refuses_posting():
    settings = load_settings()
    real_transport = _http_transport(settings)
    sent = []

    def recording_transport(body: bytes):
        sent.append(json.loads(body)["params"]["name"])
        return real_transport(body)

    client = McpClient(settings, transport=recording_transport)
    before = _bill_total(client)
    try:
        client.call_tool("Bill.submit", {"id": PLACEHOLDER_ID})
        refused = False
    except GuardRefused:
        refused = True
    after = _bill_total(client)
    was_sent = "Bill.submit" in sent
    evidence = f"refused={refused}; sent={was_sent}; bills_before={before}; bills_after={after}"
    return refused and not was_sent and before == after, evidence


def _solid_png(colour: "tuple[int, int, int]") -> str:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    size = 16
    rows = b"".join(b"\x00" + bytes(colour) * size for _ in range(size))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    return "data:image/png;base64," + base64.b64encode(png).decode()


def _ask_model(content) -> "tuple[int, str, str]":
    """Return (HTTP status, reply text, finish reason)."""
    url = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"
    body = json.dumps({"model": os.environ["OPENAI_MODEL"], "max_tokens": MODEL_REPLY_TOKENS,
                       "messages": [{"role": "user", "content": content}]}).encode()
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS) as response:
            choice = json.loads(response.read().decode("utf-8", "replace"))["choices"][0]
        return response.status, str(choice["message"].get("content") or ""), str(choice.get("finish_reason"))
    except urllib.error.HTTPError as error:
        return error.code, "", ""


def _short_answer(reply: str) -> str:
    """The images are ours, so a short answer is safe to record. Letters and spaces only."""
    return re.sub(r"[^A-Za-z ]", "", reply)[:24] or "empty"


@_task("The model reads a colour from an image correctly")
def model_reads_images():
    missing = [name for name in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL") if not os.environ.get(name)]
    if missing:
        return False, f"infrastructure: model settings missing: {','.join(missing)}"

    control, _, _ = _ask_model("Reply with the word ok.")
    if control != 200:
        return False, f"infrastructure: the model refused plain text too (HTTP {control})"

    details, correct = [], True
    for name, colour in IMAGE_COLOURS.items():
        status, reply, finish = _ask_model([
            {"type": "text", "text": "What colour fills this image? Answer with one word."},
            {"type": "image_url", "image_url": {"url": _solid_png(colour)}},
        ])
        if status in (400, 415, 422):
            return False, f"images=refused; http={status}"
        if status != 200:
            return False, f"infrastructure: image request gave HTTP {status}"
        words = re.findall(r"[a-z]+", reply.lower())
        correct = correct and name in words and not any(other in words for other in IMAGE_COLOURS if other != name)
        details.append(f"{name}_image_answer={_short_answer(reply)}; {name}_finish={finish}")
    return correct, f"images=accepted; read_correctly={correct}; " + "; ".join(details)


ALL = [system_and_settings, packages_installed, login_and_read, guard_refuses_posting, model_reads_images]
