# Phase 4 — Heavy eGP Extraction + Procurement Lifecycle Intelligence

This phase turns the bid detail experience into a structured procurement intelligence record.

Implemented extraction coverage:

- Exact subject of procurement and reference
- Procurement method, notice type and category
- Publication, deadline and exact-time extraction when eGP publishes a time
- Scope / description
- Eligibility and mandatory requirement signals
- Bid security and tender/document fees
- Submission method
- Addresses, emails and phone contacts
- Public procurement documents and application links
- Bid-opening date/time and bids received
- Structured bidder names, addresses, submission dates and amounts
- Public opening attendance / committee information when published
- Amendments / addenda links
- Best Evaluated Bidder records
- Contract/evaluated amount fields
- Lifecycle events: Advertised → Updated/Addendum → Closed → Bid Opening → Evaluation/BEB → Contract Award

## Persistence and lifecycle linking

Lifecycle overlays are matched back to persisted procurements by the public procurement reference number. This is performed after Phase 2 persistence merging, so a retained or already-closed procurement can still gain opening, BEB or award intelligence later.

No missing procurement fact is invented. If eGP has not published a value, Bid Finder leaves it blank / not published.

## Production safeguards

- Only public unauthenticated eGP pages are fetched.
- No login, CAPTCHA or access-control bypass is used.
- Detail-page enrichment is bounded and uses a small worker pool to keep deployments predictable.
- Fetch failures preserve previously collected procurement intelligence instead of deleting it.
- A dedicated Phase 4 test workflow validates heavy notice extraction and BEB lifecycle parsing.
