from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .sources.egp_uganda import EGPUgandaSource


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "public" / "data"


def iso(value):
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def bid_id(canonical_key: str) -> str:
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:28]


def main() -> int:
    source = EGPUgandaSource()
    raw = source.fetch()
    bids = list(source.parse(raw))
    if not bids:
        raise RuntimeError("eGP Uganda returned zero normalized notices")

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = []
    for bid in bids:
        source_ref = bid.sources[0] if bid.sources else None
        deadline = bid.deadline_at
        is_open = bid.status == "open" and (deadline is None or deadline > datetime.now(deadline.tzinfo or timezone.utc))
        records.append({
            "id": bid_id(bid.canonical_key()),
            "title": bid.title,
            "organization": bid.organization,
            "referenceNumber": bid.reference_number,
            "description": bid.description,
            "category": bid.category,
            "procurementType": bid.procurement_type,
            "publishedAt": iso(bid.published_at),
            "deadlineAt": iso(bid.deadline_at),
            "status": "open" if is_open else bid.status,
            "isOpen": is_open,
            "fingerprint": bid.canonical_key(),
            "firstSeenAt": generated_at,
            "lastSeenAt": generated_at,
            "deadlineChanged": False,
            "sources": [{
                "id": source.source_id,
                "name": source.name,
                "url": str(source_ref.url) if source_ref else source.url,
                "detectedAt": iso(source_ref.detected_at) if source_ref else generated_at,
            }],
        })

    records.sort(key=lambda item: item.get("deadlineAt") or "9999-12-31T23:59:59Z")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "egp-bids.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA_DIR / "egp-meta.json").write_text(json.dumps({
        "id": source.source_id,
        "name": source.name,
        "type": "government",
        "baseUrl": source.url,
        "health": "healthy",
        "enabled": True,
        "lastSuccessfulCrawlAt": generated_at,
        "lastAttemptedCrawlAt": generated_at,
        "recordsFound": len(records),
        "recordsCreated": len(records),
        "recordsUpdated": 0,
        "recordsUnchanged": 0,
        "lastError": "",
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Exported {len(records)} live eGP Uganda bids to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
