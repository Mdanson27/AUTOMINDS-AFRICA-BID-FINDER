from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import firebase_admin
import httpx
from firebase_admin import auth, credentials

DEFAULT_NEON_DATA_API_URL = "https://ep-frosty-bar-b5zf1qa1.apirest.c-7.us-east-2.aws.neon.tech/bidfinder/rest/v1"
DATA_DIR = Path("public/data")


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:120] or "unknown"


def _load_json(name: str, default: Any) -> Any:
    path = DATA_DIR / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _pg_safe(value: Any) -> Any:
    """Recursively remove NUL characters that PostgreSQL text/jsonb cannot store."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_pg_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_pg_safe(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key).replace("\x00", ""): _pg_safe(item)
            for key, item in value.items()
        }
    return value


def _collector_id_token() -> str:
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    api_key = os.environ.get("NEXT_PUBLIC_FIREBASE_API_KEY", "").strip()
    if not raw or not api_key:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON and NEXT_PUBLIC_FIREBASE_API_KEY are required for Neon sync")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))

    custom = auth.create_custom_token("bidfinder-collector")
    if isinstance(custom, bytes):
        custom = custom.decode("utf-8")

    response = httpx.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}",
        json={"token": custom, "returnSecureToken": True},
        timeout=30.0,
    )
    response.raise_for_status()
    token = response.json().get("idToken")
    if not token:
        raise RuntimeError("Firebase did not return an ID token for the collector identity")
    return str(token)


class NeonWriter:
    def __init__(self, token: str) -> None:
        self.base_url = os.environ.get("NEON_DATA_API_URL", DEFAULT_NEON_DATA_API_URL).rstrip("/")
        self.client = httpx.Client(
            timeout=45.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self.client.close()

    def upsert(self, table: str, rows: Iterable[dict[str, Any]], conflict: str, batch_size: int = 100) -> int:
        values = list(rows)
        if not values:
            return 0
        written = 0
        for start in range(0, len(values), batch_size):
            # PostgreSQL rejects U+0000 in both text and jsonb. Sanitizing at the
            # single database egress point protects all current and future nested
            # collector fields without weakening source-specific extraction.
            batch = [_pg_safe(item) for item in values[start : start + batch_size]]
            response = self.client.post(
                f"{self.base_url}/{table}",
                params={"on_conflict": conflict},
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                json=batch,
            )
            if response.status_code >= 400:
                raise RuntimeError(f"Neon {table} upsert failed ({response.status_code}): {response.text[:1200]}")
            written += len(batch)
        return written


def _source_row(source: dict[str, Any]) -> dict[str, Any]:
    source_id = str(source.get("id") or _slug(str(source.get("name") or "source")))
    return {
        "id": source_id,
        "name": str(source.get("name") or source_id),
        "source_type": str(source.get("type") or "website"),
        "source_group": str(source.get("sourceGroup") or source.get("group") or "other"),
        "base_url": str(source.get("baseUrl") or source.get("url") or ""),
        "health": str(source.get("health") or "planned"),
        "enabled": source.get("enabled") is not False,
        "last_successful_crawl_at": source.get("lastSuccessfulCrawlAt") or None,
        "last_attempted_crawl_at": source.get("lastAttemptedCrawlAt") or None,
        "records_found": int(source.get("recordsFound") or 0),
        "records_created": int(source.get("recordsCreated") or 0),
        "records_updated": int(source.get("recordsUpdated") or 0),
        "records_unchanged": int(source.get("recordsUnchanged") or 0),
        "last_error": str(source.get("lastError") or ""),
        "metadata": source,
    }


def _bid_row(bid: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(bid.get("id") or bid.get("fingerprint") or _slug(str(bid.get("title") or "bid"))),
        "title": str(bid.get("title") or "Untitled opportunity"),
        "organization": str(bid.get("organization") or ""),
        "reference_number": str(bid.get("referenceNumber") or ""),
        "description": str(bid.get("description") or ""),
        "category": str(bid.get("category") or ""),
        "procurement_type": str(bid.get("procurementType") or ""),
        "procurement_method": str(bid.get("procurementMethod") or ""),
        "source_stage": str(bid.get("sourceStage") or ""),
        "canonical_source": str(bid.get("canonicalSource") or ""),
        "canonical_source_url": str(bid.get("canonicalSourceUrl") or ""),
        "canonical_identity": str(bid.get("canonicalIdentity") or ""),
        "title_specificity": str(bid.get("titleSpecificity") or ""),
        "title_source": str(bid.get("titleSource") or ""),
        "display_eligible": bid.get("displayEligible") is not False,
        "opportunity_type": str(bid.get("opportunityType") or "tender"),
        "notice_type": str(bid.get("noticeType") or ""),
        "status": str(bid.get("status") or "open"),
        "is_open": bid.get("isOpen") is not False,
        "fingerprint": str(bid.get("fingerprint") or ""),
        "published_at": bid.get("publishedAt") or None,
        "deadline_at": bid.get("deadlineAt"),
        "opening_at": bid.get("openingAt") or None,
        "application_url": str(bid.get("applicationUrl") or ""),
        "first_seen_at": bid.get("firstSeenAt") or None,
        "first_detected_at": bid.get("firstDetectedAt") or None,
        "last_seen_at": bid.get("lastSeenAt") or None,
        "last_verified_at": bid.get("lastVerifiedAt") or None,
        "verification_status": str(bid.get("verificationStatus") or ""),
        "verification_note": str(bid.get("verificationNote") or ""),
        "retention_status": str(bid.get("retentionStatus") or ""),
        "retained_from_previous_snapshot": bid.get("retainedFromPreviousSnapshot") is True,
        "deadline_changed": bid.get("deadlineChanged") is True,
        "deadline_changed_at": bid.get("deadlineChangedAt") or None,
        "documents": bid.get("documents") or [],
        "source_metadata": bid.get("sourceMetadata") or {},
        "intelligence": bid.get("intelligence") or None,
        "contacts": bid.get("contacts") or [],
        "bidders": bid.get("bidders") or [],
        "bids_received": bid.get("bidsReceived"),
        "opening_participants": bid.get("openingParticipants") or [],
        "opening_committee": bid.get("openingCommittee") or [],
        "amendments": bid.get("amendments") or [],
        "lifecycle_events": bid.get("lifecycleEvents") or [],
        "best_evaluated_bidder": str(bid.get("bestEvaluatedBidder") or ""),
        "contract_amount": str(bid.get("contractAmount") or ""),
        "contract_currency": str(bid.get("contractCurrency") or ""),
        "phase4_enriched": bid.get("phase4Enriched") is True,
        "raw_record": bid,
    }


def _bid_source_rows(bids: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    links: list[dict[str, Any]] = []
    discovered_sources: dict[str, dict[str, Any]] = {}
    for bid in bids:
        bid_id = str(bid.get("id") or bid.get("fingerprint") or _slug(str(bid.get("title") or "bid")))
        for source in bid.get("sources") or []:
            if not isinstance(source, dict):
                continue
            name = str(source.get("name") or "Source")
            source_id = str(source.get("id") or _slug(name))
            url = str(source.get("url") or bid.get("canonicalSourceUrl") or "#")
            discovered_sources[source_id] = {
                "id": source_id,
                "name": name,
                "type": "website",
                "baseUrl": url,
                "health": "healthy",
                "enabled": True,
            }
            links.append({
                "bid_id": bid_id,
                "source_id": source_id,
                "source_name": name,
                "source_url": url,
                "source_reference": str(bid.get("referenceNumber") or ""),
                "detected_at": source.get("detectedAt") or bid.get("firstDetectedAt") or bid.get("firstSeenAt") or None,
                "deadline_at": bid.get("deadlineAt") or None,
                "published_at": bid.get("publishedAt") or None,
                "verified": str(bid.get("verificationStatus") or "") == "verified",
                "raw_record": source,
            })
    return links, list(discovered_sources.values())


def _grant_row(grant: dict[str, Any]) -> dict[str, Any] | None:
    deadline = grant.get("deadlineAt")
    if not deadline:
        return None
    return {
        "id": str(grant.get("id") or _slug(str(grant.get("title") or "grant"))),
        "title": str(grant.get("title") or "Untitled grant"),
        "organization": str(grant.get("funder") or grant.get("organization") or ""),
        "description": str(grant.get("summary") or grant.get("description") or ""),
        "category": str(grant.get("category") or "grant"),
        "published_at": grant.get("openDate") or grant.get("publishedAt") or None,
        "deadline_at": deadline,
        "source_id": _slug(str(grant.get("sourceName") or "grant-source")),
        "source_url": str(grant.get("sourceUrl") or ""),
        "display_eligible": str(grant.get("status") or "open") != "closed",
        "raw_record": grant,
    }


def _plan_row(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(plan.get("id") or _slug(str(plan.get("name") or "plan"))),
        "name": str(plan.get("name") or "Procurement plan"),
        "organization": str(plan.get("organization") or ""),
        "financial_year": str(plan.get("financialYear") or ""),
        "total_estimated_amount_ugx": str(plan.get("totalEstimatedAmountUGX") or ""),
        "source_url": str(plan.get("sourceUrl") or ""),
        "pdf_url": str(plan.get("pdfUrl") or ""),
        "excel_url": str(plan.get("excelUrl") or ""),
        "collected_at": plan.get("collectedAt") or None,
        "items": plan.get("items") or [],
        "raw_record": plan,
    }


def sync() -> None:
    bids = _load_json("bids.json", [])
    sources = _load_json("sources.json", [])
    grants = _load_json("grants.json", [])
    plans = _load_json("plans.json", [])
    if not isinstance(bids, list) or not isinstance(sources, list):
        raise RuntimeError("Canonical Bid Finder snapshots are invalid")

    bid_source_links, discovered = _bid_source_rows([item for item in bids if isinstance(item, dict)])
    source_map: dict[str, dict[str, Any]] = {}
    for source in [*sources, *discovered]:
        if isinstance(source, dict):
            row = _source_row(source)
            source_map[row["id"]] = row

    # Grant-only publishers also need a source record before the FK can be written.
    for grant in grants if isinstance(grants, list) else []:
        if not isinstance(grant, dict):
            continue
        name = str(grant.get("sourceName") or "Grant source")
        source_id = _slug(name)
        source_map.setdefault(source_id, _source_row({"id": source_id, "name": name, "baseUrl": grant.get("sourceUrl") or "", "health": "healthy", "enabled": True}))

    writer = NeonWriter(_collector_id_token())
    try:
        written_sources = writer.upsert("sources", source_map.values(), "id")
        valid_bids = [item for item in bids if isinstance(item, dict) and item.get("deadlineAt")]
        written_bids = writer.upsert("bids", (_bid_row(item) for item in valid_bids), "id")
        written_links = writer.upsert("bid_sources", bid_source_links, "bid_id,source_id,source_url")
        valid_grants = [row for item in grants if isinstance(item, dict) for row in [_grant_row(item)] if row]
        written_grants = writer.upsert("grants", valid_grants, "id")
        valid_plans = [_plan_row(item) for item in plans if isinstance(item, dict)] if isinstance(plans, list) else []
        written_plans = writer.upsert("procurement_plans", valid_plans, "id")
    finally:
        writer.close()

    print(
        "Neon sync complete: "
        f"sources={written_sources}, bids={written_bids}, bid_sources={written_links}, "
        f"grants={written_grants}, plans={written_plans}"
    )


if __name__ == "__main__":
    sync()
