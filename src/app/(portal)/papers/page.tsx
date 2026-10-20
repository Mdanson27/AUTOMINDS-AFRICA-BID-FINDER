"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ExternalLink, Newspaper, RefreshCw, Search } from "lucide-react";
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
  if (!value) return "No successful verification yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 2) return "Checked just now";
  if (minutes < 60) return `Checked ${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `Checked ${hours} hr ago`;
  return `Checked ${Math.round(hours / 24)} days ago`;
}

function countLabel(value?: number | null) {
  return value === null || value === undefined ? "Unknown" : String(value);
}

function collectorTone(source: BidSource) {
  return source.collectorStatus === "HEALTHY" ? "healthy" : "warning";
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
        recordsFound: null,
        collectorStatus: "UNKNOWN",
        captureStatus: "INCOMPLETE",
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
          <p>Only opportunities whose canonical publisher is Daily Monitor or New Vision appear here. Collector failures are shown as failures, never disguised as zero tenders.</p>
        </div>
        <button className="papers-refresh" onClick={refresh} disabled={refreshing}>{refreshing ? <RefreshCw size={15} className="spin" /> : <RefreshCw size={15} />} {refreshing ? "Checking latest…" : "Refresh latest"}</button>
      </section>

      <div className="paper-source-strip">
        {paperSources.map((source) => {
          const healthy = collectorTone(source) === "healthy";
          return (
            <article className="paper-source-card paper-source-health" key={source.name}>
              <span className="paper-source-icon"><Newspaper size={18} /></span>
              <div className="paper-source-health-body">
                <div className="paper-source-title-row">
                  <strong>{source.name}</strong>
                  <span className={`paper-health-badge ${healthy ? "is-healthy" : "is-warning"}`}>{healthy ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}{source.collectorStatus || source.health}</span>
                </div>
                <small>Capture: {source.captureStatus || "UNKNOWN"}</small>
                <small>Direct access: {source.directStatus || (source.httpStatus ? `HTTP ${source.httpStatus}` : "Not reported")}</small>
                <small>Discovery fallback: {source.discoveryStatus || "Not reported"}</small>
                <small>URLs discovered: {countLabel(source.urlsDiscovered)} · fetched: {countLabel(source.urlsSuccessfullyFetched)}</small>
                <small>Verified: {countLabel(source.verifiedRecords)} · review: {countLabel(source.needsReview)}</small>
                <small>Records found: {countLabel(source.recordsFound)} · {relativeTime(source.lastAttemptedCrawlAt || source.lastSuccessfulCrawlAt)}</small>
                {source.captureWarnings?.length ? <small className="paper-health-warning">{source.captureWarnings[0]}</small> : null}
              </div>
              <a href={paperLinks[source.name] || source.baseUrl} target="_blank" rel="noreferrer" aria-label={`Open ${source.name}`}><ExternalLink size={15} /></a>
            </article>
          );
        })}
      </div>

      <label className="paper-searchbar"><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search current paper tenders by title, organization or reference…" /><span>{paperBids.length} found</span></label>
      <div className="paper-result-note">Only direct Daily Monitor / New Vision source matches are shown here. Search-engine discovery may locate an original newspaper URL, but the search engine itself never becomes the source.</div>

      {paperBids.length || loading ? (
        <BidList bids={paperBids} loading={loading} />
      ) : (
        <div className="paper-empty"><Newspaper size={28} /><h3>No verified current-paper bids are available in this snapshot.</h3><p>Check the collector cards above: an empty result set is only a genuine zero when capture completed successfully. BLOCKED, PARTIAL, or INCOMPLETE means the true count is unknown.</p></div>
      )}
    </div>
  );
}
