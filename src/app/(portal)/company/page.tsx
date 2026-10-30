"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { BriefcaseBusiness, Building2, Check, CheckCircle2, FileBadge2, Loader2, MapPin, Save, ShieldCheck, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/components/auth/AuthProvider";
import { saveCompanyProfile, subscribeCompanyProfile } from "@/lib/userWorkspace";

type FormState = {
  companyName: string; tradingName: string; registrationNumber: string; tin: string; companyType: string; industry: string;
  description: string; website: string; email: string; phone: string; address: string; district: string; country: string;
  services: string; keywords: string; coverage: string; preferredContractMin: string; preferredContractMax: string; currency: string;
  yearsExperience: string; pastClients: string; referenceNotes: string; certifications: string;
  ursbRegistered: boolean; taxClearance: boolean; ppdaRegistered: boolean; vatRegistered: boolean;
};

const emptyForm: FormState = {
  companyName: "", tradingName: "", registrationNumber: "", tin: "", companyType: "", industry: "", description: "", website: "", email: "", phone: "",
  address: "", district: "", country: "Uganda", services: "", keywords: "", coverage: "", preferredContractMin: "", preferredContractMax: "", currency: "UGX",
  yearsExperience: "", pastClients: "", referenceNotes: "", certifications: "", ursbRegistered: false, taxClearance: false, ppdaRegistered: false, vatRegistered: false,
};

function list(value: string) { return value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean); }

