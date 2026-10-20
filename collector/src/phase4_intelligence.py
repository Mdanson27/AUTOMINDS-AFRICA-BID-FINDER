from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import re

from .models import NormalizedBid, SourceDocument, SourceRef
from .sources.egp_uganda import EGPUgandaSource


MAX_DETAIL_FETCHES = 140
MAX_WORKERS = 4


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def parse_iso(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def iso(value: datetime | None) -> str:
    if not value:
        return ""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def is_egp(record: dict) -> bool:
    for source in record.get("sources") or []:
        if not isinstance(source, dict):
            continue
        if clean(source.get("id")).lower() == "egp-uganda" or clean(source.get("name")).lower() == "egp uganda":
            return True
    return clean(record.get("canonicalSource")).lower() == "egp uganda"


def detail_url(record: dict) -> str:
    for source in record.get("sources") or []:
        if not isinstance(source, dict):
            continue
        name = clean(source.get("name")).lower()
        source_id = clean(source.get("id")).lower()
        url = clean(source.get("url"))
        if url and (name == "egp uganda" or source_id == "egp-uganda") and url.rstrip("/") != "https://egpuganda.go.ug/bid-notices":
            return url
    return ""


def _source_refs(record: dict) -> list[SourceRef]:
    output: list[SourceRef] = []
    fallback = datetime.now(timezone.utc)
    for source in record.get("sources") or []:
        if not isinstance(source, dict):
            continue
        url = clean(source.get("url"))
        name = clean(source.get("name"))
        if not url or not name:
            continue
        output.append(SourceRef(name=name, url=url, detected_at=parse_iso(source.get("detectedAt")) or fallback))
    return output


def _dummy_bid(record: dict) -> NormalizedBid | None:
    sources = _source_refs(record)
    if not sources:
        return None
    documents = []
    for item in record.get("documents") or []:
        if isinstance(item, dict) and clean(item.get("url")):
            documents.append(SourceDocument(title=clean(item.get("title")) or "Procurement document", url=clean(item.get("url")), kind=clean(item.get("kind"))))
    status = clean(record.get("status")).lower() or "open"
    if status not in {"planned", "open", "closed", "evaluation", "awarded", "cancelled"}:
        status = "open"
    return NormalizedBid(
        title=clean(record.get("title")) or "Procurement opportunity",
        organization=clean(record.get("organization")) or "Unknown procuring entity",
        reference_number=clean(record.get("referenceNumber")),
        description=clean(record.get("description")),
        category=clean(record.get("category")),
        procurement_type=clean(record.get("procurementType")),
        procurement_method=clean(record.get("procurementMethod")),
        source_stage=clean(record.get("sourceStage")),
        published_at=parse_iso(record.get("publishedAt")),
        deadline_at=parse_iso(record.get("deadlineAt")),
        deadline_precision="datetime" if re.search(r"T\d{2}:\d{2}:[0-5]\d", clean(record.get("deadlineAt"))) else "date" if record.get("deadlineAt") else "unknown",
        status=status,
        sources=sources,
        notice_type=clean(record.get("noticeType")),
        opening_at=parse_iso(record.get("openingAt")),
        application_url=clean(record.get("applicationUrl")) or None,
        source_metadata={clean(k): clean(v) for k, v in (record.get("sourceMetadata") or {}).items() if clean(k) and clean(v)},
        documents=documents,
    )


def _serialize_model(record: dict, enriched: NormalizedBid) -> dict:
    item = deepcopy(record)
    item["title"] = clean(enriched.title)[:320]
    item["organization"] = clean(enriched.organization)[:180]
    item["referenceNumber"] = clean(enriched.reference_number)[:140]
    item["description"] = clean(enriched.description)[:5000]
    item["category"] = clean(enriched.category)[:140]
    item["procurementMethod"] = clean(enriched.procurement_method)[:160]
    item["sourceStage"] = clean(enriched.source_stage)[:100]
    item["publishedAt"] = iso(enriched.published_at) or clean(item.get("publishedAt"))
    item["deadlineAt"] = iso(enriched.deadline_at) or clean(item.get("deadlineAt"))
    item["openingAt"] = iso(enriched.opening_at) or clean(item.get("openingAt"))
    item["noticeType"] = clean(enriched.notice_type)[:140]
    item["applicationUrl"] = str(enriched.application_url) if enriched.application_url else clean(item.get("applicationUrl"))
    item["documents"] = [
        {"title": clean(doc.title)[:180], "url": str(doc.url), "kind": clean(doc.kind)[:40]}
        for doc in enriched.documents
    ]
    item["sourceMetadata"] = {clean(k)[:140]: clean(v)[:700] for k, v in enriched.source_metadata.items() if clean(k) and clean(v)}
    item["contacts"] = [{"label": clean(x.label), "value": clean(x.value), "kind": x.kind} for x in enriched.contacts]
    item["bidders"] = [{
        "name": clean(x.name),
        "address": clean(x.address),
        "submissionAt": iso(x.submission_at),
        "amount": clean(x.amount),
        "currency": clean(x.currency),
        "rank": clean(x.rank),
        "status": clean(x.status),
        "evaluationStage": clean(x.evaluation_stage),
        "reasons": [clean(reason) for reason in x.reasons if clean(reason)],
    } for x in enriched.bidders]
    item["bidsReceived"] = enriched.bids_received
    item["openingParticipants"] = [{
        "name": clean(x.name),
        "address": clean(x.address),
        "position": clean(x.position),
        "departmentCompany": clean(x.department_company),
    } for x in enriched.opening_participants]
    item["openingCommittee"] = [clean(x) for x in enriched.opening_committee if clean(x)]
    item["amendments"] = [{
        "title": clean(x.title),
        "url": str(x.url) if x.url else "",
        "publishedAt": iso(x.published_at),
        "summary": clean(x.summary),
    } for x in enriched.amendments]
    item["lifecycleEvents"] = [{
        "stage": x.stage,
        "title": clean(x.title),
        "occurredAt": iso(x.occurred_at),
        "sourceUrl": str(x.source_url) if x.source_url else "",
        "details": {clean(k): clean(v) for k, v in x.details.items() if clean(k) and clean(v)},
    } for x in enriched.lifecycle_events]
    item["bestEvaluatedBidder"] = clean(enriched.best_evaluated_bidder)
    item["contractAmount"] = clean(enriched.contract_amount)
    item["contractCurrency"] = clean(enriched.contract_currency)

    intelligence = dict(item.get("intelligence") or {})
    if enriched.bid_security:
        intelligence["bidSecurity"] = clean(enriched.bid_security)
    if enriched.tender_fee:
        intelligence["tenderFee"] = clean(enriched.tender_fee)
    if enriched.submission_method:
        intelligence["submissionMethod"] = clean(enriched.submission_method)
    if enriched.mandatory_requirements:
        intelligence["mandatoryRequirements"] = [clean(x) for x in enriched.mandatory_requirements if clean(x)]
    if enriched.eligibility:
        intelligence["eligibility"] = [clean(x) for x in enriched.eligibility if clean(x)]
    evidence = sum(bool(intelligence.get(key)) for key in ("bidSecurity", "tenderFee", "submissionMethod", "mandatoryRequirements", "eligibility"))
    if item.get("bidders") or item.get("contacts") or item.get("documents"):
        evidence += 1
    intelligence["enrichmentStatus"] = "enriched" if evidence >= 4 else "partial" if evidence else intelligence.get("enrichmentStatus", "basic")
    intelligence["confidence"] = "high" if evidence >= 4 else "medium" if evidence else intelligence.get("confidence", "low")
    item["intelligence"] = intelligence
    item["phase4Enriched"] = True
    return item


def _merge_unique(existing: list, incoming: list, key_fn) -> list:
    output = [deepcopy(item) for item in existing if isinstance(item, dict)]
    seen = {key_fn(item) for item in output}
    for item in incoming:
        if not isinstance(item, dict):
            continue
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key)
        output.append(deepcopy(item))
    return output


