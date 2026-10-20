export type BidStatus = "planned" | "open" | "closed" | "evaluation" | "awarded" | "cancelled";
export type OpportunityType = "tender" | "grant" | "other";
export type UserRole = "viewer" | "admin";

export type UserProfile = { uid: string; email: string; displayName: string; role: UserRole };
export type BidSourceRef = { id?: string; name: string; url: string; detectedAt?: string };
export type BidDocument = { title: string; url: string; kind?: string };
export type BidVerificationStatus =
  | "verified"
  | "source-unavailable"
  | "not-seen-current-scan"
  | "not-verified-current-scan";
export type BidStatusHistoryEntry = {
  status: BidStatus;
  at: string;
  reason: string;
};

export type BidContact = {
  label?: string;
  value: string;
  kind?: "email" | "phone" | "address" | "other";
};

export type BidderIntelligence = {
  name: string;
  address?: string;
  submissionAt?: string;
  amount?: string;
  currency?: string;
  rank?: string;
  status?: string;
  evaluationStage?: string;
  reasons?: string[];
};

export type OpeningParticipant = {
  name: string;
  address?: string;
  position?: string;
  departmentCompany?: string;
};

export type BidAmendment = {
  title: string;
  url?: string;
  publishedAt?: string;
  summary?: string;
};

export type ProcurementLifecycleStage =
  | "advertised"
  | "updated"
  | "closed"
  | "bid-opening"
  | "evaluation"
  | "award"
  | "cancelled";

export type ProcurementLifecycleEvent = {
  stage: ProcurementLifecycleStage;
  title: string;
  occurredAt?: string;
  sourceUrl?: string;
  details?: Record<string, string>;
};

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
  procurementMethod?: string;
  sourceStage?: string;
  canonicalSource?: string;
  canonicalSourceUrl?: string;
  canonicalIdentity?: string;
  titleSpecificity?: "specific" | "unresolved";
  titleSource?: "source-metadata" | "source-title" | "description" | "unresolved" | string;
  displayEligible?: boolean;
  opportunityType?: OpportunityType;
  publishedAt: string;
  deadlineAt: string;
  status: BidStatus;
  isOpen: boolean;
  fingerprint: string;
  firstSeenAt: string;
  firstDetectedAt?: string;
  lastSeenAt: string;
  lastVerifiedAt?: string;
  verificationStatus?: BidVerificationStatus;
  verificationNote?: string;
  retentionStatus?: "active" | "active-retained" | "expired" | "deadline-unknown";
  retainedFromPreviousSnapshot?: boolean;
  statusHistory?: BidStatusHistoryEntry[];
  sources: BidSourceRef[];
  deadlineChanged?: boolean;
  deadlineChangedAt?: string;
  noticeType?: string;
  openingAt?: string;
  applicationUrl?: string;
  documents?: BidDocument[];
  sourceMetadata?: Record<string, string>;
  intelligence?: BidIntelligence;

  // Phase 4 structured procurement intelligence.
  contacts?: BidContact[];
  bidders?: BidderIntelligence[];
  bidsReceived?: number | null;
  openingParticipants?: OpeningParticipant[];
  openingCommittee?: string[];
  amendments?: BidAmendment[];
  lifecycleEvents?: ProcurementLifecycleEvent[];
  bestEvaluatedBidder?: string;
  contractAmount?: string;
  contractCurrency?: string;
  phase4Enriched?: boolean;
};

export type GrantOpportunity = {
  id: string;
  title: string;
  funder: string;
  opportunityNumber?: string;
  summary?: string;
  geography?: string;
  fundingAmount?: string;
  eligibility?: string;
  openDate?: string;
  deadlineAt?: string;
  status: "open" | "forecasted" | "closed";
  sourceName: string;
  sourceUrl: string;
  applicationUrl?: string;
  collectedAt: string;
};

export type ProcurementPlanItem = {
  number: number;
  category: string;
  estimatedAmountUGX: string;
};

export type ProcurementPlan = {
  id: string;
  name: string;
  organization: string;
  financialYear: string;
  totalEstimatedAmountUGX: string;
  sourceUrl: string;
  pdfUrl?: string;
  excelUrl?: string;
  collectedAt: string;
  items: ProcurementPlanItem[];
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
  recordsFound?: number | null;
  recordsCreated?: number;
  recordsUpdated?: number;
  recordsUnchanged?: number;
  lastError?: string;
  collectorStatus?: string;
  captureStatus?: string;
  httpStatus?: number | null;
  discoveryMethod?: string;
  urlsDiscovered?: number;
  urlsFetched?: number;
  recordsExtracted?: number;
  recordsNormalized?: number;
  recordsRejected?: number;
  duplicates?: number;
  updates?: number;
  parserErrors?: number;
  captureWarnings?: string[];
  startedAt?: string;
  completedAt?: string;
  directStatus?: string;
  renderStatus?: string;
  discoveryStatus?: string;
  reviewRequired?: number;
  verified?: number;
};
