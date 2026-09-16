"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { Building2, Check, ChevronDown, CircleCheckBig, Globe2, Landmark, Newspaper, Radar, Search, SlidersHorizontal, UsersRound } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";
import { daysUntil } from "@/lib/date";

const catalog = ["eGP Uganda", "GPP / PPDA", "NITA-U", "KCCA", "URA", "UCC", "Ministry of Finance", "Daily Monitor", "New Vision", "World Bank Uganda", "UNDP / UNCDF Uganda", "African Development Bank Uganda"];
const scopes = [
  { id: "all", label: "Everywhere", icon: Globe2, sourcePatterns: [] as string[] },
  { id: "government", label: "Government", icon: Landmark, sourcePatterns: ["egp", "ppda", "gpp", "ura", "kcca", "nita", "unra", "ucc", "nwsc", "ministry", "finance", "mofped"] },
  { id: "newspapers", label: "Newspapers", icon: Newspaper, sourcePatterns: ["daily monitor", "new vision"] },
  { id: "development", label: "NGO & Development", icon: UsersRound, sourcePatterns: ["ungm", "undp", "uncdf", "afdb", "african development bank", "giz", "enabel", "usaid", "world bank"] },
  { id: "private", label: "Private sector", icon: Building2, sourcePatterns: ["private", "company", "bank", "telecom"] },
] as const;

const statusRank: Record<string, number> = { open: 0, planned: 1, evaluation: 2, awarded: 3, closed: 4, cancelled: 5 };

function sourceMatchesScope(names: string[], scopeId: string) {
  if (scopeId === "all") return true;
  const scope = scopes.find((item) => item.id === scopeId);
  if (!scope) return false;
  return scope.sourcePatterns.some((pattern) => names.some((name) => name.includes(pattern)));
}

