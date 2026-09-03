export type BidStatus = "planned" | "open" | "closed" | "evaluation" | "awarded" | "cancelled";
export type UserRole = "viewer" | "admin";

export type UserProfile = { uid: string; email: string; displayName: string; role: UserRole };
export type BidSourceRef = { id?: string; name: string; url: string; detectedAt?: string };

export type BidIntelligence = {
  enrichmentStatus?: "basic" | "partial" | "enriched";
  confidence?: "low" | "medium" | "high";
  bidSecurity?: string;
  tenderFee?: string;
  submissionMethod?: string;
  mandatoryRequirements?: string[];
  eligibility?: string[];
  keyDates?: string[];
};

export type Bid = {
  id: string;
  title: string;
  organization: string;
  referenceNumber: string;
  description: string;
  category: string;
  procurementType: string;
  publishedAt: string;
  deadlineAt: string;
  status: BidStatus;
  isOpen: boolean;
  fingerprint: string;
  firstSeenAt: string;
  lastSeenAt: string;
  sources: BidSourceRef[];
  deadlineChanged?: boolean;
  deadlineChangedAt?: string;
  intelligence?: BidIntelligence;
};

export type SourceHealth = "healthy" | "warning" | "paused" | "planned";
export type BidSource = {
  id: string;
  name: string;
  type: string;
  baseUrl: string;
  health: SourceHealth;
  enabled: boolean;
  lastSuccessfulCrawlAt?: string;
  lastAttemptedCrawlAt?: string;
  recordsFound?: number;
  recordsCreated?: number;
  recordsUpdated?: number;
  recordsUnchanged?: number;
  lastError?: string;
};
