from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from pathlib import Path
import time

from . import export_live_snapshot as live
from .sources.public_portals import PUBLIC_PORTAL_SOURCES, PUBLIC_SOURCE_TYPES


for source in PUBLIC_PORTAL_SOURCES:
    # A successful fetch that legitimately contains no currently-open Uganda
    # notices is a healthy zero, not a collector failure.
    source.allow_empty = True

BASE_SOURCES = tuple(live.SOURCES)
NETWORK_SOURCES = (*BASE_SOURCES, *PUBLIC_PORTAL_SOURCES)
ORIGINAL_SOURCE_TYPE = live.source_type
ORIGINAL_COLLECT_ONE_SOURCE = live.collect_one_source
MAX_SOURCE_WORKERS = 6
CORE_RETRY_SOURCES = {"egp-uganda", "gpp-ppda"}


def _network_source_type(source_id: str) -> str:
    return PUBLIC_SOURCE_TYPES.get(source_id, ORIGINAL_SOURCE_TYPE(source_id))


def _financial_year_start(now: datetime) -> datetime:
    local_now = now.astimezone(live.KAMPALA)
    year = local_now.year if local_now.month >= 7 else local_now.year - 1
    start = datetime(year, 7, 1, tzinfo=live.KAMPALA)
    return max(start, live.MIN_FINANCIAL_YEAR_START)


def validate_network() -> None:
    ids = [source.source_id for source in NETWORK_SOURCES]
    if len(ids) != 30:
        raise RuntimeError(f"Bid Finder source network must contain exactly 30 sources; found {len(ids)}")
    if len(set(ids)) != len(ids):
        duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
        raise RuntimeError(f"Duplicate Bid Finder source ids: {', '.join(duplicates)}")


def _precollect_sources(now: datetime):
    """Fetch/parse independent publishers concurrently.

    `export_live_snapshot.main()` still performs the canonical validation,
    enrichment, source health accounting and deterministic merge. We only
    parallelize slow independent network I/O here, then feed cached results
    back into that proven pipeline. Core Uganda portals get one retry before
    being marked unavailable because transient eGP/GPP timeouts should not
    erase their opportunities from a scan.
    """
    cache: dict[str, list] = {}
    failures: dict[str, Exception] = {}

    def collect(source):
        attempts = 2 if source.source_id in CORE_RETRY_SOURCES else 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                return list(ORIGINAL_COLLECT_ONE_SOURCE(source, now))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt + 1 < attempts:
                    print(f"Retrying {source.name} after transient collection failure: {exc}")
                    time.sleep(1.0)
        assert last_error is not None
        raise last_error

    with ThreadPoolExecutor(max_workers=MAX_SOURCE_WORKERS, thread_name_prefix="bid-source") as executor:
        futures = {executor.submit(collect, source): source for source in NETWORK_SOURCES}
        for future in as_completed(futures):
            source = futures[future]
            try:
                cache[source.source_id] = future.result()
                print(f"Prefetched {source.name}: {len(cache[source.source_id])} parsed notices")
            except Exception as exc:  # noqa: BLE001
                failures[source.source_id] = exc
                print(f"Prefetch warning {source.name}: {exc}")

    def cached_collect(source, _now):
        failure = failures.get(source.source_id)
        if failure is not None:
            raise failure
        return list(cache.get(source.source_id, []))

    return cached_collect


def _fold_procurement_plan_health_into_egp() -> None:
    """Keep procurement plans as eGP intelligence, not a 31st bid source."""
    path = Path(live.DATA_DIR) / "sources.json"
    if not path.exists():
        return
    sources = json.loads(path.read_text(encoding="utf-8"))
    plan_meta = next((item for item in sources if item.get("id") == "egp-procurement-plans"), None)
    filtered = [item for item in sources if item.get("id") != "egp-procurement-plans"]
    if plan_meta:
        egp = next((item for item in filtered if item.get("id") == "egp-uganda"), None)
        if egp is not None:
            egp["procurementPlansHealth"] = plan_meta.get("health", "warning")
            egp["procurementPlansFound"] = plan_meta.get("recordsFound", 0)
            egp["procurementPlansLastCheckedAt"] = plan_meta.get("lastAttemptedCrawlAt", "")
            if plan_meta.get("lastError"):
                egp["procurementPlansError"] = plan_meta.get("lastError")
    path.write_text(json.dumps(filtered, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    validate_network()
    live.SOURCES = NETWORK_SOURCES
    live.source_type = _network_source_type
    # Preserve the correct July-June Uganda financial-year boundary in the
    # expanded exporter and all eligibility checks it calls.
    live.financial_year_start = _financial_year_start

    print("Bid Finder 30-source network enabled:")
    for index, source in enumerate(NETWORK_SOURCES, start=1):
        print(f"  {index:02d}. {source.name} [{source.source_id}]")

    # Parallelize only source fetch/parse. Validation/enrichment/merge remains
    # centralized and deterministic inside the mature exporter.
    prefetch_now = datetime.now(live.KAMPALA)
    live.collect_one_source = _precollect_sources(prefetch_now)
    try:
        result = live.main()
    finally:
        live.collect_one_source = ORIGINAL_COLLECT_ONE_SOURCE

    _fold_procurement_plan_health_into_egp()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
