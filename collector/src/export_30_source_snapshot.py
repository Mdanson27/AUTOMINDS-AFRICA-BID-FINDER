from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from . import export_live_snapshot as live
from .sources.public_portals import PUBLIC_PORTAL_SOURCES, PUBLIC_SOURCE_TYPES


for source in PUBLIC_PORTAL_SOURCES:
    # A successful fetch that legitimately contains no currently-open Uganda
    # notices is a healthy zero, not a collector failure.
    source.allow_empty = True

BASE_SOURCES = tuple(live.SOURCES)
NETWORK_SOURCES = (*BASE_SOURCES, *PUBLIC_PORTAL_SOURCES)
ORIGINAL_SOURCE_TYPE = live.source_type


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
    result = live.main()
    _fold_procurement_plan_health_into_egp()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
