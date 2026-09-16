from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BIDS_PATH = ROOT / "public" / "data" / "bids.json"
EGP_PATH = ROOT / "public" / "data" / "egp-bids.json"
CLOSED_RETENTION_DAYS = 3


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


def process_records(records: list[dict], now: datetime) -> list[dict]:
    """Apply bid retention only.

    Procurement snapshots are procurement records, not grant records. They are
    therefore always typed as tenders. Grants are collected independently into
    public/data/grants.json by export_grants.py.
    """
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
        f"closed retention={CLOSED_RETENTION_DAYS} days; procurement records forced to tender"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
