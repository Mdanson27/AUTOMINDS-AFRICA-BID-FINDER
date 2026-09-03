from __future__ import annotations

import logging
import sys

from .firestore_store import FirestoreBidStore, IngestionStats
from .sources.egp_uganda import EGPUgandaSource


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("autominds.egp")


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
        bids = list(source.parse(raw))
        if not bids:
            raise RuntimeError("eGP parser returned zero standard bid notices; refusing to write an empty crawl")

        log.info("Parsed %s normalized bid notices", len(bids))
        for index, bid in enumerate(bids[:3], start=1):
            log.info(
                "Live eGP sample %s: reference=%s organization=%s deadline=%s title=%s",
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
