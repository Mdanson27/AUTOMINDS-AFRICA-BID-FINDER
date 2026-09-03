from __future__ import annotations

from datetime import datetime
import re
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

KAMPALA = ZoneInfo("Africa/Kampala")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


def parse_date(value: str) -> datetime | None:
    value = clean(value)
    if not value:
        return None
    value = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", value, flags=re.I)
    try:
        parsed = date_parser.parse(value, fuzzy=True, dayfirst=True)
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KAMPALA)
    return parsed.astimezone(KAMPALA)


def extract_deadline(text: str) -> datetime | None:
    text = clean(text)
    if not text:
        return None
    month = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    patterns = [
        rf"(?:deadline|closing date|submission deadline|submit(?:ted)?[^.{{0,70}}]? by|no later than|before)\D{{0,70}}?(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+20\d{{2}}(?:\s+(?:at\s+)?\d{{1,2}}(?::\d{{2}})?\s*(?:AM|PM|hours?)?)?)",
        rf"(?:deadline|closing date|submission deadline|no later than|before)\D{{0,70}}?({month}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+20\d{{2}}(?:\s+(?:at\s+)?\d{{1,2}}(?::\d{{2}})?\s*(?:AM|PM)?)?)",
        r"(?:deadline|closing date|submission deadline)\D{0,40}?(20\d{2}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                return parsed
    return None


def extract_reference(text: str) -> str:
    text = clean(text)
    patterns = [
        r"(?:procurement\s+reference(?:\s+number)?|reference|ref\.?|rfq\s*no\.?|rfp\s*no\.?|itb\s*no\.?|eoi\s*no\.?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/()\-]{4,})",
        r"\b([A-Z]{2,}[A-Z0-9._/-]*/[A-Z0-9._/-]+/20\d{2}(?:-20\d{2})?/[A-Z0-9._/-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return clean(match.group(1)).strip(".,;:")
    return ""


def infer_type(title: str, text: str = "") -> str:
    haystack = f"{title} {text}".lower()
    if "pre-qualification" in haystack or "prequalification" in haystack:
        return "Prequalification"
    if "expression of interest" in haystack or re.search(r"\beoi\b", haystack):
        return "Expression of Interest"
    if "request for proposal" in haystack or re.search(r"\brfp\b", haystack):
        return "Request for Proposal"
    if "request for quotation" in haystack or re.search(r"\brfq\b", haystack):
        return "Request for Quotation"
    if "consultancy" in haystack or "consultant" in haystack:
        return "Consultancy"
    if "invitation to bid" in haystack or "invitation for bids" in haystack:
        return "Invitation to Bid"
    if "sale" in haystack or "auction" in haystack:
        return "Disposal"
    return "Tender"


def organization_from_title(title: str) -> str:
    title = clean(title)
    for separator in (" – ", " - ", ": "):
        if separator in title:
            candidate = clean(title.split(separator, 1)[0])
            if 2 < len(candidate) < 120:
                return candidate
    return "Published procurement notice"
