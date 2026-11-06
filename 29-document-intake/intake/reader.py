"""Turn the text of a document into proposed fields, flags and a confidence.

Rules only: the same text always gives the same result, it uses no tokens, and
the text is only ever parsed, so nothing written in a document can act as an
instruction. Everything here is a proposal for a person to review.

Confidence is a rule score from 0 to 1, not a probability.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

# The two made-up companies in the course sample set. A live run will take the
# company from the platform instead.
SAMPLE_OWN_GSTINS = frozenset({"29AAACD0000A1Z5", "29AAACS0000B1Z7"})

# The same threshold the platform's bill intake uses.
REVIEW_THRESHOLD = 0.85
TOLERANCE = Decimal("0.01")

GSTIN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b")
PARTY_LABEL = re.compile(
    r"^(?:bill(?:ed)?\s+to|buyer|customer|credit(?:ed)?\s+to|issued\s+to)\s*:?\s*$", re.I
)
TABLE_HEADER = re.compile(r"^amount$|\bqty\b.*\bamount\b", re.I)
AMOUNT_TEXT = r"\(?-?\d(?:[\d,.]*\d)?\)?"
AMOUNT_SEARCH = re.compile(AMOUNT_TEXT)
AMOUNT_ONLY = re.compile(rf"^{AMOUNT_TEXT}$")
LINE_ON_ONE_ROW = re.compile(rf"^(.+?)\s+({AMOUNT_TEXT})\s+({AMOUNT_TEXT})\s+({AMOUNT_TEXT})$")

NUMBER_LABELS = (
    r"credit\s*note\s*(?:#|no\.?|number)",
    r"cn\s*(?:#|no\.?)",
    r"note\s*(?:#|no\.?)",
    r"bill\s*(?:#|no\.?|number)",
    r"inv(?:oice)?\.?\s*(?:#|no\.?|number)",
    r"document\s*(?:#|no\.?)",
    r"ref(?:erence)?(?:\s*no\.?)?",
)
DUE_LABEL = re.compile(r"^(?:pay\s*by|payment\s*due|due\s*on|due\s*date|due)\s*:\s*(.+)$", re.I)
DATE_LABEL = re.compile(
    r"^(?:bill\s*date|invoice\s*date|credit\s*note\s*date|note\s*date|issued(?:\s*on)?|dt\.?|date)"
    r"\s*:\s*(.+)$",
    re.I,
)
ORIGINAL_LABEL = re.compile(
    r"^(?:against(?:\s*(?:invoice|inv\.?|bill))?|original\s*(?:invoice|bill)(?:\s*no\.?)?|"
    r"ref(?:erence)?\.?\s*(?:invoice|inv\.?|bill)(?:\s*no\.?)?)\s*:?\s*(\S.*)$",
    re.I,
)
SUBTOTAL_LABEL = re.compile(r"^(?:sub\s*-?\s*total|taxable\s+(?:value|amount)|net\s+total)\b", re.I)
TOTAL_LABEL = re.compile(r"^(?:grand\s+)?total(?:\s+(?:amount|payable|due|credit))?\b", re.I)
TAX_LABEL = re.compile(r"^(CGST|SGST|UTGST|IGST|VAT|GST|Tax|Cess)\b(?:\s*@\s*([\d.]+)\s*%)?", re.I)
NO_TAX = re.compile(r"\b(?:exempt|no\s+tax|not\s+applicable|nil[\s-]rated|zero[\s-]rated)\b", re.I)
CURRENCIES = (
    ("INR", re.compile(r"₹|\bRs\.?|\bINR\b", re.I)),
    ("USD", re.compile(r"US\$|\$|\bUSD\b", re.I)),
    ("EUR", re.compile(r"€|\bEUR\b", re.I)),
    ("GBP", re.compile(r"£|\bGBP\b", re.I)),
)
DATE_FORMATS = ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y")
NUMERIC_DATE = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$")

# Flags that always send a document to a person first, whatever its score.
REVIEW_FLAGS = frozenset({
    "total_mismatch",
    "lines_do_not_match_subtotal",
    "line_amount_mismatch",
    "tax_rate_mismatch",
    "tax_type_state_mismatch",
    "due_before_bill_date",
    "unknown_counterparty",
    "unknown_document_type",
    "no_text_layer",
    "unparsed_date",
    "ambiguous_date_order",
    "mixed_currencies",
    "possible_duplicate",
})


def parse_amount(text: str, decimal_comma: bool = False) -> Optional[Decimal]:
    """Parse 24,000.00 or 1,13,067.60, or 1.094,37 when decimal_comma is set."""
    # Find the number first: the dot in "Rs." must not become part of it.
    match = AMOUNT_SEARCH.search(text)
    if not match:
        return None
    cleaned = match.group(0)
    negative = cleaned.startswith(("-", "(")) or cleaned.endswith(")")
    cleaned = cleaned.strip("()-")
    if decimal_comma:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value if negative else value


def _uses_decimal_comma(lines: list[str]) -> bool:
    return any(re.search(r"\d,\d{2}\)?$", line) for line in lines)


def _day_first(raw_dates: list[str]) -> Optional[bool]:
    """Use any date in the document that can only be read one way."""
    for raw in raw_dates:
        match = NUMERIC_DATE.match(raw.strip())
        if match:
            if int(match.group(1)) > 12:
                return True
            if int(match.group(2)) > 12:
                return False
    return None


def parse_date(text: str, day_first: bool = True) -> Optional[date]:
    cleaned = text.strip()
    match = NUMERIC_DATE.match(cleaned)
    if match:
        first, second, year = (int(part) for part in match.groups())
        day, month = (first, second) if day_first else (second, first)
        try:
            return date(year, month, day)
        except ValueError:
            return None
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    return None


def _is_ambiguous_numeric_date(text: str) -> bool:
    match = NUMERIC_DATE.match(text.strip())
    return bool(match) and int(match.group(1)) <= 12 and int(match.group(2)) <= 12 \
        and match.group(1) != match.group(2)


def _first_labelled(lines: list[str], label: re.Pattern) -> Optional[str]:
    for line in lines:
        match = label.match(line)
        if match:
            return match.group(1).strip()
    return None


def _document_number(lines: list[str]) -> Optional[str]:
    for label in NUMBER_LABELS:
        pattern = re.compile(rf"^{label}\s*:?\s*(\S.*)$", re.I)
        for line in lines:
            if ORIGINAL_LABEL.match(line):
                continue
            match = pattern.match(line)
            if match:
                return match.group(1).strip()
    return None


def _title(lines: list[str]) -> str:
    for line in lines[:12]:
        upper = line.upper().strip()
        if upper in {"CREDIT NOTE", "DEBIT NOTE", "TAX INVOICE", "INVOICE", "BILL",
                     "PURCHASE ORDER", "RECEIPT"}:
            return upper
    return ""


def _classify(title: str, seller_gstin: Optional[str], buyer_gstin: Optional[str],
              own_gstins: frozenset[str]) -> "tuple[str, list[str]]":
    if title == "CREDIT NOTE":
        return "credit_note", []
    if title == "PURCHASE ORDER":
        return "purchase_order", []
    if title == "RECEIPT":
        return "receipt", []
    if title not in {"TAX INVOICE", "INVOICE", "BILL"}:
        return "unknown", ["unknown_document_type"]
    # The title cannot decide this: bills and our own sales invoices can both
    # say TAX INVOICE. What matters is which side of the document we are on.
    if buyer_gstin in own_gstins:
        return "vendor_bill", []
    if seller_gstin in own_gstins:
        return "sales_invoice", []
    return "unknown", ["unknown_counterparty"]


def _party_details(lines: list[str]) -> dict[str, Optional[str]]:
    party_index = next((i for i, line in enumerate(lines) if PARTY_LABEL.match(line)), None)
    header = lines if party_index is None else lines[:party_index]
    block = [] if party_index is None else lines[party_index + 1:party_index + 5]
    seller_gstin = next((m.group(1) for m in map(GSTIN.search, header) if m), None)
    buyer_gstin = next((m.group(1) for m in map(GSTIN.search, block) if m), None)
    return {
        "seller_name": lines[0] if lines else None,
        "seller_gstin": seller_gstin,
        "buyer_name": block[0] if block else None,
        "buyer_gstin": buyer_gstin,
    }


def _line_items(table: list[str], decimal_comma: bool) -> list[dict[str, Any]]:
    items, description, numbers = [], [], []
    for line in table:
        one_row = LINE_ON_ONE_ROW.match(line)
        if one_row and not description:
            values = [parse_amount(part, decimal_comma) for part in one_row.groups()[1:]]
            if None not in values:
                items.append({"description": one_row.group(1), "qty": values[0],
                              "rate": values[1], "amount": values[2]})
                continue
        if AMOUNT_ONLY.match(line) and description:
            numbers.append(parse_amount(line, decimal_comma))
            if len(numbers) == 3:
                if None not in numbers:
                    items.append({"description": " ".join(description), "qty": numbers[0],
                                  "rate": numbers[1], "amount": numbers[2]})
                description, numbers = [], []
        else:
            description.append(line)
    return items


def _labelled_amount(lines: list[str], index: int, label: re.Pattern, decimal_comma: bool
                     ) -> "tuple[Optional[Decimal], str]":
    """Return the amount for a label on the same line or the next one, and its text."""
    remainder = label.sub("", lines[index], count=1).strip()
    text = remainder if re.search(r"\d", remainder) else ""
    if not text and index + 1 < len(lines) and re.search(r"\d", lines[index + 1]):
        text = lines[index + 1]
    return (parse_amount(text, decimal_comma) if text else None), text


def _currency(money_texts: list[str]) -> "tuple[Optional[str], list[str]]":
    found = []
    for text in money_texts:
        for code, pattern in CURRENCIES:
            if pattern.search(text) and code not in found:
                found.append(code)
    flags = ["mixed_currencies"] if len(found) > 1 else []
    return (found[0] if found else None), flags


def _read_totals(lines: list[str], decimal_comma: bool) -> dict[str, Any]:
    totals: dict[str, Any] = {"net": None, "total": None, "tax": None, "taxes": [],
                              "no_tax": False, "exempt": False, "money_texts": []}
    tax_sum = Decimal(0)
    for index, line in enumerate(lines):
        if SUBTOTAL_LABEL.match(line):
            totals["net"], text = _labelled_amount(lines, index, SUBTOTAL_LABEL, decimal_comma)
        elif TOTAL_LABEL.match(line):
            totals["total"], text = _labelled_amount(lines, index, TOTAL_LABEL, decimal_comma)
        elif NO_TAX.search(line):
            totals["no_tax"] = True
            totals["exempt"] = totals["exempt"] or "exempt" in line.lower()
            continue
        elif TAX_LABEL.match(line):
            match = TAX_LABEL.match(line)
            amount, text = _labelled_amount(lines, index, TAX_LABEL, decimal_comma)
            if amount is not None:
                tax_sum += amount
                rate = Decimal(match.group(2)) if match.group(2) else None
                totals["taxes"].append({"type": match.group(1).upper(), "rate": rate, "amount": amount})
        else:
            continue
        if text:
            totals["money_texts"].append(text)
    if totals["taxes"]:
        totals["tax"] = tax_sum
    elif totals["no_tax"]:
        totals["tax"] = Decimal(0)
    return totals


def _check_amounts(items: list[dict[str, Any]], totals: dict[str, Any],
                   seller_gstin: Optional[str], buyer_gstin: Optional[str]) -> list[str]:
    flags = []
    net, tax, total = totals["net"], totals["tax"], totals["total"]
    if any(abs(row["qty"] * row["rate"] - row["amount"]) > TOLERANCE for row in items):
        flags.append("line_amount_mismatch")
    if items and net is not None and abs(sum(row["amount"] for row in items) - net) > TOLERANCE:
        flags.append("lines_do_not_match_subtotal")
    if None not in (net, tax, total) and abs(net + tax - total) > TOLERANCE:
        flags.append("total_mismatch")
    if net is not None and any(
        row["rate"] is not None and abs(net * row["rate"] / 100 - row["amount"]) > TOLERANCE
        for row in totals["taxes"]
    ):
        flags.append("tax_rate_mismatch")
    kinds = {row["type"] for row in totals["taxes"]}
    if seller_gstin and buyer_gstin and kinds:
        same_state = seller_gstin[:2] == buyer_gstin[:2]
        if ("IGST" in kinds and same_state) or (kinds & {"CGST", "SGST"} and not same_state):
            flags.append("tax_type_state_mismatch")
    if totals["exempt"]:
        flags.append("tax_exempt")
    if any(row["amount"] < 0 for row in items):
        flags.append("has_discount_line")
    return flags


def _confidence(doc: dict[str, Any], flags: list[str], ambiguous_date: bool) -> dict[str, float]:
    reconciled = not {"total_mismatch", "lines_do_not_match_subtotal"} & set(flags)
    return {
        "vendor": 0.0 if not doc["seller_name"] else (0.95 if doc["seller_gstin"] else 0.7),
        "invoice_number": 0.95 if doc["invoice_number"] else 0.0,
        "invoice_date": 0.0 if not doc["invoice_date"] else (0.7 if ambiguous_date else 0.95),
        "currency": 0.95 if doc["currency"] else 0.0,
        "total_stated": 0.0 if doc["total_stated"] is None else (0.98 if reconciled else 0.5),
    }


def _proposed_action(doc_type: str) -> str:
    return {
        "vendor_bill": "draft_bill",
        "sales_invoice": "reject_not_a_bill",
        "credit_note": "review_credit_note",
    }.get(doc_type, "review")


def _as_output(value: Optional[Decimal]) -> Optional[float]:
    return None if value is None else float(value)


def _counterparty(doc_type: str, parties: dict[str, Optional[str]], own_gstins: frozenset[str]
                  ) -> "tuple[Optional[str], Optional[str]]":
    """The other company on the document. Unknown stays empty rather than guessed."""
    seller = (parties["seller_name"], parties["seller_gstin"])
    buyer = (parties["buyer_name"], parties["buyer_gstin"])
    if doc_type == "vendor_bill":
        return seller
    if doc_type == "sales_invoice":
        return buyer
    if parties["seller_gstin"] in own_gstins:
        return buyer
    if parties["buyer_gstin"] in own_gstins:
        return seller
    return None, None


def _tax_type(taxes: list[dict[str, Any]]) -> str:
    kinds = {row["type"] for row in taxes}
    if not kinds:
        return "NONE"
    if kinds == {"CGST", "SGST"}:
        return "CGST_SGST"
    return "_".join(sorted(kinds))


def _tax_rate_percent(taxes: list[dict[str, Any]]) -> Optional[Any]:
    """The combined rate, so CGST 9% plus SGST 9% is 18. No tax is 0."""
    if not taxes:
        return 0
    if any(row["rate"] is None for row in taxes):
        return None
    total = sum(row["rate"] for row in taxes)
    return int(total) if total == int(total) else float(total)


def parse_document(text: str, own_gstins: frozenset[str] = SAMPLE_OWN_GSTINS,
                   base_currency: str = "INR") -> dict[str, Any]:
    """Parse one document's text into proposed fields, flags and a confidence."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {"doc_type": "unknown", "flags": ["no_text_layer"], "confidence": 0.0,
                "field_confidence": {}, "needs_review": True, "proposed_action": "review"}

    header_end = next((i for i, line in enumerate(lines) if TABLE_HEADER.search(line)), len(lines))
    subtotal_at = next((i for i, line in enumerate(lines) if SUBTOTAL_LABEL.match(line)), len(lines))
    header, table, footer = lines[:header_end], lines[header_end + 1:subtotal_at], lines[subtotal_at:]
    decimal_comma = _uses_decimal_comma(table + footer)

    parties = _party_details(lines)
    doc_type, flags = _classify(_title(header), parties["seller_gstin"], parties["buyer_gstin"], own_gstins)

    raw_date, raw_due = _first_labelled(header, DATE_LABEL), _first_labelled(header, DUE_LABEL)
    known_dates = [raw for raw in (raw_date, raw_due) if raw]
    day_first = _day_first(known_dates)
    bill_date = parse_date(raw_date, day_first is not False) if raw_date else None
    due_date = parse_date(raw_due, day_first is not False) if raw_due else None
    ambiguous_date = day_first is None and any(_is_ambiguous_numeric_date(raw) for raw in known_dates)
    if ambiguous_date:
        flags.append("ambiguous_date_order")
    if (raw_date and not bill_date) or (raw_due and not due_date):
        flags.append("unparsed_date")
    if not raw_due:
        flags.append("no_due_date")
    if bill_date and due_date and due_date < bill_date:
        flags.append("due_before_bill_date")

    items = _line_items(table, decimal_comma)
    totals = _read_totals(footer, decimal_comma)
    currency, currency_flags = _currency(totals["money_texts"])
    flags += currency_flags
    if currency and currency != base_currency:
        flags.append("foreign_currency")
    flags += _check_amounts(items, totals, parties["seller_gstin"], parties["buyer_gstin"])

    counterparty_name, counterparty_gstin = _counterparty(doc_type, parties, own_gstins)
    doc = {
        "doc_type": doc_type,
        **parties,
        "counterparty_name": counterparty_name,
        "counterparty_gstin": counterparty_gstin,
        "tax_type": _tax_type(totals["taxes"]),
        "tax_rate_percent": _tax_rate_percent(totals["taxes"]),
        "invoice_number": _document_number(header),
        "original_invoice": _first_labelled(header, ORIGINAL_LABEL),
        "invoice_date": bill_date.isoformat() if bill_date else None,
        "due_date": due_date.isoformat() if due_date else None,
        "currency": currency,
        "subtotal": _as_output(totals["net"]),
        "tax_total": _as_output(totals["tax"]),
        "total_stated": _as_output(totals["total"]),
        "lines": [{key: (float(v) if isinstance(v, Decimal) else v) for key, v in row.items()}
                       for row in items],
    }
    field_confidence = _confidence(doc, flags, ambiguous_date)
    confidence = min(field_confidence.values())
    doc.update({
        "flags": flags,
        "field_confidence": field_confidence,
        "confidence": confidence,
        "needs_review": confidence < REVIEW_THRESHOLD or bool(REVIEW_FLAGS & set(flags)),
        "proposed_action": _proposed_action(doc_type),
    })
    return doc


