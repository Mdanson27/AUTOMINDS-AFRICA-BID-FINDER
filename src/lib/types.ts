export type BidStatus = "planned" | "open" | "closed" | "evaluation" | "awarded" | "cancelled";
export type UserRole = "viewer" | "admin";

export type UserProfile = { uid: string; email: string; displayName: string; role: UserRole };
export type BidSourceRef = { name: string; url: string; detectedAt?: string };
export type Bid = {
  id: string; title: string; organization: string; referenceNumber: string; description: string; category: string;
  procurementType: string; publishedAt: string; deadlineAt: string; status: BidStatus; isOpen: boolean; fingerprint: string;
  firstSeenAt: string; lastSeenAt: string; sources: BidSourceRef[];
};
export type SourceHealth = "healthy" | "warning" | "paused" | "planned";
export type BidSource = { id: string; name: string; type: string; baseUrl: string; health: SourceHealth; enabled: boolean; lastSuccessfulCrawlAt?: string; lastAttemptedCrawlAt?: string; recordsFound?: number; recordsCreated?: number; recordsUpdated?: number; lastError?: string };
