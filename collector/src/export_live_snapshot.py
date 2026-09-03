from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .sources.afdb_uganda import AfDBUgandaSource
from .sources.common_web import clean
from .sources.daily_monitor import DailyMonitorSource
from .sources.egp_uganda import EGPUgandaSource
from .sources.gpp_ppda import GPPPPDASource
from .sources.new_vision import NewVisionSource
from .sources.uganda_direct import KCCASource, MoFPEDSource, NITAUgandaSource, UCCSource, URASource
from .sources.undp_uganda import UNDPUgandaSource
from .sources.world_bank import WorldBankUgandaSource


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "public" / "data"
KAMPALA = ZoneInfo("Africa/Kampala")
MAX_DAYS_AHEAD = 90
MIN_FINANCIAL_YEAR_START = datetime(2026, 7, 1, tzinfo=KAMPALA)

SOURCES = (
    EGPUgandaSource(),
    NITAUgandaSource(),
    KCCASource(),
    URASource(),
    UCCSource(),
    MoFPEDSource(),
    WorldBankUgandaSource(),
    UNDPUgandaSource(),
    AfDBUgandaSource(),
    GPPPPDASource(),
    DailyMonitorSource(),
    NewVisionSource(),
)


def source_type(source_id: str) -> str:
    if source_id in {"daily-monitor", "new-vision"}:
        return "newspaper"
    if source_id in {"world-bank-uganda", "undp-uganda", "afdb-uganda"}:
        return "development"
    return "government"


def financial_year_start(now: datetime) -> datetime:
    local_now = now.astimezone(KAMPALA)
    year = local_now.year if local_now.month >= 7 else local_now.year - 1
    start = datetime(year, 7, 1, tzinfo=KAMPALA)
    return max(start, MIN_FINANCIAL_YEAR_START)


def is_eligible_bid(bid, now: datetime) -> bool:
    """Keep only current-FY opportunities with a real deadline no more than 90 days ahead."""
    if bid.status in {"cancelled", "awarded"}:
        return False
    if bid.deadline_at is None:
        return False

    local_now = now.astimezone(KAMPALA)
    start = financial_year_start(local_now)
    deadline = bid.deadline_at.astimezone(KAMPALA)
    latest = local_now + timedelta(days=MAX_DAYS_AHEAD)

    if deadline < start or deadline > latest:
        return False

    if bid.published_at is not None and bid.published_at.astimezone(KAMPALA) < start:
        return False

    return True


def iso(value):
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_id(canonical_key: str) -> str:
    return hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:28]


def record_from_bid(bid, generated_at: str, now: datetime):
    deadline = bid.deadline_at
    is_open = bool(deadline and deadline >= now)
    status = "planned" if is_open and bid.status == "planned" else ("open" if is_open else "closed")
    sources = []
    for source_ref in bid.sources:
        source_id = next((source.source_id for source in SOURCES if source.name == source_ref.name), source_ref.name.lower().replace(" ", "-"))
        sources.append({
            "id": source_id,
            "name": clean(source_ref.name),
            "url": str(source_ref.url),
            "detectedAt": iso(source_ref.detected_at) or generated_at,
        })

    title = clean(bid.title)[:240]
    description = clean(bid.description)[:1600]
    organization = clean(bid.organization)[:180]
    category = clean(bid.category)[:120]
    procurement_type = clean(bid.procurement_type)[:100]
    reference = clean(bid.reference_number)[:140]

    return {
        "id": stable_id(bid.canonical_key()),
        "title": title,
        "organization": organization,
        "referenceNumber": reference,
        "description": description,
        "category": category,
        "procurementType": procurement_type,
        "publishedAt": iso(bid.published_at),
        "deadlineAt": iso(deadline),
        "status": status,
        "isOpen": is_open,
        "fingerprint": bid.canonical_key(),
        "firstSeenAt": generated_at,
        "lastSeenAt": generated_at,
        "deadlineChanged": False,
        "sources": sources,
    }


def main() -> int:
    now = datetime.now(KAMPALA)
    generated_at = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    merged: dict[str, object] = {}
    metas = []

    for source in SOURCES:
        attempted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            raw = source.fetch()
            bids = list(source.parse(raw))
            if not bids:
                raise RuntimeError("source returned zero normalized notices")

            eligible = [bid for bid in bids if is_eligible_bid(bid, now)]
            print(f"{source.name}: parsed {len(bids)} notices; kept {len(eligible)} in FY/current 90-day window")

            for bid in eligible:
                key = bid.canonical_key()
                if key in merged:
                    existing = merged[key]
                    known_urls = {item["url"] for item in existing["sources"]}
                    for ref in record_from_bid(bid, generated_at, now)["sources"]:
                        if ref["url"] not in known_urls:
                            existing["sources"].append(ref)
                else:
                    merged[key] = record_from_bid(bid, generated_at, now)

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
                "recordsCreated": len(eligible),
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
        raise RuntimeError("all public procurement sources returned zero eligible records")

    status_rank = {"open": 0, "planned": 1, "closed": 4}
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
    print(
        f"Exported {len(records)} eligible opportunities from {healthy}/{len(metas)} healthy sources "
        f"(financial year starts {financial_year_start(now).date()}, maximum {MAX_DAYS_AHEAD} days ahead)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
