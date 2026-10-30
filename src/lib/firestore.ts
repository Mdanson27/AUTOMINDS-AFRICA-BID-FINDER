import { addDoc, collection, deleteDoc, doc, limit, onSnapshot, orderBy, query, serverTimestamp, setDoc, Timestamp, where } from "firebase/firestore";
import { db } from "./firebase";
import type { Bid, BidSource, BidStatus } from "./types";

const DATA_UNAVAILABLE_MESSAGE = "Live opportunity data is temporarily unavailable. Please try again shortly.";

function iso(value: unknown): string {
  if (value instanceof Timestamp) return value.toDate().toISOString();
  if (value && typeof value === "object" && "toDate" in value && typeof (value as { toDate?: unknown }).toDate === "function") {
    try { return (value as { toDate: () => Date }).toDate().toISOString(); } catch { return ""; }
  }
  if (typeof value === "string") return value;
  return "";
}

export function subscribeToBids(onData: (bids: Bid[]) => void, onError: (message: string) => void) {
  // Firestore is the first display gate: do not even stream already-expired
  // opportunities to normal clients. The hook applies a second independent
  // deadline/lifecycle check before anything reaches the UI.
  const q = query(
    collection(db, "bids"),
    where("deadlineAt", ">=", Timestamp.now()),
    orderBy("deadlineAt", "asc"),
    limit(1000),
  );
  return onSnapshot(q, (snapshot) => onData(snapshot.docs.map((item) => {
    const data = item.data();
    return {
      id: item.id,
      title: data.title || "Untitled opportunity",
      organization: data.organization || "Unknown organization",
      referenceNumber: data.referenceNumber || "",
      description: data.description || "",
      category: data.category || "",
      procurementType: data.procurementType || "",
      procurementMethod: data.procurementMethod || "",
      sourceStage: data.sourceStage || "",
      canonicalSource: data.canonicalSource || "",
      canonicalSourceUrl: data.canonicalSourceUrl || "",
      canonicalIdentity: data.canonicalIdentity || "",
      titleSpecificity: data.titleSpecificity,
      titleSource: data.titleSource,
      displayEligible: data.displayEligible !== false,
      opportunityType: data.opportunityType,
      publishedAt: iso(data.publishedAt),
      deadlineAt: iso(data.deadlineAt),
      status: (data.status || "open") as BidStatus,
      isOpen: data.isOpen !== false,
      fingerprint: data.fingerprint || "",
      firstSeenAt: iso(data.firstSeenAt),
      firstDetectedAt: iso(data.firstDetectedAt),
      lastSeenAt: iso(data.lastSeenAt),
      lastVerifiedAt: iso(data.lastVerifiedAt),
      verificationStatus: data.verificationStatus,
      verificationNote: data.verificationNote || "",
      retentionStatus: data.retentionStatus,
      retainedFromPreviousSnapshot: data.retainedFromPreviousSnapshot === true,
      deadlineChanged: data.deadlineChanged === true,
      deadlineChangedAt: iso(data.deadlineChangedAt),
      noticeType: data.noticeType || "",
      openingAt: iso(data.openingAt),
      applicationUrl: data.applicationUrl || "",
      documents: Array.isArray(data.documents) ? data.documents : [],
      sourceMetadata: data.sourceMetadata && typeof data.sourceMetadata === "object" ? data.sourceMetadata : {},
      intelligence: data.intelligence && typeof data.intelligence === "object" ? data.intelligence : undefined,
      contacts: Array.isArray(data.contacts) ? data.contacts : [],
      bidders: Array.isArray(data.bidders) ? data.bidders : [],
      bidsReceived: typeof data.bidsReceived === "number" ? data.bidsReceived : null,
      openingParticipants: Array.isArray(data.openingParticipants) ? data.openingParticipants : [],
      openingCommittee: Array.isArray(data.openingCommittee) ? data.openingCommittee : [],
      amendments: Array.isArray(data.amendments) ? data.amendments : [],
      lifecycleEvents: Array.isArray(data.lifecycleEvents) ? data.lifecycleEvents : [],
      bestEvaluatedBidder: data.bestEvaluatedBidder || "",
      contractAmount: data.contractAmount || "",
      contractCurrency: data.contractCurrency || "",
      phase4Enriched: data.phase4Enriched === true,
      sources: Array.isArray(data.sources)
        ? data.sources.map((source: Record<string, unknown>) => ({
            id: String(source.id || ""),
            name: String(source.name || "Source"),
            url: String(source.url || "#"),
            detectedAt: iso(source.detectedAt),
          }))
        : [],
    };
  })), () => onError(DATA_UNAVAILABLE_MESSAGE));
}