def _append_status_history(item: dict, status: str, at: str, reason: str) -> None:
    history = [deepcopy(entry) for entry in (item.get("statusHistory") or []) if isinstance(entry, dict)]
    previous = clean(history[-1].get("status")).lower() if history else ""
    if previous != status:
        history.append({"status": status, "at": at, "reason": reason})
    item["statusHistory"] = history[-30:]


def _append_lifecycle_source(item: dict, lifecycle: dict) -> None:
    events = [event for event in (lifecycle.get("lifecycleEvents") or []) if isinstance(event, dict)]
    for event in events:
        url = clean(event.get("sourceUrl"))
        if not url:
            continue
        detected_at = clean(event.get("occurredAt")) or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        sources = [deepcopy(source) for source in (item.get("sources") or []) if isinstance(source, dict)]
        if any(clean(source.get("url")) == url for source in sources):
            continue
        sources.append({"id": "egp-uganda", "name": "eGP Uganda", "url": url, "detectedAt": detected_at})
        item["sources"] = sources


def _overlay_lifecycle(record: dict, lifecycle: dict) -> dict:
    item = deepcopy(record)
    if clean(lifecycle.get("title")):
        item["title"] = clean(lifecycle["title"])[:320]
    if clean(lifecycle.get("procurementMethod")):
        item["procurementMethod"] = clean(lifecycle["procurementMethod"])[:160]
    for field in ("sourceStage", "bestEvaluatedBidder", "contractAmount", "contractCurrency"):
        if clean(lifecycle.get(field)):
            item[field] = clean(lifecycle[field])

    stage_status = clean(lifecycle.get("status")).lower()
    lifecycle_events = [event for event in (lifecycle.get("lifecycleEvents") or []) if isinstance(event, dict)]
    event_at = next((clean(event.get("occurredAt")) for event in lifecycle_events if clean(event.get("occurredAt"))), "")
    if not event_at:
        event_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if stage_status in {"evaluation", "awarded", "cancelled"}:
        previous_status = clean(item.get("status")).lower()
        item["status"] = stage_status
        item["isOpen"] = False
        if previous_status != stage_status:
            _append_status_history(item, stage_status, event_at, f"egp-lifecycle-{stage_status}")

    item["bidders"] = _merge_unique(
        item.get("bidders") or [],
        lifecycle.get("bidders") or [],
        lambda x: (clean(x.get("name")).lower(), clean(x.get("amount")), clean(x.get("submissionAt"))),
    )
    item["lifecycleEvents"] = _merge_unique(
        item.get("lifecycleEvents") or [],
        lifecycle_events,
        lambda x: (clean(x.get("stage")), clean(x.get("title")).lower(), clean(x.get("occurredAt")), clean(x.get("sourceUrl"))),
    )
    _append_lifecycle_source(item, lifecycle)
    metadata = dict(item.get("sourceMetadata") or {})
    metadata.update({clean(k): clean(v) for k, v in (lifecycle.get("sourceMetadata") or {}).items() if clean(k) and clean(v)})
    item["sourceMetadata"] = metadata
    item["phase4Enriched"] = True
    return item


