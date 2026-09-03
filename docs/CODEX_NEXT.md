# Next Codex pass

Do not redesign the application foundation. Continue from the existing architecture.

Priority order:
1. Inspect the live eGP Uganda public bid-notices implementation and complete `collector/src/sources/egp_uganda.py` with robust selectors/API use.
2. Add Firestore Admin sink, idempotent upsert, exact-reference dedupe and normalized fingerprint fallback.
3. Write `crawlRuns` and `sources` health metrics.
4. Add GPP/PPDA adapter.
5. Add Daily Monitor adapter.
6. Add New Vision adapter.
7. Add deadline/status change detection and `bids/{id}/changes` writes.
8. Add scheduled execution suitable for Cloud Run / GitHub Actions during testing.
9. Add automated tests with saved HTML fixtures; never test production scraping by hammering source sites.
10. Only after multi-source ingestion is stable, add AI extraction and company-to-bid matching.

The dashboard must display real ingested procurement data, never invented filler bids.
