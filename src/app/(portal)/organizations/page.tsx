"use client";

import { useMemo, useState } from "react";
import { Building2, Search } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";

export default function OrganizationsPage() {
  const { bids, loading } = useBids();
  const [search, setSearch] = useState("");
  const rows = useMemo(() => {
    const map = new Map<string, { total: number; open: number; categories: Set<string> }>();
    bids.forEach((bid) => { const current = map.get(bid.organization) || { total: 0, open: 0, categories: new Set<string>() }; current.total += 1; if (bid.status === "open") current.open += 1; if (bid.category) current.categories.add(bid.category); map.set(bid.organization, current); });
    const needle = search.trim().toLowerCase();
    return [...map.entries()].filter(([name]) => !needle || name.toLowerCase().includes(needle)).sort((a, b) => b[1].total - a[1].total);
  }, [bids, search]);

  return (
    <div className="page-stack suite-organizations-page">
      <PageHeader eyebrow="Market map" title="Organizations" description="Explore procuring entities discovered across connected sources and see where opportunities are coming from." />
      <section className="panel suite-org-toolbar"><label><Search size={17} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search organizations…" /></label><span>{rows.length} organization{rows.length === 1 ? "" : "s"}</span></section>
      {loading ? <div className="suite-organization-grid"><div className="organization-card skeleton-block" /><div className="organization-card skeleton-block" /><div className="organization-card skeleton-block" /></div> : rows.length === 0 ? <div className="suite-empty"><Building2 size={26} /><strong>No organizations discovered yet</strong><span>As live bid notices enter the workspace, procuring entities will automatically build into an organization directory here.</span></div> : <div className="suite-organization-grid">{rows.map(([name, data]) => <article className="suite-organization-card" key={name}><span className="suite-org-icon"><Building2 size={20} /></span><div className="suite-org-main"><strong>{name}</strong><small>{data.total} opportunity{data.total === 1 ? "" : "ies"} discovered</small><div>{[...data.categories].slice(0, 3).map((item) => <span key={item}>{item}</span>)}</div></div><div className="suite-org-count"><strong>{data.open}</strong><span>open</span></div></article>)}</div>}
    </div>
  );
}
