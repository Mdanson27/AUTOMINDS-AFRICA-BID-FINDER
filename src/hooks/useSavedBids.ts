"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
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
const STORAGE_PREFIX = "autominds-bidfinder:saved-bids:v2";

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

export function useSavedBids(currentBids: Bid[] = []) {
  const { user } = useAuth();
  const [records, setRecords] = useState<SavedBidRecord[]>([]);
  const [ready, setReady] = useState(false);

  const reload = useCallback(() => {
    if (!user) {
      setRecords([]);
      setReady(true);
      return;
    }
    setRecords(readSaved(user.uid));
    setReady(true);
  }, [user]);

  useEffect(() => {
    reload();
    if (!user) return;

    const onStorage = (event: StorageEvent) => {
      if (event.key === storageKey(user.uid)) reload();
    };
    const onSaved = (event: Event) => {
      const detail = (event as CustomEvent<{ uid?: string }>).detail;
      if (!detail?.uid || detail.uid === user.uid) reload();
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener(SAVED_EVENT, onSaved);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(SAVED_EVENT, onSaved);
    };
  }, [reload, user]);

  useEffect(() => {
    if (!user || !ready || !currentBids.length) return;
    setRecords((previous) => {
      const reconciled = reconcileSavedRecords(previous, currentBids);
      if (JSON.stringify(reconciled) === JSON.stringify(previous)) return previous;
      writeSaved(user.uid, reconciled);
      return reconciled;
    });
  }, [currentBids, ready, user]);

  const toggle = useCallback((bid: Bid) => {
    if (!user) return;
    setRecords((previous) => {
      const next = isBidSaved(previous, bid)
        ? unsaveBidRecord(previous, bid)
        : saveBidRecord(previous, bid);
      writeSaved(user.uid, next);
      return next;
    });
  }, [user]);

  // The save relationship remains stored even when an older snapshot only has
  // a generic procurement method. Such records are simply withheld from the
  // visible saved-bids list until a source-supported specific title is recovered.
  const savedBids = useMemo(() => records
    .slice()
    .sort((a, b) => b.savedAt.localeCompare(a.savedAt))
    .flatMap((record) => {
      const title = resolveSpecificBidTitle(record.snapshot);
      return title ? [{ ...record.snapshot, title, titleSpecificity: "specific" as const, displayEligible: true }] : [];
    }), [records]);

  const savedIds = useMemo(() => new Set(records.map((record) => record.bidId)), [records]);
  const savedKeys = useMemo(() => new Set(records.map((record) => record.key)), [records]);
  const isSaved = useCallback((bid: Bid) => savedKeys.has(canonicalSavedBidKey(bid)), [savedKeys]);

  return { savedIds, savedBids, records, ready, isSaved, toggle };
}
