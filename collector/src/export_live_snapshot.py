from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .sources.daily_monitor import DailyMonitorSource
from .sources.egp_uganda import EGPUgandaSource
from .sources.gpp_ppda import GPPPPDASource
from .sources.new_vision import NewVisionSource
from .sources.uganda_direct import KCCASource, MoFPEDSource, NITAUgandaSource, UCCSource, URASource
from .sources.world_bank import WorldBankUgandaSource


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "public" / "data"
SOURCES = (
    EGPUgandaSource(),
    NITAUgandaSource(),
    KCCASource(),
    URASource(),
    UCCSource(),
    MoFPEDSource(),
    WorldBankUgandaSource(),
    GPPPPDASource(),
    DailyMonitorSource(),
    NewVisionSource(),
)


def source_type(source_id: str) -> str:
    if source_id in {"daily-monitor", "new-vision"}:
        return "newspaper"
    if source_id in {"world-bank-uganda"}:
        return "development"
    return "government"


def iso(value):
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_id(canonical_key: str) -> str:
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:28]


def record_from_bid(bid, generated_at: str):
    deadline = bid.deadline_at
    now = datetime.now(deadline.tzinfo or timezone.utc) if deadline else datetime.now(timezone.utc)
    is_open = bid.status == "open" and (deadline is None or deadline >= now)
    sources = []
    for source_ref in bid.sources:
        source_id = next((source.source_id for source in SOURCES if source.name == source_ref.name), source_ref.name.lower().replace(" ", "-"))
        sources.append({
            "id": source_id,
            "name": source_ref.name,
            "url": str(source_ref.url),
            "detectedAt": iso(source_ref.detected_at) or generated_at,
        })
    return {
        "id": stable_id(bid.canonical_key()),
        "title": bid.title,
        "organization": bid.organization,
        "referenceNumber": bid.reference_number,
        "description": bid.description,
        "category": bid.category,
        "procurementType": bid.procurement_type,
        "publishedAt": iso(bid.published_at),
        "deadlineAt": iso(bid.deadline_at),
        "status": "open" if is_open else ("closed" if bid.status == "open" else bid.status),
        "isOpen": is_open,
        "fingerprint": bid.canonical_key(),
        "firstSeenAt": generated_at,
        "lastSeenAt": generated_at,
        "deadlineChanged": False,
        "sources": sources,
    }


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    merged: dict[str, object] = {}
    metas = []

    for source in SOURCES:
        attempted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            raw = source.fetch()
            bids = list(source.parse(raw))
            if not bids:
                raise RuntimeError("source returned zero normalized notices")
            print(f"{source.name}: parsed {len(bids)} notices")
            for bid in bids:
                key = bid.canonical_key()
                if key in merged:
                    existing = merged[key]
                    known_urls = {item["url"] for item in existing["sources"]}
                    for ref in record_from_bid(bid, generated_at)["sources"]:
                        if ref["url"] not in known_urls:
                            existing["sources"].append(ref)
                else:
                    merged[key] = record_from_bid(bid, generated_at)
            metas.append({
                "id": source.source_id,
                "name": source.name,
                "type": source_type(source.source_id),
                "baseUrl": source.url,
                "health": "healthy",
                "enabled": True,
                "lastSuccessfulCrawlAt": attempted_at,
                "lastAttemptedCrawlAt": attempted_at,
                "recordsFound": len(bids),
                "recordsCreated": len(bids),
                "recordsUpdated": 0,
                "recordsUnchanged": 0,
                "lastError": "",
            })
        except Exception as exc:  # noqa: BLE001 - one public source must not break every other source
            print(f"WARNING {source.name}: {exc}")
            metas.append({
                "id": source.source_id,
                "name": source.name,
                "type": source_type(source.source_id),
                "baseUrl": source.url,
                "health": "warning",
                "enabled": True,
                "lastSuccessfulCrawlAt": "",
                "lastAttemptedCrawlAt": attempted_at,
                "recordsFound": 0,
                "recordsCreated": 0,
                "recordsUpdated": 0,
                "recordsUnchanged": 0,
                "lastError": str(exc)[:300],
            })

    records = list(merged.values())
    if not records:
        raise RuntimeError("all public procurement sources returned zero records")

    status_rank = {"open": 0, "planned": 1, "evaluation": 2, "awarded": 3, "closed": 4, "cancelled": 5}
    records.sort(key=lambda item: (
        status_rank.get(item.get("status"), 9),
        item.get("deadlineAt") or "9999-12-31T23:59:59Z",
    ))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "bids.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA_DIR / "sources.json").write_text(json.dumps(metas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # Keep the old paths for users with cached JavaScript while the new build rolls out.
    (DATA_DIR / "egp-bids.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    egp_meta = next((item for item in metas if item["id"] == "egp-uganda"), metas[0])
    (DATA_DIR / "egp-meta.json").write_text(json.dumps(egp_meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    healthy = sum(1 for item in metas if item["health"] == "healthy")
    print(f"Exported {len(records)} searchable opportunities from {healthy}/{len(metas)} healthy sources to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
