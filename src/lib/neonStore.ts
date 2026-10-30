import type { Bid, BidSource, BidStatus } from "./types";
import { eq, neonDelete, neonInsert, neonSelect, neonUpsert } from "./neonApi";

const DATA_UNAVAILABLE_MESSAGE = "Live opportunity data is temporarily unavailable. Please try again shortly.";

function iso(value: unknown): string {
  if (!value) return "";
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "string") return value;
  return "";
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : [];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function bidFromRow(row: Record<string, unknown>): Bid {
  const raw = asRecord(row.raw_record);
  const merged = { ...raw, ...row } as Record<string, unknown>;
  const rawSources = asArray<Record<string, unknown>>(raw.sources || row.sources);
  return {
    id: String(merged.id || ""),
    title: String(merged.title || "Untitled opportunity"),
    organization: String(merged.organization || "Unknown organization"),
    referenceNumber: String(merged.referenceNumber || merged.reference_number || ""),
    description: String(merged.description || ""),
    category: String(merged.category || ""),
    procurementType: String(merged.procurementType || merged.procurement_type || ""),
    procurementMethod: String(merged.procurementMethod || merged.procurement_method || ""),
    sourceStage: String(merged.sourceStage || merged.source_stage || ""),
    canonicalSource: String(merged.canonicalSource || merged.canonical_source || ""),
    canonicalSourceUrl: String(merged.canonicalSourceUrl || merged.canonical_source_url || ""),
    canonicalIdentity: String(merged.canonicalIdentity || merged.canonical_identity || ""),
    titleSpecificity: merged.titleSpecificity === "specific" || merged.title_specificity === "specific" ? "specific" : merged.titleSpecificity === "unresolved" || merged.title_specificity === "unresolved" ? "unresolved" : undefined,
    titleSource: String(merged.titleSource || merged.title_source || "") || undefined,
    displayEligible: merged.displayEligible !== false && merged.display_eligible !== false,
    opportunityType: (merged.opportunityType || merged.opportunity_type || "tender") as Bid["opportunityType"],
    publishedAt: iso(merged.publishedAt || merged.published_at),
    deadlineAt: iso(merged.deadlineAt || merged.deadline_at),
    status: String(merged.status || "open") as BidStatus,
    isOpen: merged.isOpen !== false && merged.is_open !== false,
    fingerprint: String(merged.fingerprint || ""),
    firstSeenAt: iso(merged.firstSeenAt || merged.first_seen_at || merged.created_at),
    firstDetectedAt: iso(merged.firstDetectedAt || merged.first_detected_at),
    lastSeenAt: iso(merged.lastSeenAt || merged.last_seen_at || merged.updated_at),
    lastVerifiedAt: iso(merged.lastVerifiedAt || merged.last_verified_at),
    verificationStatus: merged.verificationStatus as Bid["verificationStatus"],
    verificationNote: String(merged.verificationNote || merged.verification_note || ""),
    retentionStatus: merged.retentionStatus as Bid["retentionStatus"],
    retainedFromPreviousSnapshot: merged.retainedFromPreviousSnapshot === true || merged.retained_from_previous_snapshot === true,
    sources: rawSources.map((source) => ({
      id: String(source.id || ""),
      name: String(source.name || "Source"),
      url: String(source.url || "#"),
      detectedAt: iso(source.detectedAt || source.detected_at),
    })),
    deadlineChanged: merged.deadlineChanged === true || merged.deadline_changed === true,
    deadlineChangedAt: iso(merged.deadlineChangedAt || merged.deadline_changed_at),
    noticeType: String(merged.noticeType || merged.notice_type || ""),
    openingAt: iso(merged.openingAt || merged.opening_at),
    applicationUrl: String(merged.applicationUrl || merged.application_url || ""),
    documents: asArray(merged.documents),
    sourceMetadata: asRecord(merged.sourceMetadata || merged.source_metadata) as Record<string, string>,
    intelligence: asRecord(merged.intelligence) as Bid["intelligence"],
    contacts: asArray(merged.contacts),
    bidders: asArray(merged.bidders),
    bidsReceived: typeof (merged.bidsReceived ?? merged.bids_received) === "number" ? Number(merged.bidsReceived ?? merged.bids_received) : null,
    openingParticipants: asArray(merged.openingParticipants || merged.opening_participants),
    openingCommittee: asArray(merged.openingCommittee || merged.opening_committee),
    amendments: asArray(merged.amendments),
    lifecycleEvents: asArray(merged.lifecycleEvents || merged.lifecycle_events),
    bestEvaluatedBidder: String(merged.bestEvaluatedBidder || merged.best_evaluated_bidder || ""),
    contractAmount: String(merged.contractAmount || merged.contract_amount || ""),
    contractCurrency: String(merged.contractCurrency || merged.contract_currency || ""),
    phase4Enriched: merged.phase4Enriched === true || merged.phase4_enriched === true,
  };
}

export async function fetchLiveBids() {
  const rows = await neonSelect<Record<string, unknown>>(
    "bids",
    "select=*&order=deadline_at.asc&limit=1000",
  );
  return rows.map(bidFromRow);
}

export function subscribeToBids(onData: (bids: Bid[]) => void, onError: (message: string) => void) {
  let active = true;
  let timer: number | undefined;

  const load = async () => {
    try {
      const items = await fetchLiveBids();
      if (active) onData(items);
    } catch {
      if (active) onError(DATA_UNAVAILABLE_MESSAGE);
    }
  };

  void load();
  if (typeof window !== "undefined") {
    timer = window.setInterval(() => void load(), 60_000);
    const focus = () => void load();
    window.addEventListener("focus", focus);
    return () => {
      active = false;
      if (timer !== undefined) window.clearInterval(timer);
      window.removeEventListener("focus", focus);
    };
  }

  return () => { active = false; };
}

