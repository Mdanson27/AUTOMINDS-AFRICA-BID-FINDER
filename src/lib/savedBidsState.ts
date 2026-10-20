import type { Bid } from "./types";

export type SavedBidRecord = {
  key: string;
  bidId: string;
  savedAt: string;
  updatedAt: string;
  snapshot: Bid;
};

function normalize(value: string | undefined) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 240);
}

export function canonicalSavedBidKey(bid: Bid): string {
  if (bid.canonicalIdentity) return `canonical:${normalize(bid.canonicalIdentity)}`;
  if (bid.fingerprint) return `fingerprint:${normalize(bid.fingerprint)}`;
  const organization = normalize(bid.organization);
  const reference = normalize(bid.referenceNumber);
  const source = normalize(bid.canonicalSource || bid.sources?.[0]?.name);
  if (organization && reference) return `procurement:${organization}:${reference}:${source}`;
  return `bid:${normalize(bid.id)}`;
}

export function reconcileSavedRecords(records: SavedBidRecord[], currentBids: Bid[], nowIso = new Date().toISOString()): SavedBidRecord[] {
  const currentByKey = new Map(currentBids.map((bid) => [canonicalSavedBidKey(bid), bid]));
  return records.map((record) => {
    const current = currentByKey.get(record.key);
    if (!current) return record;
    if (record.bidId === current.id && JSON.stringify(record.snapshot) === JSON.stringify(current)) return record;
    return {
      ...record,
      bidId: current.id,
      updatedAt: nowIso,
      snapshot: current,
    };
  });
}

export function saveBidRecord(records: SavedBidRecord[], bid: Bid, nowIso = new Date().toISOString()): SavedBidRecord[] {
  const key = canonicalSavedBidKey(bid);
  const existing = records.find((record) => record.key === key);
  const next: SavedBidRecord = {
    key,
    bidId: bid.id,
    savedAt: existing?.savedAt || nowIso,
    updatedAt: nowIso,
    snapshot: bid,
  };
  return [...records.filter((record) => record.key !== key), next];
}

export function unsaveBidRecord(records: SavedBidRecord[], bid: Bid): SavedBidRecord[] {
  const key = canonicalSavedBidKey(bid);
  return records.filter((record) => record.key !== key);
}

export function isBidSaved(records: SavedBidRecord[], bid: Bid): boolean {
  const key = canonicalSavedBidKey(bid);
  return records.some((record) => record.key === key);
}

export function parseSavedBidRecords(raw: string | null): SavedBidRecord[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is SavedBidRecord => Boolean(
      item &&
      typeof item === "object" &&
      typeof item.key === "string" &&
      typeof item.bidId === "string" &&
      typeof item.savedAt === "string" &&
      item.snapshot &&
      typeof item.snapshot === "object" &&
      typeof item.snapshot.id === "string",
    ));
  } catch {
    return [];
  }
}
