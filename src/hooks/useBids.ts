"use client";

import { useEffect, useState } from "react";
import { subscribeToBids } from "@/lib/firestore";
import { resolveSpecificBidTitle } from "@/lib/titleSpecificity";
import type { Bid, BidStatus, OpportunityType } from "@/lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const MAX_DAYS_AHEAD = 90;
const DAY_MS = 86_400_000;
const MIN_FY_START = new Date("2026-07-01T00:00:00+03:00").getTime();
const COMPLETED_STATUSES = new Set<BidStatus>(["closed", "evaluation", "awarded", "cancelled"]);
export const SNAPSHOT_REFRESH_EVENT = "bidfinder:refresh-snapshot";

const GRANT_TERMS = [
  "grant",
  "grants",
  "funding opportunity",
  "call for proposals",
  "call for proposal",
  "request for proposals",
  "innovation fund",
  "challenge fund",
  "seed fund",
  "matching grant",
  "small grants",
  "funding window",
  "financial support",
];

const textCache = new Map<string, string>();

function plainText(value: string) {
  if (!value) return "";
  const cached = textCache.get(value);
  if (cached !== undefined) return cached;

  let text = value;
  // Most collector fields are already plain text. Avoid constructing DOMParser
  // instances for every field on every publish unless decoding is actually needed.
  if (/[<&]/.test(text)) {
    const parser = new DOMParser();
    for (let pass = 0; pass < 2; pass += 1) {
      const doc = parser.parseFromString(text, "text/html");
      text = doc.body.textContent || text;
    }
  }
  const result = text.replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  if (textCache.size > 6000) textCache.clear();
  textCache.set(value, result);
  return result;
}

function currentFinancialYearStart(now: Date) {
  const year = now.getUTCMonth() >= 6 ? now.getUTCFullYear() : now.getUTCFullYear() - 1;
  return Math.max(new Date(`${year}-07-01T00:00:00+03:00`).getTime(), MIN_FY_START);
}

function detectOpportunityType(bid: Bid): OpportunityType {
  if (bid.opportunityType) return bid.opportunityType;
  const haystack = [
    bid.title,
    bid.description,
    bid.category,
    bid.procurementType,
    bid.noticeType,
    ...Object.values(bid.sourceMetadata || {}),
  ]
    .join(" ")
    .toLowerCase();

  if (GRANT_TERMS.some((term) => haystack.includes(term))) return "grant";
  return "tender";
}

function normalizeBid(bid: Bid, now = new Date()): Bid | null {
  if (bid.displayEligible === false || COMPLETED_STATUSES.has(bid.status)) return null;

  const deadline = new Date(bid.deadlineAt);
  if (Number.isNaN(deadline.getTime())) return null;

  const nowMs = now.getTime();
  const fyStart = currentFinancialYearStart(now);
  const latestDeadline = nowMs + MAX_DAYS_AHEAD * DAY_MS;
  const deadlineMs = deadline.getTime();

  if (deadlineMs <= nowMs || deadlineMs < fyStart || deadlineMs > latestDeadline) return null;

  if (bid.publishedAt) {
    const published = new Date(bid.publishedAt);
    if (Number.isNaN(published.getTime())) return null;
    const publishedMs = published.getTime();
    if (publishedMs < fyStart || publishedMs > deadlineMs || publishedMs > nowMs + DAY_MS) return null;
  }

  const specificTitle = resolveSpecificBidTitle(bid);
  if (!specificTitle) return null;
  const title = plainText(specificTitle).slice(0, 320);
  if (!title) return null;

  const status: BidStatus = bid.status === "planned" ? "planned" : "open";

  return {
    ...bid,
    title,
    titleSpecificity: "specific",
    displayEligible: true,
    organization: plainText(bid.organization).slice(0, 180),
    referenceNumber: plainText(bid.referenceNumber).slice(0, 140),
    description: plainText(bid.description).slice(0, 2400),
    category: plainText(bid.category).slice(0, 120),
    procurementType: plainText(bid.procurementType).slice(0, 100),
    opportunityType: detectOpportunityType(bid),
    noticeType: plainText(bid.noticeType || "").slice(0, 120),
    sourceMetadata: Object.fromEntries(
      Object.entries(bid.sourceMetadata || {})
        .map(([key, value]) => [plainText(key).slice(0, 120), plainText(value).slice(0, 500)])
        .filter(([key, value]) => key && value),
    ),
    documents: (bid.documents || []).map((document) => ({
      ...document,
      title: plainText(document.title).slice(0, 180),
      kind: plainText(document.kind || "").slice(0, 40),
    })),
    status,
    isOpen: true,
    sources: (bid.sources || []).map((source) => ({ ...source, name: plainText(source.name) })),
  };
}

function mergeSources(left: Bid["sources"], right: Bid["sources"]) {
  const merged = new Map<string, Bid["sources"][number]>();
  for (const source of [...(left || []), ...(right || [])]) {
    merged.set(`${source.id || source.name}|${source.url}`, source);
  }
  return Array.from(merged.values());
}

