import { auth } from "./firebaseClient";
import { ensureNeonUser, eq, neonSelect, neonUpsert } from "./neonApi";

export type CompanyCompliance = {
  ursbRegistered: boolean;
  taxClearance: boolean;
  ppdaRegistered: boolean;
  vatRegistered: boolean;
};

export type CompanyProfile = {
  ownerUid: string;
  companyName: string;
  tradingName: string;
  registrationNumber: string;
  tin: string;
  companyType: string;
  industry: string;
  description: string;
  website: string;
  email: string;
  phone: string;
  address: string;
  district: string;
  country: string;
  services: string[];
  keywords: string[];
  coverage: string[];
  preferredContractMin: number;
  preferredContractMax: number;
  currency: string;
  yearsExperience: number;
  pastClients: string[];
  referenceNotes: string;
  certifications: string[];
  compliance: CompanyCompliance;
  profileStatus: "active" | "incomplete";
};

export type UserPreferences = {
  ownerUid: string;
  scope: "all" | "government" | "newspapers" | "development" | "private";
  closingSoonDays: 3 | 7 | 14 | 30;
  defaultSort: "deadline" | "newest" | "organization";
  activeOnly: boolean;
};

export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  ownerUid: "",
  scope: "all",
  closingSoonDays: 14,
  defaultSort: "deadline",
  activeOnly: true,
};

const WORKSPACE_EVENT = "bidfinder:workspace-changed";
const COMPANY_PREFIX = "autominds-bidfinder:company:v3";
const PREFS_PREFIX = "autominds-bidfinder:prefs:v3";

function readLocal<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : null;
  } catch {
    return null;
  }
}

function writeLocal(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(value));
  queueMicrotask(() => window.dispatchEvent(new CustomEvent(WORKSPACE_EVENT)));
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).map((item) => item.trim()).filter(Boolean) : [];
}

function companyFromRow(uid: string, data: Record<string, unknown>): CompanyProfile {
  const compliance = data.compliance && typeof data.compliance === "object" ? data.compliance as Record<string, unknown> : {};
  return {
    ownerUid: uid,
    companyName: String(data.company_name || ""),
    tradingName: String(data.trading_name || ""),
    registrationNumber: String(data.registration_number || ""),
    tin: String(data.tin || ""),
    companyType: String(data.company_type || ""),
    industry: String(data.industry || ""),
    description: String(data.description || ""),
    website: String(data.website || ""),
    email: String(data.email || ""),
    phone: String(data.phone || ""),
    address: String(data.address || ""),
    district: String(data.district || ""),
    country: String(data.country || "Uganda"),
    services: strings(data.services),
    keywords: strings(data.keywords),
    coverage: strings(data.coverage),
    preferredContractMin: Number(data.preferred_contract_min || 0),
    preferredContractMax: Number(data.preferred_contract_max || 0),
    currency: String(data.currency || "UGX"),
    yearsExperience: Number(data.years_experience || 0),
    pastClients: strings(data.past_clients),
    referenceNotes: String(data.reference_notes || ""),
    certifications: strings(data.certifications),
    compliance: {
      ursbRegistered: compliance.ursbRegistered === true,
      taxClearance: compliance.taxClearance === true,
      ppdaRegistered: compliance.ppdaRegistered === true,
      vatRegistered: compliance.vatRegistered === true,
    },
    profileStatus: data.profile_status === "active" ? "active" : "incomplete",
  };
}

async function loadCompany(uid: string) {
  try {
    const rows = await neonSelect<Record<string, unknown>>("companies", `select=*&owner_uid=${eq(uid)}&limit=1`);
    if (!rows.length) return readLocal<CompanyProfile>(`${COMPANY_PREFIX}:${uid}`);
    const profile = companyFromRow(uid, rows[0]);
    writeLocal(`${COMPANY_PREFIX}:${uid}`, profile);
    return profile;
  } catch {
    return readLocal<CompanyProfile>(`${COMPANY_PREFIX}:${uid}`);
  }
}

export function subscribeCompanyProfile(
  uid: string,
  onData: (profile: CompanyProfile | null) => void,
  onError: (message: string) => void = () => undefined,
) {
  let active = true;
  const load = () => void loadCompany(uid).then((value) => {
    if (active) onData(value);
  }).catch(() => {
    if (active) onError("We could not load your company profile. Please try again.");
  });

  load();
  if (typeof window === "undefined") return () => { active = false; };
  const refresh = () => load();
  window.addEventListener(WORKSPACE_EVENT, refresh);
  window.addEventListener("focus", refresh);
  return () => {
    active = false;
    window.removeEventListener(WORKSPACE_EVENT, refresh);
    window.removeEventListener("focus", refresh);
  };
}

