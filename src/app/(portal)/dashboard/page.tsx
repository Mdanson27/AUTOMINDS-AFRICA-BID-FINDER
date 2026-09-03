"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Bookmark, CalendarClock, FileSearch, Globe2, RadioTower, Search, Sparkles } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { useBids } from "@/hooks/useBids";
import { useSavedBids } from "@/hooks/useSavedBids";
import { useSources } from "@/hooks/useSources";
import { daysUntil, isSameLocalDay } from "@/lib/date";

const quickSearches = ["ICT", "Construction", "Consultancy", "Supplies", "Agriculture", "Security"];

export default function DashboardPage() {
  const router = useRouter();
  const { bids, loading, error } = useBids();
  const { savedIds } = useSavedBids();
  const { sources } = useSources();
  const [search, setSearch] = useState("");
  const now = new Date();
  const open = bids.filter((bid) => bid.status === "open" && daysUntil(bid.deadlineAt) >= 0);
  const newToday = bids.filter((bid) => isSameLocalDay(bid.firstSeenAt, now));
  const closing = open.filter((bid) => daysUntil(bid.deadlineAt) <= 7).sort((a, b) => daysUntil(a.deadlineAt) - daysUntil(b.deadlineAt));
  const healthySources = sources.filter((source) => source.health === "healthy" && source.enabled).length;

  function runSearch(event: React.FormEvent) {
    event.preventDefault();
    const value = search.trim();
    router.push(value ? `/bids?q=${encodeURIComponent(value)}` : "/bids");
  }

  return (
    <div className="page-stack suite-dashboard">
      <PageHeader
        eyebrow="Procurement intelligence"
        title="Your opportunity desk"
        description="Search Uganda’s procurement landscape, follow deadlines and keep the opportunities worth pursuing in one place."
        action={<Link href="/bids" className="button primary">Explore all bids <ArrowRight size={16} /></Link>}
      />

      <section className="suite-hero dashboard-search-hero">
        <span className="eyebrow">START A SEARCH</span>
        <h2>What opportunity are you looking for today?</h2>
        <p>Run one search across every connected source, or narrow the search to government portals, newspapers, development partners or private organizations.</p>
        <form className="suite-hero-search" onSubmit={runSearch}>
          <label><Search size={19} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Try ‘software development’, ‘stationery’ or an organization name…" /></label>
          <button><Sparkles size={17} /> Search opportunities</button>
        </form>
        <div className="suite-quick-chips">{quickSearches.map((item) => <button key={item} onClick={() => router.push(`/bids?q=${encodeURIComponent(item)}`)}>{item}</button>)}</div>
      </section>

      <section className="stats-grid suite-stats" aria-label="Bid summary">
        <StatCard label="Open opportunities" value={loading ? "—" : open.length} icon={<FileSearch />} hint="Active bids you can still act on" />
        <StatCard label="New today" value={loading ? "—" : newToday.length} icon={<RadioTower />} hint="First discovered today" />
        <StatCard label="Closing this week" value={loading ? "—" : closing.length} icon={<CalendarClock />} hint="Needs attention soon" />
        <StatCard label="Saved bids" value={savedIds.size} icon={<Bookmark />} hint="Your current watchlist" />
      </section>

      <div className="suite-dashboard-grid">
        <section className="panel suite-priority-panel">
          <div className="suite-section-title"><div><span className="eyebrow">PRIORITY QUEUE</span><h2>Closing soon</h2><p>Open opportunities with the nearest deadlines.</p></div><Link href="/closing-soon" className="text-link">View all <ArrowRight size={15} /></Link></div>
          {error ? <div className="suite-empty"><strong>Opportunity data is temporarily unavailable</strong><span>{error}</span></div> : !loading && closing.length === 0 ? <div className="suite-empty"><CalendarClock size={24} /><strong>No urgent deadlines yet</strong><span>As live sources begin feeding the workspace, time-sensitive opportunities will surface here automatically.</span></div> : <BidList bids={closing.slice(0, 5)} loading={loading} compact />}
        </section>

        <aside className="panel suite-source-pulse">
          <div className="suite-section-title"><div><span className="eyebrow">SOURCE NETWORK</span><h2>Collection readiness</h2><p>Your discovery coverage at a glance.</p></div></div>
          <div className="source-pulse-metric"><span className="source-pulse-icon"><Globe2 size={19} /></span><div><strong>{healthySources || 0}</strong><span>sources reporting healthy</span></div></div>
          <div className="suite-source-groups">
            <Link href="/bids?scope=government"><span>Government</span><small>eGP · PPDA · agencies</small></Link>
            <Link href="/bids?scope=newspapers"><span>Newspapers</span><small>Monitor · New Vision</small></Link>
            <Link href="/bids?scope=development"><span>Development</span><small>NGOs · UN · partners</small></Link>
            <Link href="/bids?scope=private"><span>Private sector</span><small>Companies · institutions</small></Link>
          </div>
          <Link href="/sources" className="suite-source-link">Manage search sources <ArrowRight size={14} /></Link>
        </aside>
      </div>
    </div>
  );
}