function mergeBids(snapshotBids: Bid[], liveBids: Bid[]) {
  const merged = new Map<string, Bid>();
  const now = new Date();
  for (const raw of [...snapshotBids, ...liveBids]) {
    const bid = normalizeBid(raw, now);
    if (!bid) continue;

    const existing = merged.get(bid.id);
    if (!existing) {
      merged.set(bid.id, bid);
      continue;
    }

    merged.set(bid.id, {
      ...existing,
      ...bid,
      description: bid.description || existing.description,
      documents: bid.documents?.length ? bid.documents : existing.documents,
      sourceMetadata: Object.keys(bid.sourceMetadata || {}).length ? bid.sourceMetadata : existing.sourceMetadata,
      intelligence: bid.intelligence || existing.intelligence,
      contacts: bid.contacts?.length ? bid.contacts : existing.contacts,
      bidders: bid.bidders?.length ? bid.bidders : existing.bidders,
      openingParticipants: bid.openingParticipants?.length ? bid.openingParticipants : existing.openingParticipants,
      openingCommittee: bid.openingCommittee?.length ? bid.openingCommittee : existing.openingCommittee,
      amendments: bid.amendments?.length ? bid.amendments : existing.amendments,
      lifecycleEvents: bid.lifecycleEvents?.length ? bid.lifecycleEvents : existing.lifecycleEvents,
      sources: mergeSources(existing.sources, bid.sources),
    });
  }
  return Array.from(merged.values());
}

type BidViewState = { bids: Bid[]; loading: boolean; error: string };

// The bid dataset is application data, not page data. Keep one in-memory store and
// one Firestore listener for the entire browser session so route changes never
// re-download/re-parse the same snapshot or reopen the same live subscription.
let viewState: BidViewState = { bids: [], loading: true, error: "" };
let snapshotBids: Bid[] = [];
let liveBids: Bid[] = [];
let snapshotSettled = false;
let liveSettled = false;
let liveError = "";
let storeStarted = false;
let snapshotRequest: Promise<void> | null = null;
let expiryTimer: number | undefined;
const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) listener();
}

function scheduleExpiry() {
  if (typeof window === "undefined") return;
  if (expiryTimer !== undefined) window.clearTimeout(expiryTimer);
  const nowMs = Date.now();
  const nextDeadline = viewState.bids
    .map((item) => new Date(item.deadlineAt).getTime())
    .filter((value) => Number.isFinite(value) && value > nowMs)
    .sort((a, b) => a - b)[0];
  if (nextDeadline === undefined) return;
  const delay = Math.min(Math.max(nextDeadline - nowMs + 100, 100), 2_147_000_000);
  expiryTimer = window.setTimeout(publish, delay);
}

function publish() {
  const merged = mergeBids(snapshotBids, liveBids);
  // A usable static snapshot should render immediately; Firestore is a live
  // enhancement and must never hold the page behind a spinner.
  const loading = !snapshotSettled && liveBids.length === 0;
  const error = merged.length ? "" : snapshotSettled && liveSettled ? liveError : "";
  viewState = { bids: merged, loading, error };
  scheduleExpiry();
  notify();
}

async function fetchSnapshot(path: string, force: boolean) {
  const suffix = force ? `?v=${Date.now()}` : "";
  const response = await fetch(`${basePath}${path}${suffix}`, {
    cache: force ? "no-store" : "default",
  });
  if (!response.ok) throw new Error(`Snapshot request failed: ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error("Invalid opportunity snapshot");
  return data as Bid[];
}

async function loadSnapshot(force = false) {
  if (snapshotRequest && !force) return snapshotRequest;

  const task = (async () => {
    try {
      snapshotBids = await fetchSnapshot("/data/bids.json", force);
    } catch {
      try {
        snapshotBids = await fetchSnapshot("/data/egp-bids.json", force);
      } catch {
        snapshotBids = [];
      }
    } finally {
      snapshotSettled = true;
      publish();
    }
  })();

  snapshotRequest = task;
  try {
    await task;
  } finally {
    if (snapshotRequest === task) snapshotRequest = null;
  }
}

function startStore() {
  if (storeStarted || typeof window === "undefined") return;
  storeStarted = true;

  void loadSnapshot(false);
  window.addEventListener(SNAPSHOT_REFRESH_EVENT, () => void loadSnapshot(true));

  subscribeToBids(
    (items) => {
      liveBids = items;
      liveSettled = true;
      liveError = "";
      publish();
    },
    (reason) => {
      liveSettled = true;
      liveError = reason;
      publish();
    },
  );
}

export function requestSnapshotRefresh() {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(SNAPSHOT_REFRESH_EVENT));
}

export function useBids() {
  const [state, setState] = useState<BidViewState>(() => viewState);

  useEffect(() => {
    const listener = () => setState(viewState);
    listeners.add(listener);
    startStore();
    listener();
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return state;
}
