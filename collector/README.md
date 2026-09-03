# Collector workspace

This directory is intentionally isolated from the Next.js UI.

The production collector will:
1. fetch public bid sources,
2. normalize every source into the common `NormalizedBid` contract,
3. deduplicate by procurement reference and fingerprint,
4. compare changes against Firestore,
5. write source health and crawl-run metrics.

Start with `EGPUgandaSource`, then GPP/PPDA, Daily Monitor and New Vision.
Never bypass authentication, CAPTCHAs, paywalls or access controls.
