import { addDoc, collection, deleteDoc, doc, limit, onSnapshot, orderBy, query, serverTimestamp, setDoc, Timestamp, where } from "firebase/firestore";
import { db } from "./firebase";
import type { Bid, BidSource, BidStatus } from "./types";

function iso(value: unknown): string {
  if (value instanceof Timestamp) return value.toDate().toISOString();
  if (typeof value === "string") return value;
  return "";
}

export function subscribeToBids(onData: (bids: Bid[]) => void, onError: (message: string) => void) {
  const q = query(collection(db, "bids"), orderBy("deadlineAt", "asc"), limit(300));
  return onSnapshot(q, (snapshot) => onData(snapshot.docs.map((item) => {
    const data = item.data();
    return {
      id: item.id, title: data.title || "Untitled opportunity", organization: data.organization || "Unknown organization",
      referenceNumber: data.referenceNumber || "", description: data.description || "", category: data.category || "",
      procurementType: data.procurementType || "", publishedAt: iso(data.publishedAt), deadlineAt: iso(data.deadlineAt),
      status: (data.status || "open") as BidStatus, isOpen: data.isOpen !== false, fingerprint: data.fingerprint || "",
      firstSeenAt: iso(data.firstSeenAt), lastSeenAt: iso(data.lastSeenAt), sources: Array.isArray(data.sources) ? data.sources.map((source: Record<string, unknown>) => ({ name: String(source.name || "Source"), url: String(source.url || "#"), detectedAt: iso(source.detectedAt) })) : [],
    };
  })), (error) => onError(error.message));
}

export function subscribeToSources(onData: (sources: BidSource[]) => void, onError: (message: string) => void) {
  return onSnapshot(collection(db, "sources"), (snapshot) => onData(snapshot.docs.map((item) => {
    const d = item.data(); return { id: item.id, name: d.name || "Unnamed source", type: d.type || "website", baseUrl: d.baseUrl || "", health: d.health || "planned", enabled: d.enabled !== false, lastSuccessfulCrawlAt: iso(d.lastSuccessfulCrawlAt), lastAttemptedCrawlAt: iso(d.lastAttemptedCrawlAt), recordsFound: d.recordsFound || 0, recordsCreated: d.recordsCreated || 0, recordsUpdated: d.recordsUpdated || 0, lastError: d.lastError || "" };
  })), (error) => onError(error.message));
}

export function subscribeSavedBidIds(uid: string, onData: (ids: Set<string>) => void) {
  const q = query(collection(db, "savedBids"), where("ownerUid", "==", uid));
  return onSnapshot(q, (snapshot) => onData(new Set(snapshot.docs.map((item) => String(item.data().bidId)))));
}

export async function setSavedBid(uid: string, bidId: string, saved: boolean) {
  const ref = doc(db, "savedBids", `${uid}_${bidId}`);
  if (!saved) return deleteDoc(ref);
  return setDoc(ref, { ownerUid: uid, bidId, savedAt: serverTimestamp() });
}

function fingerprint(value: string) { return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 180); }

export async function addManualBid(input: { title: string; organization: string; referenceNumber: string; description: string; category: string; procurementType: string; publishedAt: string; deadlineAt: string; sourceName: string; sourceUrl: string; }) {
  const deadline = new Date(input.deadlineAt); if (Number.isNaN(deadline.getTime())) throw new Error("A valid deadline is required.");
  const published = input.publishedAt ? new Date(input.publishedAt) : new Date();
  const sourceName = input.sourceName || "Manual test";
  const record = await addDoc(collection(db, "bids"), {
    title: input.title.trim(), organization: input.organization.trim(), referenceNumber: input.referenceNumber.trim(), description: input.description.trim(), category: input.category.trim(), procurementType: input.procurementType.trim(),
    publishedAt: Timestamp.fromDate(published), deadlineAt: Timestamp.fromDate(deadline), status: "open", isOpen: true,
    fingerprint: fingerprint(input.referenceNumber || `${input.organization}-${input.title}`), firstSeenAt: serverTimestamp(), lastSeenAt: serverTimestamp(), createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    sources: [{ name: sourceName, url: input.sourceUrl || "#", detectedAt: new Date().toISOString() }], ingestionMode: "manual-test",
  });
  return record.id;
}
