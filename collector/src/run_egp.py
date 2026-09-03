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
    run_ref, _ = store.start_run()
    stats = IngestionStats()

    try:
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
        store.finish_run(run_ref, stats, error=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