function sourceFromRow(row: Record<string, unknown>): BidSource {
  const metadata = asRecord(row.metadata);
  return {
    id: String(row.id || ""),
    name: String(row.name || "Unnamed source"),
    type: String(row.source_type || metadata.type || "website"),
    baseUrl: String(row.base_url || metadata.baseUrl || ""),
    health: String(row.health || "planned") as BidSource["health"],
    enabled: row.enabled !== false,
    lastSuccessfulCrawlAt: iso(row.last_successful_crawl_at),
    lastAttemptedCrawlAt: iso(row.last_attempted_crawl_at),
    recordsFound: Number(row.records_found || 0),
    recordsCreated: Number(row.records_created || 0),
    recordsUpdated: Number(row.records_updated || 0),
    recordsUnchanged: Number(row.records_unchanged || 0),
    lastError: String(row.last_error || ""),
    collectorStatus: String(metadata.collectorStatus || metadata.collector_status || "") || undefined,
    captureStatus: String(metadata.captureStatus || metadata.capture_status || "") || undefined,
    httpStatus: typeof metadata.httpStatus === "number" ? metadata.httpStatus : null,
    discoveryMethod: String(metadata.discoveryMethod || "") || undefined,
    urlsDiscovered: Number(metadata.urlsDiscovered || 0),
    urlsSuccessfullyFetched: Number(metadata.urlsSuccessfullyFetched || 0),
    recordsExtracted: Number(metadata.recordsExtracted || 0),
    recordsNormalized: Number(metadata.recordsNormalized || 0),
    recordsRejected: Number(metadata.recordsRejected || 0),
    duplicates: Number(metadata.duplicates || 0),
    updates: Number(metadata.updates || 0),
    parserErrors: Number(metadata.parserErrors || 0),
    captureWarnings: asArray<string>(metadata.captureWarnings),
    directStatus: String(metadata.directStatus || "") || undefined,
    renderStatus: String(metadata.renderStatus || "") || undefined,
    discoveryStatus: String(metadata.discoveryStatus || "") || undefined,
    needsReview: Number(metadata.needsReview || 0),
    verifiedRecords: Number(metadata.verifiedRecords || 0),
  };
}

export async function fetchLiveSources() {
  const rows = await neonSelect<Record<string, unknown>>("sources", "select=*&order=name.asc&limit=200");
  return rows.map(sourceFromRow);
}

export function subscribeToSources(onData: (sources: BidSource[]) => void, onError: (message: string) => void) {
  let active = true;
  const load = async () => {
    try {
      const items = await fetchLiveSources();
      if (active) onData(items);
    } catch {
      if (active) onError(DATA_UNAVAILABLE_MESSAGE);
    }
  };
  void load();
  const timer = typeof window !== "undefined" ? window.setInterval(() => void load(), 120_000) : undefined;
  return () => {
    active = false;
    if (timer !== undefined) window.clearInterval(timer);
  };
}

export async function setSavedBid(uid: string, bidId: string, saved: boolean, snapshot?: Bid) {
  if (!saved) {
    await neonDelete("saved_bids", `owner_uid=${eq(uid)}&bid_id=${eq(bidId)}`);
    return;
  }
  const now = new Date().toISOString();
  await neonUpsert("saved_bids", {
    owner_uid: uid,
    bid_id: bidId,
    stage: "watching",
    notes: "",
    snapshot: snapshot || {},
    saved_at: now,
    updated_at: now,
  }, "owner_uid,bid_id");
}

function fingerprint(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 180);
}

export async function addManualBid(input: { title: string; organization: string; referenceNumber: string; description: string; category: string; procurementType: string; publishedAt: string; deadlineAt: string; sourceName: string; sourceUrl: string; }) {
  const now = new Date();
  const deadline = new Date(input.deadlineAt);
  if (Number.isNaN(deadline.getTime())) throw new Error("A valid deadline is required.");
  if (deadline <= now) throw new Error("The deadline must still be open. Expired bids cannot be added.");
  const published = input.publishedAt ? new Date(input.publishedAt) : now;
  if (Number.isNaN(published.getTime())) throw new Error("A valid publication date is required.");
  if (published > deadline) throw new Error("The publication date cannot be after the submission deadline.");

  const id = `manual-${crypto.randomUUID()}`;
  const sourceName = input.sourceName || "Manual test";
  const raw: Bid = {
    id,
    title: input.title.trim(),
    organization: input.organization.trim(),
    referenceNumber: input.referenceNumber.trim(),
    description: input.description.trim(),
    category: input.category.trim(),
    procurementType: input.procurementType.trim(),
    publishedAt: published.toISOString(),
    deadlineAt: deadline.toISOString(),
    status: "open",
    isOpen: true,
    displayEligible: true,
    fingerprint: fingerprint(input.referenceNumber || `${input.organization}-${input.title}`),
    firstSeenAt: now.toISOString(),
    lastSeenAt: now.toISOString(),
    sources: [{ id: "manual-test", name: sourceName, url: input.sourceUrl || "#", detectedAt: now.toISOString() }],
  };
  await neonInsert("bids", {
    id,
    title: raw.title,
    organization: raw.organization,
    reference_number: raw.referenceNumber,
    description: raw.description,
    category: raw.category,
    procurement_type: raw.procurementType,
    display_eligible: true,
    opportunity_type: "tender",
    status: "open",
    is_open: true,
    fingerprint: raw.fingerprint,
    published_at: raw.publishedAt,
    deadline_at: raw.deadlineAt,
    raw_record: raw,
    updated_at: now.toISOString(),
  });
  return id;
}
