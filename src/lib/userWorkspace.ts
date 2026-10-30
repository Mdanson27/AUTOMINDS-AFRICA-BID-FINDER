import { doc, onSnapshot, serverTimestamp, setDoc } from "firebase/firestore";
import { db } from "./firebase";

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

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).map((item) => item.trim()).filter(Boolean) : [];
}

export function subscribeCompanyProfile(
  uid: string,
  onData: (profile: CompanyProfile | null) => void,
  onError: (message: string) => void = () => undefined,
) {
  return onSnapshot(doc(db, "companyProfiles", uid), (snapshot) => {
    if (!snapshot.exists()) {
      onData(null);
      return;
    }
    const data = snapshot.data();
    const compliance = data.compliance && typeof data.compliance === "object" ? data.compliance as Record<string, unknown> : {};
    onData({
      ownerUid: uid,
      companyName: String(data.companyName || ""),
      tradingName: String(data.tradingName || ""),
      registrationNumber: String(data.registrationNumber || ""),
      tin: String(data.tin || ""),
      companyType: String(data.companyType || ""),
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
      preferredContractMin: Number(data.preferredContractMin || 0),
      preferredContractMax: Number(data.preferredContractMax || 0),
      currency: String(data.currency || "UGX"),
      yearsExperience: Number(data.yearsExperience || 0),
      pastClients: strings(data.pastClients),
      referenceNotes: String(data.referenceNotes || ""),
      certifications: strings(data.certifications),
      compliance: {
        ursbRegistered: compliance.ursbRegistered === true,
        taxClearance: compliance.taxClearance === true,
        ppdaRegistered: compliance.ppdaRegistered === true,
        vatRegistered: compliance.vatRegistered === true,
      },
      profileStatus: data.profileStatus === "active" ? "active" : "incomplete",
    });
  }, () => onError("We could not load your company profile. Please try again."));
}

export async function saveCompanyProfile(uid: string, profile: Omit<CompanyProfile, "ownerUid" | "profileStatus">) {
  const profileStatus = profile.companyName.trim() && profile.services.length ? "active" : "incomplete";
  await setDoc(doc(db, "companyProfiles", uid), {
    ...profile,
    ownerUid: uid,
    profileStatus,
    updatedAt: serverTimestamp(),
  }, { merge: true });
}

export function subscribeUserPreferences(
  uid: string,
  onData: (preferences: UserPreferences) => void,
  onError: (message: string) => void = () => undefined,
) {
  return onSnapshot(doc(db, "userPreferences", uid), (snapshot) => {
    if (!snapshot.exists()) {
      onData({ ...DEFAULT_USER_PREFERENCES, ownerUid: uid });
      return;
    }
    const data = snapshot.data();
    const scope = ["all", "government", "newspapers", "development", "private"].includes(String(data.scope))
      ? data.scope as UserPreferences["scope"] : "all";
    const closing = [3, 7, 14, 30].includes(Number(data.closingSoonDays)) ? Number(data.closingSoonDays) as UserPreferences["closingSoonDays"] : 14;
    const defaultSort = ["deadline", "newest", "organization"].includes(String(data.defaultSort))
      ? data.defaultSort as UserPreferences["defaultSort"] : "deadline";
    onData({ ownerUid: uid, scope, closingSoonDays: closing, defaultSort, activeOnly: data.activeOnly !== false });
  }, () => onError("We could not load your workspace preferences. Please try again."));
}

export async function saveUserPreferences(uid: string, preferences: Omit<UserPreferences, "ownerUid">) {
  await setDoc(doc(db, "userPreferences", uid), {
    ...preferences,
    ownerUid: uid,
    updatedAt: serverTimestamp(),
  }, { merge: true });
}
