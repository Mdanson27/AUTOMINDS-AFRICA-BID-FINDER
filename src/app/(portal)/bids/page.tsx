"use client";

import { useEffect, useMemo, useState } from "react";
import { Building2, CalendarRange, Check, ChevronDown, Globe2, Landmark, Newspaper, Search, SlidersHorizontal, UsersRound } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";
import { daysUntil } from "@/lib/date";

const catalog = ["eGP Uganda", "GPP / PPDA", "NITA-U", "KCCA", "URA", "UCC", "Ministry of Finance", "Daily Monitor", "New Vision", "World Bank Uganda", "UN / Development Partners"];
const scopes = [
  { id: "all", label: "Everywhere", icon: Globe2, patterns: [] as string[] },
  { id: "government", label: "Government", icon: Landmark, patterns: ["egp", "ppda", "gpp", "ura", "kcca", "nita", "unra", "ucc", "nwsc", "ministry", "finance", "mofped"] },
  { id: "newspapers", label: "Newspapers", icon: Newspaper, patterns: ["monitor", "new vision", "newspaper"] },
  { id: "development", label: "NGO & Development", icon: UsersRound, patterns: ["un ", "ungm", "giz", "enabel", "usaid", "ngo", "development", "world bank"] },
  { id: "private", label: "Private sector", icon: Building2, patterns: ["private", "company", "bank", "telecom"] },
] as const;

const statusRank: Record<string, number> = {
  open: 0,
  planned: 1,
  evaluation: 2,
  awarded: 3,
  closed: 4,
  cancelled: 5,
};

