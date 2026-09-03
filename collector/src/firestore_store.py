from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore

from .models import NormalizedBid


TRACKED_FIELDS = (
    "title",
    "organization",
    "referenceNumber",
    "description",
    "category",
    "procurementType",
    "publishedAt",
    "deadlineAt",
    "status",
    "isOpen",
)


@dataclass
class IngestionStats:
    found: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0


class FirestoreBidStore:
    def __init__(self, source_id: str, source_name: str, source_url: str):
        self.source_id = source_id
        self.source_name = source_name
        self.source_url = source_url
        self.db = self._client()

    @staticmethod
    def _client():
        if not firebase_admin._apps:
            raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
            if not raw:
                raise RuntimeError(
                    "FIREBASE_SERVICE_ACCOUNT_JSON is required for collector writes. "
                    "Store it as a GitHub Actions secret; never commit it."
                )
            try:
                service_account = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
            firebase_admin.initialize_app(credentials.Certificate(service_account))
        return firestore.client()

    def start_run(self) -> tuple[Any, datetime]:
        started = datetime.now(timezone.utc)
        ref = self.db.collection("crawlRuns").document()
        ref.set(
            {
                "sourceId": self.source_id,
                "sourceName": self.source_name,
                "status": "running",
                "startedAt": started,
                "recordsFound": 0,
                "recordsCreated": 0,
                "recordsUpdated": 0,
                "recordsUnchanged": 0,
            }
        )
        self.db.collection("sources").document(self.source_id).set(
            {
                "name": self.source_name,
                "type": "government",
                "baseUrl": self.source_url,
                "enabled": True,
                "health": "warning",
                "lastAttemptedCrawlAt": started,
                "updatedAt": started,
            },
            merge=True,
        )
        return ref, started

    def finish_run(self, run_ref: Any, stats: IngestionStats, *, error: str = "") -> None:
        finished = datetime.now(timezone.utc)
        status = "failed" if error else "success"
        run_ref.set(
            {
                "status": status,
                "finishedAt": finished,
                "recordsFound": stats.found,
                "recordsCreated": stats.created,
                "recordsUpdated": stats.updated,
                "recordsUnchanged": stats.unchanged,
                "error": error[:3000],
            },
            merge=True,
        )
        source_payload = {
            "name": self.source_name,
            "type": "government",
            "baseUrl": self.source_url,
            "enabled": True,
            "health": "warning" if error else "healthy",
            "lastAttemptedCrawlAt": finished,
            "recordsFound": stats.found,
            "recordsCreated": stats.created,
            "recordsUpdated": stats.updated,
            "recordsUnchanged": stats.unchanged,
            "lastError": error[:3000],
            "updatedAt": finished,
        }
        if not error:
            source_payload["lastSuccessfulCrawlAt"] = finished
        self.db.collection("sources").document(self.source_id).set(source_payload, merge=True)

    def ingest(self, bids: list[NormalizedBid]) -> IngestionStats:
        stats = IngestionStats(found=len(bids))
        for bid in bids:
            outcome = self.upsert_bid(bid)
            if outcome == "created":
                stats.created += 1
            elif outcome == "updated":
                stats.updated += 1
            else:
                stats.unchanged += 1
        return stats

    def upsert_bid(self, bid: NormalizedBid) -> str:
        now = datetime.now(timezone.utc)
        canonical_key = bid.canonical_key()
        bid_id = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:40]
        ref = self.db.collection("bids").document(bid_id)
        snapshot = ref.get()
        existing = snapshot.to_dict() if snapshot.exists else None

        primary_source = bid.sources[0]
        source_entry = {
            "id": self.source_id,
            "name": primary_source.name,
            "url": str(primary_source.url),
            "detectedAt": primary_source.detected_at,
        }
        payload = {
            "canonicalKey": canonical_key,
            "referenceNumber": bid.reference_number,
            "title": bid.title,
            "organization": bid.organization,
            "description": bid.description,
            "category": bid.category,
            "procurementType": bid.procurement_type,
            "publishedAt": bid.published_at,
            "deadlineAt": bid.deadline_at,
            "deadlinePrecision": bid.deadline_precision,
            "status": bid.status,
            "isOpen": bid.status == "open",
            "fingerprint": self._fingerprint(bid.reference_number or f"{bid.organization}-{bid.title}"),
            "lastSeenAt": now,
            "updatedAt": now,
            "ingestionMode": "automated",
        }

        if existing is None:
            payload["firstSeenAt"] = now
            payload["createdAt"] = now
            payload["sources"] = [source_entry]
            payload["deadlineChanged"] = False
            ref.set(payload)
            self._upsert_bid_source(ref, source_entry, now)
            self._upsert_organization(bid.organization, now)
            return "created"

        merged_sources = self._merge_sources(existing.get("sources", []), source_entry)
        payload["sources"] = merged_sources
        changes = self._detect_changes(existing, payload)
        if changes:
            deadline_changed = any(change["field"] == "deadlineAt" for change in changes)
            if deadline_changed:
                payload["deadlineChanged"] = True
                payload["deadlineChangedAt"] = now
            ref.set(payload, merge=True)
            for change in changes:
                ref.collection("changes").document().set(
                    {
                        **change,
                        "sourceId": self.source_id,
                        "sourceName": self.source_name,
                        "detectedAt": now,
                    }
                )
            outcome = "updated"
        else:
            ref.set(
                {
                    "lastSeenAt": now,
                    "sources": merged_sources,
                },
                merge=True,
            )
            outcome = "unchanged"

        self._upsert_bid_source(ref, source_entry, now)
        self._upsert_organization(bid.organization, now)
        return outcome

    def _upsert_bid_source(self, bid_ref: Any, source_entry: dict[str, Any], now: datetime) -> None:
        bid_ref.collection("sources").document(self.source_id).set(
            {
                **source_entry,
                "firstDetectedAt": firestore.SERVER_TIMESTAMP,
                "lastDetectedAt": now,
            },
            merge=True,
        )

    def _upsert_organization(self, organization: str, now: datetime) -> None:
        organization_id = hashlib.sha1(organization.lower().strip().encode("utf-8")).hexdigest()[:32]
        self.db.collection("organizations").document(organization_id).set(
            {
                "name": organization,
                "normalizedName": " ".join(organization.lower().split()),
                "lastSeenAt": now,
                "updatedAt": now,
            },
            merge=True,
        )

    @staticmethod
    def _merge_sources(existing: list[Any], incoming: dict[str, Any]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        replaced = False
        for item in existing if isinstance(existing, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("id") == incoming["id"] or item.get("name") == incoming["name"]:
                merged.append(incoming)
                replaced = True
            else:
                merged.append(item)
        if not replaced:
            merged.append(incoming)
        return merged

    @staticmethod
    def _detect_changes(existing: dict[str, Any], incoming: dict[str, Any]) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for field in TRACKED_FIELDS:
            old_value = existing.get(field)
            new_value = incoming.get(field)
            if FirestoreBidStore._comparable(old_value) == FirestoreBidStore._comparable(new_value):
                continue
            changes.append(
                {
                    "field": field,
                    "oldValue": FirestoreBidStore._serializable(old_value),
                    "newValue": FirestoreBidStore._serializable(new_value),
                }
            )
        return changes

    @staticmethod
    def _comparable(value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).replace(microsecond=0)
        return value

    @staticmethod
    def _serializable(value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @staticmethod
    def _fingerprint(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return normalized[:180]
