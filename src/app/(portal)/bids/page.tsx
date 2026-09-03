"use client";

import { useMemo, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";

export default function BidsPage() {
  const { bids, loading, error } = useBids();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [category, setCategory] = useState("all");
  const [source, setSource] = useState("all");

  const categories = useMemo(() => [...new Set(bids.map((b) => b.category).filter(Boolean))].sort(), [bids]);
  const sources = useMemo(() => [...new Set(bids.flatMap((b) => b.sources.map((s) => s.name)))].sort(), [bids]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return bids.filter((bid) => {
      const matchesText = !needle || [bid.title, bid.organization, bid.referenceNumber, bid.description]
        .join(" ")
        .toLowerCase()
        .includes(needle);
      const matchesStatus = status === "all" || bid.status === status;
      const matchesCategory = category === "all" || bid.category === category;
      const matchesSource = source === "all" || bid.sources.some((item) => item.name === source);
      return matchesText && matchesStatus && matchesCategory && matchesSource;
    });
  }, [bids, category, search, source, status]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Opportunity search"
        title="Find bids"
        description="Search normalized procurement opportunities from every connected source."
      />

      <section className="filter-panel">
        <label className="search-box">
          <Search size={18} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search title, organization or reference…" />
        </label>
        <div className="filter-row">
          <span className="filter-label"><SlidersHorizontal size={16} /> Filters</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
            <option value="all">All statuses</option><option value="open">Open</option><option value="planned">Planned</option><option value="evaluation">Evaluation</option><option value="awarded">Awarded</option><option value="closed">Closed</option><option value="cancelled">Cancelled</option>
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
            <option value="all">All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}
          </select>
          <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
            <option value="all">All sources</option>{sources.map((item) => <option key={item}>{item}</option>)}
          </select>
          <span className="result-count">{filtered.length} result{filtered.length === 1 ? "" : "s"}</span>
        </div>
      </section>

      {error ? <EmptyState title="Could not load bids" description={error} /> : <BidList bids={filtered} loading={loading} />}
    </div>
  );
}
