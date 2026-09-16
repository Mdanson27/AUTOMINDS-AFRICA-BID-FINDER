from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BIDS_PATH = ROOT / "public" / "data" / "bids.json"
EGP_PATH = ROOT / "public" / "data" / "egp-bids.json"
CLOSED_RETENTION_DAYS = 3

GRANT_TERMS = (
    "grant",
    "grants",
    "funding opportunity",
    "call for proposals",
    "call for proposal",
    "request for proposals",
    "innovation fund",
    "challenge fund",
    "seed fund",
    "matching grant",
    "small grants",
    "funding window",
    "financial support",
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


def detect_opportunity_type(record: dict) -> str:
    existing = str(record.get("opportunityType", "")).lower().strip()
    if existing in {"grant", "tender", "other"}:
        return existing

    metadata = record.get("sourceMetadata") or {}
    text = " ".join(
        str(value)
        for value in [
            record.get("title", ""),
            record.get("description", ""),
            record.get("category", ""),
            record.get("procurementType", ""),
            record.get("noticeType", ""),
            *metadata.values(),
        ]
        if value
    ).lower()

    if any(term in text for term in GRANT_TERMS):
        return "grant"
    return "tender"


def process_records(records: list[dict], now: datetime) -> list[dict]:
    oldest_closed = now - timedelta(days=CLOSED_RETENTION_DAYS)
    output: list[dict] = []

    for record in records:
        deadline = parse_iso(str(record.get("deadlineAt", "")))
        if deadline is None:
            continue

        is_open = deadline >= now
        if not is_open and deadline < oldest_closed:
            continue

        record = dict(record)
        record["isOpen"] = is_open
        if record.get("status") not in {"planned", "cancelled", "awarded"}:
            record["status"] = "open" if is_open else "closed"
        elif record.get("status") == "planned" and not is_open:
            record["status"] = "closed"
        record["opportunityType"] = detect_opportunity_type(record)
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
        f"Postprocessed opportunities: bids {before}->{after}, eGP {egp_before}->{egp_after}; "
        f"closed retention={CLOSED_RETENTION_DAYS} days; opportunity typing enabled"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