export async function saveCompanyProfile(uid: string, profile: Omit<CompanyProfile, "ownerUid" | "profileStatus">) {
  const profileStatus = profile.companyName.trim() && profile.services.length ? "active" : "incomplete";
  const local: CompanyProfile = { ...profile, ownerUid: uid, profileStatus };
  writeLocal(`${COMPANY_PREFIX}:${uid}`, local);
  await ensureNeonUser();
  await neonUpsert("companies", {
    owner_uid: uid,
    company_name: profile.companyName,
    trading_name: profile.tradingName,
    registration_number: profile.registrationNumber,
    tin: profile.tin,
    company_type: profile.companyType,
    industry: profile.industry,
    description: profile.description,
    website: profile.website,
    email: profile.email,
    phone: profile.phone,
    address: profile.address,
    district: profile.district,
    country: profile.country,
    services: profile.services,
    keywords: profile.keywords,
    coverage: profile.coverage,
    preferred_contract_min: profile.preferredContractMin,
    preferred_contract_max: profile.preferredContractMax,
    currency: profile.currency,
    years_experience: profile.yearsExperience,
    past_clients: profile.pastClients,
    reference_notes: profile.referenceNotes,
    certifications: profile.certifications,
    compliance: profile.compliance,
    profile_status: profileStatus,
    updated_at: new Date().toISOString(),
  }, "owner_uid");
}

function preferencesFromRow(uid: string, data: Record<string, unknown>): UserPreferences {
  const scope = ["all", "government", "newspapers", "development", "private"].includes(String(data.scope))
    ? data.scope as UserPreferences["scope"] : "all";
  const closing = [3, 7, 14, 30].includes(Number(data.closing_soon_days))
    ? Number(data.closing_soon_days) as UserPreferences["closingSoonDays"] : 14;
  const defaultSort = ["deadline", "newest", "organization"].includes(String(data.default_sort))
    ? data.default_sort as UserPreferences["defaultSort"] : "deadline";
  return { ownerUid: uid, scope, closingSoonDays: closing, defaultSort, activeOnly: data.active_only !== false };
}

async function loadPreferences(uid: string) {
  try {
    const rows = await neonSelect<Record<string, unknown>>("user_preferences", `select=*&owner_uid=${eq(uid)}&limit=1`);
    const prefs = rows.length
      ? preferencesFromRow(uid, rows[0])
      : readLocal<UserPreferences>(`${PREFS_PREFIX}:${uid}`) || { ...DEFAULT_USER_PREFERENCES, ownerUid: uid };
    writeLocal(`${PREFS_PREFIX}:${uid}`, prefs);
    return prefs;
  } catch {
    return readLocal<UserPreferences>(`${PREFS_PREFIX}:${uid}`) || { ...DEFAULT_USER_PREFERENCES, ownerUid: uid };
  }
}

export function subscribeUserPreferences(
  uid: string,
  onData: (preferences: UserPreferences) => void,
  onError: (message: string) => void = () => undefined,
) {
  let active = true;
  const load = () => void loadPreferences(uid).then((value) => {
    if (active) onData(value);
  }).catch(() => {
    if (active) onError("We could not load your workspace preferences. Please try again.");
  });
  load();
  if (typeof window === "undefined") return () => { active = false; };
  const refresh = () => load();
  window.addEventListener(WORKSPACE_EVENT, refresh);
  window.addEventListener("focus", refresh);
  return () => {
    active = false;
    window.removeEventListener(WORKSPACE_EVENT, refresh);
    window.removeEventListener("focus", refresh);
  };
}

export async function saveUserPreferences(uid: string, preferences: Omit<UserPreferences, "ownerUid">) {
  const local: UserPreferences = { ...preferences, ownerUid: uid };
  writeLocal(`${PREFS_PREFIX}:${uid}`, local);
  if (!auth.currentUser) throw new Error("Your session is no longer available. Please sign in again.");
  await ensureNeonUser();
  await neonUpsert("user_preferences", {
    owner_uid: uid,
    scope: preferences.scope,
    closing_soon_days: preferences.closingSoonDays,
    default_sort: preferences.defaultSort,
    active_only: preferences.activeOnly,
    updated_at: new Date().toISOString(),
  }, "owner_uid");
}
