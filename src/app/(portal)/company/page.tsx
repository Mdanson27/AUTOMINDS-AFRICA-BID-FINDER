import { BriefcaseBusiness, Building2, CheckCircle2, FileBadge2, MapPin, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";

const capabilityGroups = ["Industries & services", "Preferred contract size", "Coverage & locations", "Experience & references", "Compliance documents", "Qualification keywords"];

export default function CompanyPage() {
  return <div className="page-stack suite-company-page"><PageHeader eyebrow="Matching foundation" title="My company" description="Build the company profile that will later power relevance scoring, eligibility checks and tailored opportunity recommendations." />
    <section className="suite-hero suite-company-hero"><span className="eyebrow">COMPANY INTELLIGENCE</span><h2>Your future bid-matching profile starts here.</h2><p>Once the matching engine is connected, Bid Finder will compare opportunity requirements with your services, experience, coverage and compliance profile.</p><div className="suite-company-hero-tags"><span><Sparkles size={14} /> Relevance scoring</span><span><CheckCircle2 size={14} /> Eligibility checks</span><span><FileBadge2 size={14} /> Requirement matching</span></div></section>
    <section className="suite-company-grid"><article><span><Building2 size={20} /></span><div><strong>Company identity</strong><p>Name, registration details, industry and company description.</p></div><em>Profile setup</em></article><article><span><BriefcaseBusiness size={20} /></span><div><strong>Capabilities</strong><p>Products, services, technical strengths and procurement categories.</p></div><em>Profile setup</em></article><article><span><MapPin size={20} /></span><div><strong>Coverage</strong><p>Districts, regions and delivery areas your company can serve.</p></div><em>Profile setup</em></article></section>
    <section className="panel"><div className="suite-section-title"><div><span className="eyebrow">PROFILE STRUCTURE</span><h2>Matching data we will use</h2><p>The structure is prepared now so the later intelligence engine can be added without redesigning this workspace.</p></div></div><div className="suite-capability-list">{capabilityGroups.map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong><em>Coming next</em></div>)}</div></section>
  </div>;
}
