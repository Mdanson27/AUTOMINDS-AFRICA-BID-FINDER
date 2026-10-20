from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone


def parse_iso(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_key(record: dict) -> str:
    return str(
        record.get("canonicalIdentity")
        or record.get("fingerprint")
        or record.get("id")
        or ""
    ).strip()


def source_keys(record: dict) -> set[str]:
    keys: set[str] = set()
    for source in record.get("sources") or []:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id") or "").strip().lower()
        name = str(source.get("name") or "").strip().lower()
        if source_id:
            keys.add(source_id)
        if name:
            keys.add(name)
    return keys


def source_health_index(source_metas: list[dict]) -> dict[str, str]:
    index: dict[str, str] = {}
    for meta in source_metas:
        if not isinstance(meta, dict):
            continue
        health = str(meta.get("health") or "warning").strip().lower()
        source_id = str(meta.get("id") or "").strip().lower()
        name = str(meta.get("name") or "").strip().lower()
        if source_id:
            index[source_id] = health
        if name:
            index[name] = health
    return index


def verification_status_for_missing(record: dict, source_metas: list[dict]) -> tuple[str, str]:
    """Explain why a retained record was not re-verified this scan.

    A failed/degraded source changes verification state only. It never removes
    the procurement record. If at least one known source completed healthy but
    omitted the record, we mark it not seen in the current scan while retaining
    it until/after its deadline for procurement history.
    """
    health = source_health_index(source_metas)
    relevant = [health[key] for key in source_keys(record) if key in health]
    if relevant and all(item != "healthy" for item in relevant):
        return "source-unavailable", "Source scan failed or was degraded; existing bid retained."
    if any(item == "healthy" for item in relevant):
        return "not-seen-current-scan", "Source completed but did not return this known bid; existing bid retained."
    return "not-verified-current-scan", "Bid was not re-verified in this scan; existing bid retained."


def merge_sources(previous: dict, current: dict) -> list[dict]:
    output: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for record in (current, previous):
        for source in record.get("sources") or []:
            if not isinstance(source, dict):
                continue
            key = (str(source.get("id") or ""), str(source.get("url") or ""))
            if key in seen:
                continue
            seen.add(key)
            output.append(deepcopy(source))
    return output


def append_status_history(record: dict, *, status: str, at: str, reason: str) -> None:
    history = [deepcopy(item) for item in (record.get("statusHistory") or []) if isinstance(item, dict)]
    previous_status = str(history[-1].get("status") or "") if history else ""
    if previous_status != status:
        history.append({"status": status, "at": at, "reason": reason})
    record["statusHistory"] = history[-30:]


def initialize_current_record(record: dict, generated_at: str) -> dict:
    item = deepcopy(record)
    first_detected = str(item.get("firstDetectedAt") or item.get("firstSeenAt") or generated_at)
    item["firstDetectedAt"] = first_detected
    item["firstSeenAt"] = first_detected  # compatibility with the existing UI/data contract
    item["lastSeenAt"] = generated_at
    item["lastVerifiedAt"] = generated_at
    item["verificationStatus"] = "verified"
    item["verificationNote"] = "Observed in the current source scan."
    append_status_history(
        item,
        status=str(item.get("status") or "open"),
        at=generated_at,
        reason="discovered-and-verified",
    )
    return item


def merge_persistent_records(
    previous_records: list[dict],
    current_records: list[dict],
    source_metas: list[dict],
    *,
    now: datetime,
    generated_at: str,
) -> list[dict]:
    """Merge a fresh discovery scan into durable procurement history.

    The 90-day rule belongs to discovery. Once a record has been accepted into
    Bid Finder, omission from later scans cannot delete it. The stored deadline
    controls the open/closed transition; source health controls verification
    status only.
    """
    now_utc = now.astimezone(timezone.utc)
    previous_by_key = {
        canonical_key(item): deepcopy(item)
        for item in previous_records
        if isinstance(item, dict) and canonical_key(item)
    }
    current_by_key = {
        canonical_key(item): initialize_current_record(item, generated_at)
        for item in current_records
        if isinstance(item, dict) and canonical_key(item)
    }

    merged: dict[str, dict] = {}

    for key, current in current_by_key.items():
        previous = previous_by_key.get(key)
        if previous:
            current["firstDetectedAt"] = str(
                previous.get("firstDetectedAt")
                or previous.get("firstSeenAt")
                or current.get("firstDetectedAt")
                or generated_at
            )
            current["firstSeenAt"] = current["firstDetectedAt"]
            current["sources"] = merge_sources(previous, current)
            previous_deadline = str(previous.get("deadlineAt") or "")
            current_deadline = str(current.get("deadlineAt") or "")
            current["deadlineChanged"] = bool(previous_deadline and current_deadline and previous_deadline != current_deadline)
            current["statusHistory"] = [
                deepcopy(item) for item in (previous.get("statusHistory") or []) if isinstance(item, dict)
            ]
            append_status_history(
                current,
                status=str(current.get("status") or "open"),
                at=generated_at,
                reason="verified-status-change",
            )
        merged[key] = current

    for key, previous in previous_by_key.items():
        if key in merged:
            continue

        retained = deepcopy(previous)
        first_detected = str(retained.get("firstDetectedAt") or retained.get("firstSeenAt") or generated_at)
        retained["firstDetectedAt"] = first_detected
        retained["firstSeenAt"] = first_detected
        retained.setdefault("lastSeenAt", first_detected)
        retained.setdefault("lastVerifiedAt", retained.get("lastSeenAt") or first_detected)

        deadline = parse_iso(retained.get("deadlineAt"))
        terminal = str(retained.get("status") or "").lower() in {"awarded", "cancelled"}
        if deadline is not None and deadline < now_utc and not terminal:
            retained["status"] = "closed"
            retained["isOpen"] = False
            retained["retentionStatus"] = "expired"
            append_status_history(
                retained,
                status="closed",
                at=generated_at,
                reason="deadline-passed",
            )
        elif not terminal:
            retained["status"] = "open" if str(retained.get("status") or "open").lower() != "planned" else "planned"
            retained["isOpen"] = True
            retained["retentionStatus"] = "active-retained"

        verification_status, note = verification_status_for_missing(retained, source_metas)
        retained["verificationStatus"] = verification_status
        retained["verificationNote"] = note
        retained["retainedFromPreviousSnapshot"] = True
        merged[key] = retained

    return list(merged.values())