export function subscribeToSources(onData: (sources: BidSource[]) => void, onError: (message: string) => void) {
  return onSnapshot(collection(db, "sources"), (snapshot) => onData(snapshot.docs.map((item) => {
    const d = item.data();
    return {
      id: item.id,
      name: d.name || "Unnamed source",
      type: d.type || "website",
      baseUrl: d.baseUrl || "",
      health: d.health || "planned",
      enabled: d.enabled !== false,
      lastSuccessfulCrawlAt: iso(d.lastSuccessfulCrawlAt),
      lastAttemptedCrawlAt: iso(d.lastAttemptedCrawlAt),
      recordsFound: d.recordsFound || 0,
      recordsCreated: d.recordsCreated || 0,
      recordsUpdated: d.recordsUpdated || 0,
      recordsUnchanged: d.recordsUnchanged || 0,
      lastError: d.lastError || "",
    };
  })), () => onError(DATA_UNAVAILABLE_MESSAGE));
}

export function subscribeSavedBidIds(uid: string, onData: (ids: Set<string>) => void, onError: () => void = () => undefined) {
  const q = query(collection(db, "savedBids"), where("ownerUid", "==", uid));
  return onSnapshot(q, (snapshot) => onData(new Set(snapshot.docs.map((item) => String(item.data().bidId)))), onError);
}

export async function setSavedBid(uid: string, bidId: string, saved: boolean) {
  const ref = doc(db, "savedBids", `${uid}_${bidId}`);
  if (!saved) return deleteDoc(ref);
  return setDoc(ref, { ownerUid: uid, bidId, savedAt: serverTimestamp(), stage: "watching", notes: "", updatedAt: serverTimestamp() });
}

function fingerprint(value: string) { return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 180); }

export async function addManualBid(input: { title: string; organization: string; referenceNumber: string; description: string; category: string; procurementType: string; publishedAt: string; deadlineAt: string; sourceName: string; sourceUrl: string; }) {
  const now = new Date();
  const deadline = new Date(input.deadlineAt);
  if (Number.isNaN(deadline.getTime())) throw new Error("A valid deadline is required.");
  if (deadline <= now) throw new Error("The deadline must still be open. Expired bids cannot be added.");

  const published = input.publishedAt ? new Date(input.publishedAt) : now;
  if (Number.isNaN(published.getTime())) throw new Error("A valid publication date is required.");
  if (published > deadline) throw new Error("The publication date cannot be after the submission deadline.");

  const sourceName = input.sourceName || "Manual test";
  const record = await addDoc(collection(db, "bids"), {
    title: input.title.trim(), organization: input.organization.trim(), referenceNumber: input.referenceNumber.trim(), description: input.description.trim(), category: input.category.trim(), procurementType: input.procurementType.trim(),
    publishedAt: Timestamp.fromDate(published), deadlineAt: Timestamp.fromDate(deadline), status: "open", isOpen: true, displayEligible: true,
    fingerprint: fingerprint(input.referenceNumber || `${input.organization}-${input.title}`), firstSeenAt: serverTimestamp(), lastSeenAt: serverTimestamp(), createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    deadlineChanged: false,
    sources: [{ id: "manual-test", name: sourceName, url: input.sourceUrl || "#", detectedAt: new Date().toISOString() }], ingestionMode: "manual-test",
  });
  return record.id;
}