def apply_phase4_intelligence(records: list[dict]) -> list[dict]:
    """Deep-enrich persisted eGP records and attach lifecycle events.

    Detail requests are bounded and concurrent so production deploys remain
    predictable. Public eGP pages are used only; failures retain prior data.
    """
    source = EGPUgandaSource()
    output = [deepcopy(item) for item in records]
    candidates: list[tuple[int, int, str]] = []
    for index, record in enumerate(output):
        if not is_egp(record):
            continue
        url = detail_url(record)
        if not url:
            continue
        stage = clean(record.get("sourceStage")).lower()
        status = clean(record.get("status")).lower()
        priority = 0 if "opening" in stage or "/opening/details" in url else 1 if status in {"open", "evaluation"} else 2
        candidates.append((priority, index, url))
    candidates.sort(key=lambda item: item[0])
    candidates = candidates[:MAX_DETAIL_FETCHES]

    def fetch_and_parse(index: int, url: str):
        record = output[index]
        dummy = _dummy_bid(record)
        if dummy is None:
            return index, None
        raw = source._fetch_url(url)
        return index, source.parse_detail(raw, dummy, url)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_and_parse, index, url): index for _, index, url in candidates}
        for future in as_completed(futures):
            index = futures[future]
            try:
                _, enriched = future.result()
            except Exception:
                continue
            if enriched is not None:
                output[index] = _serialize_model(output[index], enriched)

    try:
        lifecycle_records = source.collect_lifecycle_records()
    except Exception:
        lifecycle_records = []

    by_reference: dict[str, list[int]] = {}
    for index, record in enumerate(output):
        reference = re.sub(r"\s+", "", clean(record.get("referenceNumber")).lower())
        if reference:
            by_reference.setdefault(reference, []).append(index)

    for lifecycle in lifecycle_records:
        reference = re.sub(r"\s+", "", clean(lifecycle.get("referenceNumber")).lower())
        if not reference:
            continue
        for index in by_reference.get(reference, []):
            output[index] = _overlay_lifecycle(output[index], lifecycle)

    return output