export default function BidsPage() {
  const { bids, loading, error } = useBids();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [category, setCategory] = useState("all");
  const [source, setSource] = useState("all");
  const [scope, setScope] = useState("all");
  const [customOpen, setCustomOpen] = useState(false);
  const [customSources, setCustomSources] = useState<string[]>([]);
  const [advanced, setAdvanced] = useState(false);
  const [organization, setOrganization] = useState("");
  const [procurementType, setProcurementType] = useState("all");
  const [deadlineWindow, setDeadlineWindow] = useState("all");
  const [sort, setSort] = useState("deadline");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q"); const requestedScope = params.get("scope");
    if (q) setSearch(q);
    if (requestedScope && scopes.some((item) => item.id === requestedScope)) setScope(requestedScope);
  }, []);

  const categories = useMemo(() => [...new Set(bids.map((b) => b.category).filter(Boolean))].sort(), [bids]);
  const sources = useMemo(() => [...new Set(bids.flatMap((b) => b.sources.map((s) => s.name)))].sort(), [bids]);
  const procurementTypes = useMemo(() => [...new Set(bids.map((b) => b.procurementType).filter(Boolean))].sort(), [bids]);
  const sourceChoices = useMemo(() => [...new Set([...catalog, ...sources])], [sources]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const orgNeedle = organization.trim().toLowerCase();
    const selectedScope = scopes.find((item) => item.id === scope);
    const result = bids.filter((bid) => {
      const text = [bid.title, bid.organization, bid.referenceNumber, bid.description, bid.category, bid.procurementType].join(" ").toLowerCase();
      const names = bid.sources.map((item) => item.name.toLowerCase());
      const matchesText = !needle || text.includes(needle);
      const matchesStatus = status === "all" || bid.status === status;
      const matchesCategory = category === "all" || bid.category === category;
      const matchesSource = source === "all" || bid.sources.some((item) => item.name === source);
      const matchesOrg = !orgNeedle || bid.organization.toLowerCase().includes(orgNeedle);
      const matchesType = procurementType === "all" || bid.procurementType === procurementType;
      const days = daysUntil(bid.deadlineAt);
      const matchesDeadline = deadlineWindow === "all" || (days >= 0 && days <= Number(deadlineWindow));
      const matchesScope = scope === "all" || scope === "custom"
        ? scope !== "custom" || customSources.length === 0 || bid.sources.some((item) => customSources.includes(item.name))
        : Boolean(selectedScope?.patterns.some((pattern) => names.some((name) => name.includes(pattern)) || text.includes(pattern)));
      return matchesText && matchesStatus && matchesCategory && matchesSource && matchesOrg && matchesType && matchesDeadline && matchesScope;
    });
    return [...result].sort((a, b) => {
      const statusDifference = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
      if (statusDifference !== 0) return statusDifference;
      if (sort === "organization") return a.organization.localeCompare(b.organization);
      if (sort === "newest") return new Date(b.firstSeenAt).getTime() - new Date(a.firstSeenAt).getTime();
      const aDeadline = a.deadlineAt ? new Date(a.deadlineAt).getTime() : Number.POSITIVE_INFINITY;
      const bDeadline = b.deadlineAt ? new Date(b.deadlineAt).getTime() : Number.POSITIVE_INFINITY;
      return aDeadline - bDeadline;
    });
  }, [bids, category, customSources, deadlineWindow, organization, procurementType, scope, search, sort, source, status]);

  function toggleCustom(name: string) { setCustomSources((items) => items.includes(name) ? items.filter((item) => item !== name) : [...items, name]); setScope("custom"); }
  function reset() { setSearch(""); setStatus("all"); setCategory("all"); setSource("all"); setScope("all"); setOrganization(""); setProcurementType("all"); setDeadlineWindow("all"); setCustomSources([]); }

  return (
    <div className="page-stack suite-find-page">
      <PageHeader eyebrow="Opportunity search" title="Find bids" description="Choose where to search, describe what you need and narrow the results without jumping between portals or publications." />

      <section className="panel suite-search-console">
        <div className="suite-search-question"><div><span className="eyebrow">SEARCH COVERAGE</span><h2>Where should we search?</h2><p>Search everything at once or focus on a specific part of the procurement landscape.</p></div><button className="button secondary" onClick={() => setCustomOpen((value) => !value)}>Choose sources <ChevronDown size={15} /></button></div>
        <div className="suite-scope-tabs">{scopes.map(({ id, label, icon: Icon }) => <button className={scope === id ? "active" : ""} onClick={() => setScope(id)} key={id}><Icon size={17} /><span>{label}</span></button>)}</div>
        {customOpen && <div className="suite-custom-sources"><div className="suite-custom-source-head"><strong>Choose individual sources</strong><span>{customSources.length ? `${customSources.length} selected` : "Select one or more, or leave empty to search all."}</span></div><div className="suite-source-checks">{sourceChoices.map((name) => <button key={name} className={customSources.includes(name) ? "selected" : ""} onClick={() => toggleCustom(name)}><span className="source-check-mark">{customSources.includes(name) && <Check size={13} />}</span>{name}</button>)}</div></div>}

        <label className="suite-main-search"><Search size={21} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title, organization, procurement reference, service or keyword…" /><span>{filtered.length} result{filtered.length === 1 ? "" : "s"}</span></label>

        <div className="suite-filter-bar">
          <span className="filter-label"><SlidersHorizontal size={16} /> Filters</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="all">All statuses</option><option value="open">Open</option><option value="planned">Planned</option><option value="evaluation">Evaluation</option><option value="awarded">Awarded</option><option value="closed">Closed</option><option value="cancelled">Cancelled</option></select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category"><option value="all">All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select>
          <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source"><option value="all">All detected sources</option>{sources.map((item) => <option key={item}>{item}</option>)}</select>
          <button className={`suite-advanced-toggle ${advanced ? "active" : ""}`} onClick={() => setAdvanced((value) => !value)}><CalendarRange size={15} /> Advanced</button>
          <button className="suite-reset" onClick={reset}>Reset</button>
        </div>

        {advanced && <div className="suite-advanced-grid"><label><span>Organization</span><input value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder="e.g. KCCA" /></label><label><span>Procurement type</span><select value={procurementType} onChange={(e) => setProcurementType(e.target.value)}><option value="all">Any type</option>{procurementTypes.map((item) => <option key={item}>{item}</option>)}</select></label><label><span>Deadline within</span><select value={deadlineWindow} onChange={(e) => setDeadlineWindow(e.target.value)}><option value="all">Any time</option><option value="3">3 days</option><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option></select></label></div>}
      </section>

      <section className="suite-results-section">
        <div className="suite-results-head"><div><span className="eyebrow">SEARCH RESULTS</span><h2>{scope === "all" ? "All matching opportunities" : scope === "custom" ? "Selected-source results" : `${scopes.find((item) => item.id === scope)?.label} opportunities`}</h2></div><label className="suite-sort">Sort by <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="deadline">Nearest deadline</option><option value="newest">Newest discovered</option><option value="organization">Organization</option></select></label></div>
        {error ? <div className="suite-empty"><strong>Search data is temporarily unavailable</strong><span>{error}</span></div> : <BidList bids={filtered} loading={loading} />}
      </section>
    </div>
  );
}
