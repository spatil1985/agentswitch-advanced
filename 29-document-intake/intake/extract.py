"""Read PDFs and write proposed fields to a JSON file, without using the platform.

Run from 29-document-intake:
    python -m intake.extract local/samples/sample_01.pdf --out local/predictions.json

The output holds document data, so keep it in the git-ignored local/ folder.
Standard output is counts only.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

from .reader import mark_duplicates, parse_document


def read_pdf_text(path: Path) -> str:
    """Return the PDF's text layer, or an empty string if it has none or cannot be read."""
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    except (PyPdfError, OSError, ValueError):
        return ""


def extract_files(paths: list[Path]) -> list[dict]:
    docs = []
    for path in sorted(paths):
        doc = parse_document(read_pdf_text(path))
        doc["source_file"] = path.name
        doc["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        docs.append(doc)
    mark_duplicates(docs)
    return docs


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    docs = extract_files(args.pdfs)
    args.out.write_text(json.dumps(docs, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"documents: {len(docs)}")
    print(f"types: {dict(sorted(collections.Counter(d['doc_type'] for d in docs).items()))}")
    print(f"sent to a person first: {sum(d['needs_review'] for d in docs)}")
    flags = collections.Counter(flag for d in docs for flag in d["flags"])
    print(f"flags: {dict(sorted(flags.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
