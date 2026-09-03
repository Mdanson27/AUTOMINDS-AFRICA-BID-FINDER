"use client";

import { useEffect, useState } from "react";
import { subscribeToBids } from "@/lib/firestore";
import type { Bid, BidStatus } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const MAX_DAYS_AHEAD = 90;
const MIN_FY_START = new Date("2026-07-01T00:00:00+03:00").getTime();
export const SNAPSHOT_REFRESH_EVENT = "bidfinder:refresh-snapshot";

function plainText(value: string) {
  if (!value) return "";
  let text = value;
  const parser = new DOMParser();
  for (let pass = 0; pass < 2; pass += 1) {
    const doc = parser.parseFromString(text, "text/html");
    text = doc.body.textContent || text;
  }
  return text.replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
}

function currentFinancialYearStart(now: Date) {
  const year = now.getUTCMonth() >= 6 ? now.getUTCFullYear() : now.getUTCFullYear() - 1;
  return Math.max(new Date(`${year}-07-01T00:00:00+03:00`).getTime(), MIN_FY_START);
}

function normalizeBid(bid: Bid, now = new Date()): Bid | null {
  const deadline = new Date(bid.deadlineAt);
  if (Number.isNaN(deadline.getTime())) return null;

  const nowMs = now.getTime();
  const fyStart = currentFinancialYearStart(now);
  const latestDeadline = nowMs + MAX_DAYS_AHEAD * 86_400_000;
  const deadlineMs = deadline.getTime();

  if (deadlineMs < fyStart || deadlineMs > latestDeadline) return null;

  if (bid.publishedAt) {
    const published = new Date(bid.publishedAt);
    if (!Number.isNaN(published.getTime()) && published.getTime() < fyStart) return null;
  }

  const title = plainText(bid.title).slice(0, 320);
  if (!title) return null;

  const isOpen = deadlineMs >= nowMs;
  const status: BidStatus = isOpen && bid.status === "planned" ? "planned" : isOpen ? "open" : "closed";

  return {
    ...bid,
    title,
    organization: plainText(bid.organization).slice(0, 180),
    referenceNumber: plainText(bid.referenceNumber).slice(0, 140),
    description: plainText(bid.description).slice(0, 2400),
    category: plainText(bid.category).slice(0, 120),
    procurementType: plainText(bid.procurementType).slice(0, 100),
    status,
    isOpen,
    sources: (bid.sources || []).map((source) => ({ ...source, name: plainText(source.name) })),
  };
}

function mergeBids(snapshotBids: Bid[], liveBids: Bid[]) {
  const merged = new Map<string, Bid>();
  const now = new Date();
  for (const raw of [...snapshotBids, ...liveBids]) {
    const bid = normalizeBid(raw, now);
    if (bid) merged.set(bid.id, bid);
  }
  return Array.from(merged.values());
}

export function requestSnapshotRefresh() {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(SNAPSHOT_REFRESH_EVENT));
}

export function useBids() {
  const [bids, setBids] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let snapshotBids: Bid[] = [];
    let liveBids: Bid[] = [];

    const publish = () => {
      if (!active) return;
      const merged = mergeBids(snapshotBids, liveBids);
      setBids(merged);
      if (merged.length) setError("");
      setLoading(false);
    };

    const loadSnapshot = async () => {
      const bust = Date.now();
      try {
        const response = await fetch(`${basePath}/data/bids.json?v=${bust}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Snapshot request failed: ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error("Invalid opportunity snapshot");
        snapshotBids = data as Bid[];
        publish();
      } catch {
        try {
          const response = await fetch(`${basePath}/data/egp-bids.json?v=${bust}`, { cache: "no-store" });
          if (!response.ok) throw new Error(`Fallback snapshot request failed: ${response.status}`);
          const data = await response.json();
          if (!Array.isArray(data)) throw new Error("Invalid fallback opportunity snapshot");
          snapshotBids = data as Bid[];
          publish();
        } catch {
          if (liveBids.length) publish();
        }
      }
    };

    void loadSnapshot();
    window.addEventListener(SNAPSHOT_REFRESH_EVENT, loadSnapshot);

    const unsubscribe = subscribeToBids(
      (items) => {
        liveBids = items;
        publish();
      },
      (reason) => {
        if (!snapshotBids.length && active) {
          setError(reason);
          setLoading(false);
        }
      },
    );

    return () => {
      active = false;
      window.removeEventListener(SNAPSHOT_REFRESH_EVENT, loadSnapshot);
      unsubscribe();
    };
  }, []);

  return { bids, loading, error };
}
