from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "public" / "data"
CURRENT_BIDS_PATH = DATA_DIR / "bids.json"
PREVIOUS_BIDS_PATH = DATA_DIR / "previous-bids.json"
COLLECTION = "bidFinderPersistentBids"
STATE_COLLECTION = "bidFinderSystemState"
STATE_DOCUMENT = "procurementPersistence"


def _client():
    if not firebase_admin._apps:
        raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        if not raw:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is required for persistent bid storage")
        try:
            service_account = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
        firebase_admin.initialize_app(credentials.Certificate(service_account))

    database_id = os.environ.get("FIRESTORE_DATABASE_ID", "default").strip() or "default"
    return firestore.client(database_id=database_id)


def load_previous_snapshot(*, fallback_to_current_file: bool = True) -> int:
    """Materialize durable procurement history for the next collector run.

    On the first migration run, the committed current snapshot is used as a
    bootstrap if the dedicated persistence collection is still empty.
    """
    db = _client()
    records: list[dict] = []
    for snapshot in db.collection(COLLECTION).stream():
        value = snapshot.to_dict() or {}
        record = value.get("record") if isinstance(value, dict) else None
        if isinstance(record, dict):
            records.append(record)

    if not records and fallback_to_current_file and CURRENT_BIDS_PATH.exists():
        current = json.loads(CURRENT_BIDS_PATH.read_text(encoding="utf-8"))
        if isinstance(current, list):
            records = [item for item in current if isinstance(item, dict)]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PREVIOUS_BIDS_PATH.write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Loaded {len(records)} persistent procurement records")
    return len(records)


def save_current_snapshot() -> int:
    """Persist the fully merged Bid Finder procurement history."""
    if not CURRENT_BIDS_PATH.exists():
        raise RuntimeError("public/data/bids.json does not exist")

    records = json.loads(CURRENT_BIDS_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise RuntimeError("public/data/bids.json must contain a list")

    db = _client()
    batch = db.batch()
    pending = 0
    written = 0
    now = datetime.now(timezone.utc)

    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = str(record.get("id") or "").strip()
        if not record_id:
            raise RuntimeError("Cannot persist bid without id")
        ref = db.collection(COLLECTION).document(record_id)
        batch.set(
            ref,
            {
                "record": record,
                "updatedAt": now,
                "status": str(record.get("status") or ""),
                "deadlineAt": str(record.get("deadlineAt") or ""),
                "verificationStatus": str(record.get("verificationStatus") or ""),
            },
            merge=True,
        )
        pending += 1
        written += 1
        if pending >= 400:
            batch.commit()
            batch = db.batch()
            pending = 0

    if pending:
        batch.commit()

    db.collection(STATE_COLLECTION).document(STATE_DOCUMENT).set(
        {
            "updatedAt": now,
            "recordCount": written,
            "storageVersion": 2,
        },
        merge=True,
    )
    print(f"Persisted {written} procurement records")
    return written


def main() -> int:
    action = os.environ.get("BID_PERSISTENCE_ACTION", "load").strip().lower()
    if action == "load":
        load_previous_snapshot()
        return 0
    if action == "save":
        save_current_snapshot()
        return 0
    raise RuntimeError(f"Unknown BID_PERSISTENCE_ACTION: {action}")


if __name__ == "__main__":
    raise SystemExit(main())