export default function BidsPage() {
  const { bids, loading, error } = useBids();
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [activeOnly, setActiveOnly] = useState(true);
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
    const q = params.get("q");
    const requestedScope = params.get("scope");
    if (q) setSearch(q);
    if (requestedScope && scopes.some((item) => item.id === requestedScope)) setScope(requestedScope);
  }, []);

  const categories = useMemo(() => [...new Set(bids.map((b) => b.category).filter(Boolean))].sort(), [bids]);
  const sources = useMemo(() => [...new Set(bids.flatMap((b) => b.sources.map((s) => s.name)))].sort(), [bids]);
  const procurementTypes = useMemo(() => [...new Set(bids.map((b) => b.procurementType).filter(Boolean))].sort(), [bids]);
  const sourceChoices = useMemo(() => [...new Set([...catalog, ...sources])], [sources]);

  const indexedBids = useMemo(() => bids.map((bid) => ({
    bid,
    text: [bid.title, bid.organization, bid.referenceNumber, bid.description, bid.category, bid.procurementType, bid.noticeType, ...bid.sources.map((item) => item.name)].join(" ").toLowerCase(),
    sourceNames: bid.sources.map((item) => item.name.toLowerCase()),
  })), [bids]);

  const filtered = useMemo(() => {
    const needle = deferredSearch.trim().toLowerCase();
    const orgNeedle = organization.trim().toLowerCase();
    const result = indexedBids.filter(({ bid, text, sourceNames }) => {
      if (activeOnly && !bid.isOpen) return false;
      if (needle && !text.includes(needle)) return false;
      if (status !== "all" && bid.status !== status) return false;
      if (category !== "all" && bid.category !== category) return false;
      if (source !== "all" && !bid.sources.some((item) => item.name === source)) return false;
      if (orgNeedle && !bid.organization.toLowerCase().includes(orgNeedle)) return false;
      if (procurementType !== "all" && bid.procurementType !== procurementType) return false;
      const days = daysUntil(bid.deadlineAt);
      if (deadlineWindow !== "all" && !(days >= 0 && days <= Number(deadlineWindow))) return false;
      if (scope === "custom") {
        if (customSources.length && !bid.sources.some((item) => customSources.includes(item.name))) return false;
      } else if (!sourceMatchesScope(sourceNames, scope)) return false;
      return true;
    }).map(({ bid }) => bid);

    return [...result].sort((a, b) => {
      const statusDifference = (statusRank[a.status] ?? 9) - (statusRank[b.status] ?? 9);
      if (statusDifference !== 0) return statusDifference;
      if (sort === "organization") return a.organization.localeCompare(b.organization);
      if (sort === "newest") return new Date(b.firstSeenAt).getTime() - new Date(a.firstSeenAt).getTime();
      const aDeadline = a.deadlineAt ? new Date(a.deadlineAt).getTime() : Number.POSITIVE_INFINITY;
      const bDeadline = b.deadlineAt ? new Date(b.deadlineAt).getTime() : Number.POSITIVE_INFINITY;
      return aDeadline - bDeadline;
    });
  }, [activeOnly, category, customSources, deadlineWindow, deferredSearch, indexedBids, organization, procurementType, scope, sort, source, status]);

  const activeCount = useMemo(() => bids.filter((bid) => bid.isOpen).length, [bids]);

  function toggleCustom(name: string) {
    setCustomSources((items) => items.includes(name) ? items.filter((item) => item !== name) : [...items, name]);
    setScope("custom");
  }

  function reset() {
    setSearch(""); setActiveOnly(true); setStatus("all"); setCategory("all"); setSource("all"); setScope("all");
    setOrganization(""); setProcurementType("all"); setDeadlineWindow("all"); setCustomSources([]);
  }

  return (
    <div className="page-stack suite-find-page">
      <PageHeader
        eyebrow="Procurement search"
        title="Find bids"
        description="Search procurement notices and tender opportunities. Grants are kept in the separate Grants section. Closed bids remain visible for up to 3 days, then disappear automatically."
        action={<Link href="/scan" className="button primary"><Radar size={15} /> Scan newest</Link>}
      />

      <section className="panel suite-search-console">
        <label className="suite-main-search"><Search size={21} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title, organization, reference, service or requirement…" /><span>{filtered.length} result{filtered.length === 1 ? "" : "s"}</span></label>

        <div className="suite-filter-bar" aria-label="Quick filters">
          <button className={activeOnly ? "button primary" : "button secondary"} onClick={() => setActiveOnly((value) => !value)}><CircleCheckBig size={15} /> Active only ({activeCount})</button>
          <button className="suite-advanced-toggle" onClick={() => setAdvanced((value) => !value)}><SlidersHorizontal size={15} /> More filters</button>
          <button className="suite-reset" onClick={reset}>Reset</button>
        </div>

        <div className="suite-search-question">
          <div><span className="eyebrow">SEARCH COVERAGE</span><h2>Where should we search?</h2><p>Use one broad channel or choose individual procurement sources when you need to narrow the results.</p></div>
          <button className="button secondary" onClick={() => setCustomOpen((value) => !value)}>Choose sources <ChevronDown size={15} /></button>
        </div>
        <div className="suite-scope-tabs">{scopes.map(({ id, label, icon: Icon }) => <button className={scope === id ? "active" : ""} onClick={() => setScope(id)} key={id}><Icon size={17} /><span>{label}</span></button>)}</div>
        {customOpen && <div className="suite-custom-sources"><div className="suite-custom-source-head"><strong>Choose individual sources</strong><span>{customSources.length ? `${customSources.length} selected` : "Select one or more, or leave empty to search all."}</span></div><div className="suite-source-checks">{sourceChoices.map((name) => <button key={name} className={customSources.includes(name) ? "selected" : ""} onClick={() => toggleCustom(name)}><span className="source-check-mark">{customSources.includes(name) && <Check size={13} />}</span>{name}</button>)}</div></div>}

        {advanced && <div className="suite-advanced-grid">
          <label><span>Status</span><select value={status} onChange={(e) => { setStatus(e.target.value); if (e.target.value === "closed") setActiveOnly(false); }}><option value="all">Any status</option><option value="open">Open</option><option value="planned">Planned</option><option value="evaluation">Evaluation</option><option value="awarded">Awarded</option><option value="closed">Closed — last 3 days</option><option value="cancelled">Cancelled</option></select></label>
          <label><span>Category</span><select value={category} onChange={(e) => setCategory(e.target.value)}><option value="all">All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>Source</span><select value={source} onChange={(e) => setSource(e.target.value)}><option value="all">All detected sources</option>{sources.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>Organization</span><input value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder="e.g. KCCA" /></label>
          <label><span>Procurement type</span><select value={procurementType} onChange={(e) => setProcurementType(e.target.value)}><option value="all">Any type</option>{procurementTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>Deadline within</span><select value={deadlineWindow} onChange={(e) => setDeadlineWindow(e.target.value)}><option value="all">Any time</option><option value="3">3 days</option><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option><option value="60">60 days</option><option value="90">90 days</option></select></label>
        </div>}
      </section>

      <section className="suite-results-section">
        <div className="suite-results-head"><div><span className="eyebrow">SEARCH RESULTS</span><h2>{activeOnly ? "Active bids" : "All recent bids"}</h2></div><label className="suite-sort">Sort by <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="deadline">Nearest deadline</option><option value="newest">Newest discovered</option><option value="organization">Organization</option></select></label></div>
        {error ? <div className="suite-empty"><strong>Search data is temporarily unavailable</strong><span>{error}</span></div> : <BidList bids={filtered} loading={loading} />}
      </section>
    </div>
  );
}