export default function CompanyPage() {
  const { user } = useAuth();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [hasProfile, setHasProfile] = useState(false);

  useEffect(() => {
    if (!user?.uid) return;
    return subscribeCompanyProfile(user.uid, (profile) => {
      if (profile) {
        setHasProfile(true);
        setForm({
          companyName: profile.companyName, tradingName: profile.tradingName, registrationNumber: profile.registrationNumber, tin: profile.tin,
          companyType: profile.companyType, industry: profile.industry, description: profile.description, website: profile.website, email: profile.email,
          phone: profile.phone, address: profile.address, district: profile.district, country: profile.country || "Uganda", services: profile.services.join(", "),
          keywords: profile.keywords.join(", "), coverage: profile.coverage.join(", "), preferredContractMin: profile.preferredContractMin ? String(profile.preferredContractMin) : "",
          preferredContractMax: profile.preferredContractMax ? String(profile.preferredContractMax) : "", currency: profile.currency || "UGX",
          yearsExperience: profile.yearsExperience ? String(profile.yearsExperience) : "", pastClients: profile.pastClients.join(", "), referenceNotes: profile.referenceNotes,
          certifications: profile.certifications.join(", "), ursbRegistered: profile.compliance.ursbRegistered, taxClearance: profile.compliance.taxClearance,
          ppdaRegistered: profile.compliance.ppdaRegistered, vatRegistered: profile.compliance.vatRegistered,
        });
      }
      setLoading(false);
    }, (message) => { setError(message); setLoading(false); });
  }, [user?.uid]);

  const completion = useMemo(() => {
    const checks = [form.companyName, form.registrationNumber || form.tin, form.industry, form.description, form.services, form.coverage, form.phone || form.email, form.keywords];
    return Math.round((checks.filter((value) => value.trim()).length / checks.length) * 100);
  }, [form]);

  function field<K extends keyof FormState>(key: K, value: FormState[K]) { setForm((current) => ({ ...current, [key]: value })); }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!user?.uid) return;
    if (!form.companyName.trim()) { setError("Company name is required."); return; }
    if (!form.services.trim()) { setError("Add at least one service or product so Bid Finder can match opportunities correctly."); return; }
    const min = Number(form.preferredContractMin || 0); const max = Number(form.preferredContractMax || 0);
    if (min < 0 || max < 0 || (min && max && min > max)) { setError("Preferred contract range is not valid."); return; }
    setSaving(true); setSaved(false); setError("");
    try {
      await saveCompanyProfile(user.uid, {
        companyName: form.companyName.trim(), tradingName: form.tradingName.trim(), registrationNumber: form.registrationNumber.trim(), tin: form.tin.trim(),
        companyType: form.companyType.trim(), industry: form.industry.trim(), description: form.description.trim(), website: form.website.trim(), email: form.email.trim(),
        phone: form.phone.trim(), address: form.address.trim(), district: form.district.trim(), country: form.country.trim() || "Uganda", services: list(form.services),
        keywords: list(form.keywords), coverage: list(form.coverage), preferredContractMin: min, preferredContractMax: max, currency: form.currency,
        yearsExperience: Math.max(0, Number(form.yearsExperience || 0)), pastClients: list(form.pastClients), referenceNotes: form.referenceNotes.trim(), certifications: list(form.certifications),
        compliance: { ursbRegistered: form.ursbRegistered, taxClearance: form.taxClearance, ppdaRegistered: form.ppdaRegistered, vatRegistered: form.vatRegistered },
      });
      setHasProfile(true); setSaved(true); window.setTimeout(() => setSaved(false), 2200);
    } catch { setError("Your company profile could not be saved. Please check your connection and try again."); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="page-stack"><section className="panel suite-loading-panel"><Loader2 className="spin" size={20} /> Loading company profile…</section></div>;

  return <div className="page-stack suite-company-page">
    <PageHeader eyebrow="Company intelligence" title="My company" description="Add your company once and use the profile as the matching foundation for procurement discovery, eligibility and relevance scoring." />

    <section className="suite-hero suite-company-hero">
      <div className="suite-company-hero-copy"><span className="eyebrow">{hasProfile ? "PROFILE ACTIVE" : "COMPANY SETUP"}</span><h2>{hasProfile ? form.companyName || "Your company profile" : "Add your company to Bid Finder."}</h2><p>Bid Finder uses this information to understand what you sell, where you operate, the contract sizes you target and the compliance signals that matter when screening opportunities.</p><div className="suite-company-hero-tags"><span><Sparkles size={14} /> Relevance scoring</span><span><CheckCircle2 size={14} /> Eligibility checks</span><span><FileBadge2 size={14} /> Requirement matching</span></div></div>
      <div className="suite-profile-meter"><strong>{completion}%</strong><span>Profile completeness</span><div><i style={{ width: `${completion}%` }} /></div></div>
    </section>

    <form className="suite-company-form" onSubmit={submit}>
      <section className="panel suite-form-section"><div className="suite-form-section-head"><span><Building2 size={19} /></span><div><h2>Company identity</h2><p>Legal and contact information used to identify your business.</p></div></div><div className="suite-form-grid">
        <label><span>Legal company name *</span><input value={form.companyName} onChange={(e) => field("companyName", e.target.value)} placeholder="e.g. AutoMinds Africa Ltd" /></label>
        <label><span>Trading name</span><input value={form.tradingName} onChange={(e) => field("tradingName", e.target.value)} placeholder="Public-facing business name" /></label>
        <label><span>Registration number</span><input value={form.registrationNumber} onChange={(e) => field("registrationNumber", e.target.value)} placeholder="URSB registration number" /></label>
        <label><span>TIN</span><input value={form.tin} onChange={(e) => field("tin", e.target.value)} placeholder="Tax Identification Number" /></label>
        <label><span>Company type</span><select value={form.companyType} onChange={(e) => field("companyType", e.target.value)}><option value="">Select type</option><option>Limited company</option><option>Partnership</option><option>Sole proprietorship</option><option>NGO / Non-profit</option><option>Other</option></select></label>
        <label><span>Primary industry</span><input value={form.industry} onChange={(e) => field("industry", e.target.value)} placeholder="e.g. Technology, Construction" /></label>
        <label className="span-2"><span>Company description</span><textarea rows={4} value={form.description} onChange={(e) => field("description", e.target.value)} placeholder="Describe what the company does, its strengths and the work it is best positioned to deliver." /></label>
      </div></section>

      <section className="panel suite-form-section"><div className="suite-form-section-head"><span><BriefcaseBusiness size={19} /></span><div><h2>Capabilities & target contracts</h2><p>Tell the matching engine exactly what you can supply or deliver.</p></div></div><div className="suite-form-grid">
        <label className="span-2"><span>Products & services *</span><textarea rows={3} value={form.services} onChange={(e) => field("services", e.target.value)} placeholder="Separate with commas: AI automation, web development, CRM systems, IT support" /></label>
        <label className="span-2"><span>Qualification keywords</span><textarea rows={3} value={form.keywords} onChange={(e) => field("keywords", e.target.value)} placeholder="Terms that should increase match confidence, separated by commas" /></label>
        <label><span>Minimum preferred contract</span><input type="number" min="0" value={form.preferredContractMin} onChange={(e) => field("preferredContractMin", e.target.value)} placeholder="0" /></label>
        <label><span>Maximum preferred contract</span><input type="number" min="0" value={form.preferredContractMax} onChange={(e) => field("preferredContractMax", e.target.value)} placeholder="No maximum" /></label>
        <label><span>Currency</span><select value={form.currency} onChange={(e) => field("currency", e.target.value)}><option>UGX</option><option>USD</option><option>EUR</option><option>GBP</option></select></label>
        <label><span>Years of experience</span><input type="number" min="0" value={form.yearsExperience} onChange={(e) => field("yearsExperience", e.target.value)} placeholder="0" /></label>
      </div></section>

      <section className="panel suite-form-section"><div className="suite-form-section-head"><span><MapPin size={19} /></span><div><h2>Coverage & contacts</h2><p>Define the places your business can serve and the contacts procurement teams can verify.</p></div></div><div className="suite-form-grid">
        <label className="span-2"><span>Coverage areas</span><textarea rows={3} value={form.coverage} onChange={(e) => field("coverage", e.target.value)} placeholder="e.g. Kampala, Central Uganda, Nationwide, East Africa" /></label>
        <label><span>District / city</span><input value={form.district} onChange={(e) => field("district", e.target.value)} placeholder="Kampala" /></label>
        <label><span>Country</span><input value={form.country} onChange={(e) => field("country", e.target.value)} /></label>
        <label className="span-2"><span>Business address</span><input value={form.address} onChange={(e) => field("address", e.target.value)} placeholder="Office or registered business address" /></label>
        <label><span>Business email</span><input type="email" value={form.email} onChange={(e) => field("email", e.target.value)} placeholder="procurement@company.com" /></label>
        <label><span>Phone</span><input value={form.phone} onChange={(e) => field("phone", e.target.value)} placeholder="+256…" /></label>
        <label className="span-2"><span>Website</span><input value={form.website} onChange={(e) => field("website", e.target.value)} placeholder="https://company.com" /></label>
      </div></section>

      <section className="panel suite-form-section"><div className="suite-form-section-head"><span><ShieldCheck size={19} /></span><div><h2>Experience & compliance</h2><p>Capture evidence that helps Bid Finder distinguish opportunities you can realistically pursue.</p></div></div><div className="suite-form-grid">
        <label className="span-2"><span>Past clients / reference organizations</span><textarea rows={3} value={form.pastClients} onChange={(e) => field("pastClients", e.target.value)} placeholder="Separate client or reference organization names with commas" /></label>
        <label className="span-2"><span>Reference notes</span><textarea rows={3} value={form.referenceNotes} onChange={(e) => field("referenceNotes", e.target.value)} placeholder="Relevant completed projects, contract experience or reference details" /></label>
        <label className="span-2"><span>Certifications</span><textarea rows={2} value={form.certifications} onChange={(e) => field("certifications", e.target.value)} placeholder="ISO, professional certifications, sector licences, manufacturer authorizations…" /></label>
      </div><div className="suite-check-grid">
        <label><input type="checkbox" checked={form.ursbRegistered} onChange={(e) => field("ursbRegistered", e.target.checked)} /><span>URSB registered</span></label>
        <label><input type="checkbox" checked={form.taxClearance} onChange={(e) => field("taxClearance", e.target.checked)} /><span>Valid tax clearance</span></label>
        <label><input type="checkbox" checked={form.ppdaRegistered} onChange={(e) => field("ppdaRegistered", e.target.checked)} /><span>PPDA / supplier registration</span></label>
        <label><input type="checkbox" checked={form.vatRegistered} onChange={(e) => field("vatRegistered", e.target.checked)} /><span>VAT registered</span></label>
      </div></section>

      {error && <div className="suite-form-message error">{error}</div>}
      <div className="suite-form-actions"><span>{hasProfile ? "Changes update your existing company profile." : "This will create your company profile."}</span><button className="button primary" type="submit" disabled={saving}>{saving ? <><Loader2 className="spin" size={15} /> Saving…</> : saved ? <><Check size={15} /> Company saved</> : <><Save size={15} /> Save company profile</>}</button></div>
    </form>
  </div>;
}
