# Architecture

```text
Public Uganda sources
        ↓
Collector adapters (isolated Python workspace)
        ↓
Fetch → Parse → Normalize → Deduplicate → Change detection
        ↓
Firestore (MVP/testing)
        ↓
Next.js live subscriptions
        ↓
Dashboard / search / saved bids / source monitor
```

## Firestore collections

- `users` — Firebase Auth profile + application role
- `bids` — one normalized opportunity record
- `bids/{id}/sources` — source evidence (future collector writes)
- `bids/{id}/changes` — field-level change history
- `sources` — source registry and health
- `crawlRuns` — ingestion observability
- `savedBids` — user watchlists
- `organizations` — normalized procuring entities
- `companyProfiles` — future matching profiles

The MVP UI also accepts a `sources` summary array on each bid to keep initial reads inexpensive. The collector can keep that summary synchronized while also preserving full source evidence in the subcollection.

## Migration path
Firestore is intentionally behind a small data-access layer. When volume requires it, the collector and app can move to PostgreSQL/AWS without redesigning the UI or the normalized bid contract.
