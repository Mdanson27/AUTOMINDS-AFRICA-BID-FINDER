from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
BIDS_PATH = ROOT / "public" / "data" / "bids.json"
EGP_PATH = ROOT / "public" / "data" / "egp-bids.json"
CLOSED_RETENTION_DAYS = 3

TITLE_METADATA_KEYS = (
    "subject of procurement",
    "procurement subject",
    "tender title",
    "bid title",
    "title of procurement",
    "description of procurement",
)
METHOD_METADATA_KEYS = (
    "procurement method",
    "method of procurement",
    "procurement procedure",
)
VAGUE_TITLE_PATTERNS = (
    r"^request for quotations?(?:/proposals?)?$",
    r"^request for proposals?$",
    r"^request for quotation notice$",
    r"^invitation to bid$",
    r"^invitation for bids$",
    r"^open domestic bidding$",
    r"^open international bidding$",
    r"^micro procurement$",
    r"^direct procurement$",
    r"^restricted bidding$",
    r"^expression of interest$",
    r"^procurement notice$",
    r"^bid notice$",
)
METHOD_HINTS = (
    "request for quotation",
    "request for proposal",
    "open domestic bidding",
    "open international bidding",
    "micro procurement",
    "direct procurement",
    "restricted bidding",
    "quality and cost based selection",
    "consultant qualification selection",
)


def parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean_text(value).lower()).strip()


def metadata_value(record: dict, accepted_keys: tuple[str, ...]) -> str:
    metadata = record.get("sourceMetadata") or {}
    if not isinstance(metadata, dict):
        return ""
    normalized_targets = {normalized_key(key) for key in accepted_keys}
    for raw_key, raw_value in metadata.items():
        if normalized_key(raw_key) in normalized_targets:
            value = clean_text(raw_value)
            if value:
                return value
    return ""


def is_vague_title(value: str) -> bool:
    title = clean_text(value).lower().strip(" .:-")
    if not title:
        return True
    return any(re.fullmatch(pattern, title, flags=re.IGNORECASE) for pattern in VAGUE_TITLE_PATTERNS)


def authoritative_title(record: dict) -> str:
    """Prefer an explicit procurement subject/title over method-like labels."""
    subject = metadata_value(record, TITLE_METADATA_KEYS)
    current = clean_text(record.get("title"))

    if subject and not is_vague_title(subject):
        return subject
    return current


def procurement_method(record: dict) -> str:
    explicit = metadata_value(record, METHOD_METADATA_KEYS)
    if explicit:
        return explicit

    legacy = clean_text(record.get("procurementType"))
    lower = legacy.lower()
    if any(hint in lower for hint in METHOD_HINTS):
        return legacy
    return ""


def source_stage(record: dict) -> str:
    explicit = metadata_value(record, ("source stage", "procurement stage", "notice stage"))
    if explicit:
        return explicit

    metadata = record.get("sourceMetadata") or {}
    metadata_keys = " ".join(normalized_key(key) for key in metadata.keys()) if isinstance(metadata, dict) else ""
    if record.get("openingAt") or "bids received" in metadata_keys or "date and time of bid opening" in metadata_keys:
        return "Bid opening"

    status = clean_text(record.get("status")).lower()
    if status == "evaluation":
        return "Evaluation"
    if status == "awarded":
        return "Contract award"
    if status == "cancelled":
        return "Cancelled"
    if status == "closed":
        return "Closed"
    return "Bidding / submission"


def canonical_source(record: dict) -> tuple[str, str]:
    sources = record.get("sources") or []
    if not isinstance(sources, list) or not sources:
        return "", ""
    first = sources[0] if isinstance(sources[0], dict) else {}
    return clean_text(first.get("name")), clean_text(first.get("url"))


def canonical_identity(record: dict) -> str:
    """Build identity from multiple stable procurement fields.

    Reference + organization is preferred because a reference alone can be
    reused or conflict. Without a reference, organization + authoritative title
    + canonical source is used. Deadline is intentionally excluded so an
    extension does not manufacture a second procurement record.
    """
    reference = re.sub(r"\s+", "", clean_text(record.get("referenceNumber")).lower())
    organization = normalized_key(record.get("organization"))
    title = normalized_key(record.get("title"))
    source_name, _ = canonical_source(record)
    source = normalized_key(source_name)

    if reference:
        return f"ref-org:{reference}|{organization}"
    return f"org-title-source:{organization}|{title}|{source}"


def stable_id(identity: str) -> str:
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:28]


def apply_canonical_fields(record: dict) -> dict:
    record = dict(record)

    title = authoritative_title(record)
    if title:
        record["title"] = title[:320]

    method = procurement_method(record)
    record["procurementMethod"] = method[:140]
    record["sourceStage"] = source_stage(record)[:80]

    source_name, source_url = canonical_source(record)
    record["canonicalSource"] = source_name[:120]
    record["canonicalSourceUrl"] = source_url

    identity = canonical_identity(record)
    record["canonicalIdentity"] = identity
    record["fingerprint"] = identity
    record["id"] = stable_id(identity)
    return record


def process_records(records: list[dict], now: datetime) -> list[dict]:
    """Apply canonical bid fields and current bid retention.

    Procurement snapshots are procurement records, not grant records. They are
    therefore always typed as tenders. Grants are collected independently into
    public/data/grants.json by export_grants.py.
    """
    oldest_closed = now - timedelta(days=CLOSED_RETENTION_DAYS)
    output: list[dict] = []

    for raw_record in records:
        record = apply_canonical_fields(raw_record)
        deadline = parse_iso(str(record.get("deadlineAt", "")))
        if deadline is None:
            continue

        is_open = deadline >= now
        if not is_open and deadline < oldest_closed:
            continue

        record["isOpen"] = is_open
        if record.get("status") not in {"planned", "cancelled", "awarded"}:
            record["status"] = "open" if is_open else "closed"
        elif record.get("status") == "planned" and not is_open:
            record["status"] = "closed"
        record["sourceStage"] = source_stage(record)[:80]
        record["opportunityType"] = "tender"
        output.append(record)

    return output


def process_file(path: Path, now: datetime) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"Expected a list in {path}")
    processed = process_records(records, now)
    path.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(records), len(processed)


def main() -> int:
    now = datetime.now(timezone.utc)
    before, after = process_file(BIDS_PATH, now)
    egp_before, egp_after = process_file(EGP_PATH, now)
    print(
        f"Postprocessed procurement: bids {before}->{after}, eGP {egp_before}->{egp_after}; "
        f"canonical titles/identity applied; closed retention={CLOSED_RETENTION_DAYS} days; "
        "procurement records forced to tender"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