def _number_key(number: str) -> str:
    return re.sub(r"\s+", "", number).upper()


def mark_duplicates(docs: list[dict[str, Any]]) -> None:
    """Flag later documents that repeat an earlier one. Docs need a source_file."""
    by_number: dict[tuple, str] = {}
    by_content: dict[tuple, str] = {}
    for doc in docs:
        seller = doc.get("seller_gstin") or doc.get("seller_name")
        number_key = (seller, _number_key(doc["invoice_number"])) if doc.get("invoice_number") else None
        content_key = (seller, doc.get("invoice_date"), doc.get("total_stated"))
        if number_key and number_key in by_number:
            duplicate_of = by_number[number_key]
            doc["duplicate_of"] = duplicate_of
            doc["flags"].append("duplicate_of_" + duplicate_of.rsplit(".", 1)[0])
            doc["needs_review"] = True
            doc["proposed_action"] = "reject_duplicate"
        elif doc.get("invoice_date") and doc.get("total_stated") is not None and content_key in by_content:
            doc["duplicate_of"] = by_content[content_key]
            doc["flags"].append("possible_duplicate")
            doc["needs_review"] = True
        if number_key:
            by_number.setdefault(number_key, doc["source_file"])
        by_content.setdefault(content_key, doc["source_file"])
