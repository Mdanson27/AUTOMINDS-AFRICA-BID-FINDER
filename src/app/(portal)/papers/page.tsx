"use client";

import { useMemo, useState } from "react";
import { ExternalLink, Newspaper, RefreshCw, Search } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { requestSnapshotRefresh, useBids } from "@/hooks/useBids";
import { useSources } from "@/hooks/useSources";
import type { BidSource } from "@/lib/types";

const paperNames = new Set(["Daily Monitor", "New Vision"]);
const paperLinks: Record<string, string> = {
  "Daily Monitor": "https://www.monitor.co.ug/uganda/jobs/tenders",
  "New Vision": "https://www.newvision.co.ug/opportunities/tenders",
};

function relativeTime(value?: string) {
  if (!value) return "No successful crawl yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 2) return "Checked just now";
  if (minutes < 60) return `Checked ${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Checked ${hours} hr ago`;
  return `Checked ${Math.round(hours / 24)} days ago`;
}

export default function PapersPage() {
  const { bids, loading } = useBids();
  const { sources } = useSources();
  const [query, setQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const paperSources = useMemo<BidSource[]>(() => {
    const existing = sources.filter((source) => source.type === "newspaper" || paperNames.has(source.name));
    const byName = new Map(existing.map((source) => [source.name, source]));
    return ["Daily Monitor", "New Vision"].map((name) => {
      const existingSource = byName.get(name);
      if (existingSource) return existingSource;
      return {
        id: name.toLowerCase().replace(/\s+/g, "-"),
        name,
        type: "newspaper",
        baseUrl: paperLinks[name],
        health: "planned",
        enabled: true,
        recordsFound: 0,
      };
    });
  }, [sources]);

  const paperBids = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return bids.filter((bid) => {
      const actualPaperSource = bid.sources.some((source) => paperNames.has(source.name));
      if (!actualPaperSource) return false;
      if (!needle) return true;
      return [bid.title, bid.organization, bid.referenceNumber, bid.description].join(" ").toLowerCase().includes(needle);
    }).sort((a, b) => new Date(b.firstSeenAt).getTime() - new Date(a.firstSeenAt).getTime());
  }, [bids, query]);

  async function refresh() {
    setRefreshing(true);
    requestSnapshotRefresh();
    await new Promise((resolve) => window.setTimeout(resolve, 700));
    setRefreshing(false);
  }

  return (
    <div className="papers-page page-stack">
      <section className="papers-hero">
        <div>
          <span className="eyebrow">CURRENT PAPERS</span>
          <h1>Search today&apos;s tender pages.</h1>
          <p>Focus only on opportunities detected directly from Uganda&apos;s major newspaper tender channels. Bid Finder keeps the source identity strict, so an eGP notice containing the word “newspaper” will never be misclassified as a newspaper result.</p>
        </div>
        <button className="papers-refresh" onClick={refresh} disabled={refreshing}>{refreshing ? <RefreshCw size={15} className="spin" /> : <RefreshCw size={15} />} {refreshing ? "Checking latest…" : "Refresh latest"}</button>
      </section>

      <div className="paper-source-strip">
        {paperSources.map((source) => (
          <article className="paper-source-card" key={source.name}>
            <span className="paper-source-icon"><Newspaper size={18} /></span>
            <div><strong>{source.name}</strong><small>{source.health} · {source.recordsFound || 0} notices · {relativeTime(source.lastAttemptedCrawlAt || source.lastSuccessfulCrawlAt)}</small></div>
            <a href={paperLinks[source.name] || source.baseUrl} target="_blank" rel="noreferrer" aria-label={`Open ${source.name}`}><ExternalLink size={15} /></a>
          </article>
        ))}
      </div>

      <label className="paper-searchbar"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search current paper tenders by title, organization or reference…" /><span>{paperBids.length} found</span></label>
      <div className="paper-result-note">Only direct Daily Monitor / New Vision source matches are shown here. Background collection still respects the 2026/27 financial-year and 90-day deadline rules.</div>

      {paperBids.length || loading ? (
        <BidList bids={paperBids} loading={loading} />
      ) : (
        <div className="paper-empty"><Newspaper size={28} /><h3>No directly indexed current-paper bids are available in this snapshot.</h3><p>The newspaper pages are still available through the official links above. If a publisher blocks automated collection or renders notices dynamically, Bid Finder reports that source honestly instead of filling this page with unrelated eGP or development notices.</p></div>
      )}
    </div>
  );
}
