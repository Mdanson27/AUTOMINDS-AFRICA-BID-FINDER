from __future__ import annotations

from datetime import datetime, timedelta
import logging
import sys
from zoneinfo import ZoneInfo

from .firestore_store import FirestoreBidStore, IngestionStats
from .sources.egp_uganda import EGPUgandaSource


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("autominds.egp")
KAMPALA = ZoneInfo("Africa/Kampala")
MAX_DAYS_AHEAD = 90
TERMINAL_STATUSES = {"closed", "evaluation", "awarded", "cancelled"}


def _display_candidate(bid, now: datetime) -> tuple[bool, str]:
    """Fail closed when an eGP record cannot safely be offered as a live bid."""
    deadline = bid.deadline_at
    if deadline is None:
        return False, "missing-deadline"

    deadline = deadline.astimezone(KAMPALA)
    if deadline <= now:
        return False, "deadline-passed"
    if deadline > now + timedelta(days=MAX_DAYS_AHEAD):
        return False, "deadline-outside-live-window"
    if str(bid.status or "").lower() in TERMINAL_STATUSES:
        return False, f"terminal-status:{bid.status}"

    if bid.published_at is not None:
        published = bid.published_at.astimezone(KAMPALA)
        if published > deadline:
            return False, "publication-after-deadline"
        if published > now + timedelta(days=1):
            return False, "publication-date-in-future"

    return True, "verified-active"


def main() -> int:
    source = EGPUgandaSource()
    store = FirestoreBidStore(source.source_id, source.name, source.url)
    stats = IngestionStats()
    run_ref = None

    try:
        # Prove the public source is reachable and parsable independently of the
        # database. This keeps source failures distinct from storage failures.
        log.info("Fetching public eGP Uganda bid notices")
        raw = source.fetch()
        parsed_bids = list(source.parse(raw))
        if not parsed_bids:
            raise RuntimeError("eGP parser returned zero standard bid notices; refusing to write an empty crawl")

        now = datetime.now(KAMPALA)
        bids = []
        rejected = 0
        deadline_updates = 0

        # The list page is discovery only. Before a record is written to the live
        # application collection, fetch its detail page so an authoritative
        # submission deadline can replace a stale/list-only date when available.
        for bid in parsed_bids:
            precheck, precheck_reason = _display_candidate(bid, now)
            if not precheck:
                rejected += 1
                log.info("Withholding %s before enrichment: %s", bid.reference_number or bid.title, precheck_reason)
                continue

            discovered_deadline = bid.deadline_at
            try:
                enriched = source.enrich(bid)
            except Exception as exc:  # noqa: BLE001 - keep the authoritative list fallback available
                log.warning("Detail validation failed for %s: %s", bid.reference_number or bid.title, exc)
                enriched = bid

            if discovered_deadline and enriched.deadline_at and discovered_deadline != enriched.deadline_at:
                deadline_updates += 1
                log.info(
                    "Authoritative deadline update %s: %s -> %s",
                    bid.reference_number or bid.title,
                    discovered_deadline.isoformat(),
                    enriched.deadline_at.isoformat(),
                )

            eligible, reason = _display_candidate(enriched, now)
            if not eligible:
                rejected += 1
                log.warning("Withholding %s after detail validation: %s", enriched.reference_number or enriched.title, reason)
                continue
            bids.append(enriched)

        if not bids:
            raise RuntimeError("eGP validation produced zero active bids; refusing to write an empty live crawl")

        log.info(
            "Parsed %s eGP notices; validated %s active bids; withheld %s; corrected %s deadlines",
            len(parsed_bids),
            len(bids),
            rejected,
            deadline_updates,
        )
        for index, bid in enumerate(bids[:3], start=1):
            log.info(
                "Validated eGP sample %s: reference=%s organization=%s deadline=%s title=%s",
                index,
                bid.reference_number or "(none)",
                bid.organization,
                bid.deadline_at.isoformat() if bid.deadline_at else "unknown",
                bid.title,
            )

        run_ref, _ = store.start_run()
        stats = store.ingest(bids)
        store.finish_run(run_ref, stats)
        log.info(
            "eGP ingestion complete: found=%s created=%s updated=%s unchanged=%s",
            stats.found,
            stats.created,
            stats.updated,
            stats.unchanged,
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - ingestion boundary must persist failure state
        log.exception("eGP ingestion failed")
        if run_ref is not None:
            try:
                store.finish_run(run_ref, stats, error=str(exc))
            except Exception:  # noqa: BLE001 - preserve the primary source/storage error
                log.exception("Could not persist failed eGP crawl status")
        return 1


if __name__ == "__main__":
    sys.exit(main())
