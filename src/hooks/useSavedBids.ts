"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { ensureNeonUser, eq, neonDelete, neonSelect, neonUpsert } from "@/lib/neonApi";
import { resolveSpecificBidTitle } from "@/lib/titleSpecificity";
import type { Bid } from "@/lib/types";
import {
  canonicalSavedBidKey,
  isBidSaved,
  parseSavedBidRecords,
  reconcileSavedRecords,
  saveBidRecord,
  type SavedBidRecord,
  unsaveBidRecord,
} from "@/lib/savedBidsState";

const SAVED_EVENT = "bidfinder:saved-bids-changed";
const STORAGE_PREFIX = "autominds-bidfinder:saved-bids:v3";
const COMPLETED_STATUSES = new Set(["closed", "evaluation", "awarded", "cancelled"]);

function storageKey(uid: string) {
  return `${STORAGE_PREFIX}:${uid}`;
}

function readSaved(uid: string): SavedBidRecord[] {
  if (typeof window === "undefined") return [];
  try {
    return parseSavedBidRecords(window.localStorage.getItem(storageKey(uid)));
  } catch {
    return [];
  }
}

function writeSaved(uid: string, records: SavedBidRecord[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey(uid), JSON.stringify(records));
  queueMicrotask(() => window.dispatchEvent(new CustomEvent(SAVED_EVENT, { detail: { uid } })));
}

function isActiveSavedSnapshot(bid: Bid) {
  if (bid.displayEligible === false || COMPLETED_STATUSES.has(bid.status)) return false;
  const deadline = new Date(bid.deadlineAt);
  if (Number.isNaN(deadline.getTime()) || deadline.getTime() <= Date.now()) return false;
  const published = bid.publishedAt ? new Date(bid.publishedAt) : null;
  if (published && !Number.isNaN(published.getTime()) && published > deadline) return false;
  return true;
}

function rowToSaved(row: Record<string, unknown>): SavedBidRecord | null {
  const snapshot = row.snapshot as Bid | undefined;
  if (!snapshot || typeof snapshot !== "object" || !snapshot.id) return null;
  const savedAt = String(row.saved_at || new Date().toISOString());
  return {
    key: canonicalSavedBidKey(snapshot),
    bidId: String(row.bid_id || snapshot.id),
    savedAt,
    updatedAt: String(row.updated_at || savedAt),
    snapshot,
  };
}

async function loadCloudSaved(uid: string) {
  const rows = await neonSelect<Record<string, unknown>>(
    "saved_bids",
    `select=bid_id,saved_at,updated_at,snapshot&owner_uid=${eq(uid)}&order=saved_at.desc&limit=1000`,
  );
  return rows.flatMap((row) => {
    const record = rowToSaved(row);
    return record ? [record] : [];
  });
}

async function persistCloudSaved(uid: string, record: SavedBidRecord) {
  await ensureNeonUser();
  await neonUpsert("saved_bids", {
    owner_uid: uid,
    bid_id: record.bidId,
    stage: "watching",
    notes: "",
    snapshot: record.snapshot,
    saved_at: record.savedAt,
    updated_at: record.updatedAt,
  }, "owner_uid,bid_id");
}

async function deleteCloudSaved(uid: string, bidId: string) {
  await neonDelete("saved_bids", `owner_uid=${eq(uid)}&bid_id=${eq(bidId)}`);
}

export function useSavedBids(currentBids: Bid[] = []) {
  const { user } = useAuth();
  const [records, setRecords] = useState<SavedBidRecord[]>([]);
  const [ready, setReady] = useState(false);

  const reloadLocal = useCallback(() => {
    if (!user) {
      setRecords([]);
      setReady(true);
      return;
    }
    setRecords(readSaved(user.uid));
    setReady(true);
  }, [user]);

  const reloadCloud = useCallback(async () => {
    if (!user) return;
    try {
      const cloud = await loadCloudSaved(user.uid);
      setRecords((previous) => {
        const byKey = new Map<string, SavedBidRecord>();
        for (const item of previous) byKey.set(item.key, item);
        for (const item of cloud) {
          const existing = byKey.get(item.key);
          if (!existing || item.updatedAt >= existing.updatedAt) byKey.set(item.key, item);
        }
        const merged = Array.from(byKey.values());
        writeSaved(user.uid, merged);
        return merged;
      });
    } catch {
      // Keep the local cache usable during a temporary Neon/network outage.
    }
  }, [user]);

  useEffect(() => {
    reloadLocal();
    if (!user) return;
    void reloadCloud();

    const onStorage = (event: StorageEvent) => {
      if (event.key === storageKey(user.uid)) reloadLocal();
    };
    const onSaved = (event: Event) => {
      const detail = (event as CustomEvent<{ uid?: string }>).detail;
      if (!detail?.uid || detail.uid === user.uid) reloadLocal();
    };
    const onFocus = () => void reloadCloud();

    window.addEventListener("storage", onStorage);
    window.addEventListener(SAVED_EVENT, onSaved);
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(SAVED_EVENT, onSaved);
      window.removeEventListener("focus", onFocus);
    };
  }, [reloadCloud, reloadLocal, user]);

  useEffect(() => {
    if (!user || !ready || !currentBids.length) return;
    setRecords((previous) => {
      const reconciled = reconcileSavedRecords(previous, currentBids);
      if (JSON.stringify(reconciled) === JSON.stringify(previous)) return previous;
      writeSaved(user.uid, reconciled);
      for (const record of reconciled) void persistCloudSaved(user.uid, record).catch(() => undefined);
      return reconciled;
    });
  }, [currentBids, ready, user]);

  const toggle = useCallback((bid: Bid) => {
    if (!user) return;
    setRecords((previous) => {
      const currentlySaved = isBidSaved(previous, bid);
      const existing = previous.find((record) => record.key === canonicalSavedBidKey(bid));
      const next = currentlySaved
        ? unsaveBidRecord(previous, bid)
        : saveBidRecord(previous, bid);
      writeSaved(user.uid, next);

      if (currentlySaved) {
        if (existing) void deleteCloudSaved(user.uid, existing.bidId).catch(() => undefined);
      } else {
        const added = next.find((record) => record.key === canonicalSavedBidKey(bid));
        if (added) void persistCloudSaved(user.uid, added).catch(() => undefined);
      }
      return next;
    });
  }, [user]);

  // Saved relationships stay in history, but expired/completed snapshots are
  // never surfaced as live Bid Finder opportunities.
  const savedBids = useMemo(() => records
    .slice()
    .sort((a, b) => b.savedAt.localeCompare(a.savedAt))
    .flatMap((record) => {
      if (!isActiveSavedSnapshot(record.snapshot)) return [];
      const title = resolveSpecificBidTitle(record.snapshot);
      return title ? [{ ...record.snapshot, title, titleSpecificity: "specific" as const, displayEligible: true }] : [];
    }), [records]);

  const savedIds = useMemo(() => new Set(records.map((record) => record.bidId)), [records]);
  const savedKeys = useMemo(() => new Set(records.map((record) => record.key)), [records]);
  const isSaved = useCallback((bid: Bid) => savedKeys.has(canonicalSavedBidKey(bid)), [savedKeys]);

  return { savedIds, savedBids, records, ready, isSaved, toggle };
}
