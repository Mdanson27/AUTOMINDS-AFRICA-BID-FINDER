import test from "node:test";
import assert from "node:assert/strict";
import {
  canonicalSavedBidKey,
  isBidSaved,
  parseSavedBidRecords,
  reconcileSavedRecords,
  saveBidRecord,
  unsaveBidRecord,
} from "../src/lib/savedBidsState.ts";
import type { Bid } from "../src/lib/types.ts";

function bid(overrides: Partial<Bid> = {}): Bid {
  return {
    id: "bid-v1",
    title: "Procurement of Enterprise Systems Cybersecurity Audit Tools",
    organization: "Kampala Capital City Authority",
    referenceNumber: "KCCA/NCONS/2026-2027/00255",
    description: "Cybersecurity audit tools",
    category: "Non-consultancy services",
    procurementType: "Non Consulting Services",
    procurementMethod: "Request For Quotations/Proposals",
    canonicalIdentity: "kcca|KCCA/NCONS/2026-2027/00255",
    canonicalSource: "eGP Uganda",
    publishedAt: "2026-10-01T08:00:00Z",
    deadlineAt: "2026-10-31T08:00:00Z",
    status: "open",
    isOpen: true,
    fingerprint: "fingerprint-v1",
    firstSeenAt: "2026-10-01T08:00:00Z",
    lastSeenAt: "2026-10-20T08:00:00Z",
    sources: [{ name: "eGP Uganda", url: "https://egpuganda.go.ug/example" }],
    ...overrides,
  };
}

test("save is immediate and a serialized reload preserves the relationship", () => {
  const original = bid();
  const saved = saveBidRecord([], original, "2026-10-20T09:00:00Z");
  assert.equal(saved.length, 1);
  assert.equal(isBidSaved(saved, original), true);

  const reloaded = parseSavedBidRecords(JSON.stringify(saved));
  assert.equal(reloaded.length, 1);
  assert.equal(isBidSaved(reloaded, original), true);
  assert.equal(reloaded[0].snapshot.title, original.title);
});

test("enrichment updates the same saved record instead of duplicating it", () => {
  const original = bid();
  const saved = saveBidRecord([], original, "2026-10-20T09:00:00Z");
  const enriched = bid({
    id: "bid-v2",
    title: "Procurement of Enterprise Systems Cybersecurity Audit Tools - Lot 1",
    description: "Deeply enriched public notice",
    deadlineAt: "2026-11-07T08:00:00Z",
    deadlineChanged: true,
  });

  const reconciled = reconcileSavedRecords(saved, [enriched], "2026-10-21T09:00:00Z");
  assert.equal(reconciled.length, 1);
  assert.equal(reconciled[0].bidId, "bid-v2");
  assert.equal(reconciled[0].snapshot.description, "Deeply enriched public notice");
  assert.equal(reconciled[0].savedAt, "2026-10-20T09:00:00Z");
});

test("source failure does not remove a saved bid", () => {
  const original = bid();
  const saved = saveBidRecord([], original, "2026-10-20T09:00:00Z");
  const reconciled = reconcileSavedRecords(saved, [], "2026-10-21T09:00:00Z");
  assert.deepEqual(reconciled, saved);
});

test("a closed bid stays saved", () => {
  const original = bid();
  const saved = saveBidRecord([], original, "2026-10-20T09:00:00Z");
  const closed = bid({
    id: "bid-v3",
    status: "closed",
    isOpen: false,
    deadlineAt: "2026-10-19T08:00:00Z",
  });

  const reconciled = reconcileSavedRecords(saved, [closed], "2026-10-21T09:00:00Z");
  assert.equal(reconciled.length, 1);
  assert.equal(reconciled[0].snapshot.status, "closed");
  assert.equal(isBidSaved(reconciled, closed), true);
});

test("unsave is the only operation that removes the relationship", () => {
  const original = bid();
  const saved = saveBidRecord([], original, "2026-10-20T09:00:00Z");
  const removed = unsaveBidRecord(saved, original);
  assert.equal(removed.length, 0);
  assert.equal(isBidSaved(removed, original), false);
});

test("canonical identity, not volatile bid id, defines saved identity", () => {
  const first = bid({ id: "temporary-1" });
  const second = bid({ id: "temporary-2", title: "Improved procurement title" });
  assert.equal(canonicalSavedBidKey(first), canonicalSavedBidKey(second));
});
