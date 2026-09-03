"use client";

import { useMemo, useState } from "react";
import { ExternalLink, Globe2, Landmark, Newspaper, Radar, RefreshCw, SearchCheck, UsersRound } from "lucide-react";
import { useBids, requestSnapshotRefresh } from "@/hooks/useBids";
import { useSources } from "@/hooks/useSources";
import { auth } from "@/lib/firebase";

const scanApiUrl = process.env.NEXT_PUBLIC_SCAN_API_URL || "";

const modes = [
  { id: "all", label: "Everywhere", description: "Government, newspapers and development sources", icon: Globe2 },
  { id: "government", label: "Government", description: "eGP, PPDA and public institutions", icon: Landmark },
  { id: "newspaper", label: "Current papers", description: "Daily Monitor and New Vision tender notices", icon: Newspaper },
  { id: "development", label: "Development", description: "World Bank, UN and development partners", icon: UsersRound },
  { id: "custom", label: "Choose sources", description: "Run a focused source-by-source check", icon: SearchCheck },
] as const;

type Mode = typeof modes[number]["id"];

function relativeTime(value?: string) {
  if (!value) return "Never checked";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 2) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export default function ScanPage() {
  const { bids } = useBids();
  const { sources, loading } = useSources();
  const [mode, setMode] = useState<Mode>("all");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState("");

  const healthy = sources.filter((source) => source.health === "healthy").length;
  const warning = sources.filter((source) => source.health === "warning").length;
  const newspaperSources = sources.filter((source) => source.type === "newspaper");
  const newestCheck = useMemo(() => {
    const times = sources.map((source) => source.lastAttemptedCrawlAt || "").filter(Boolean).sort();
    return times.length ? times[times.length - 1] : "";
  }, [sources]);

  const visibleSources = useMemo(() => {
    if (mode === "all" || mode === "custom") return sources;
    if (mode === "newspaper") return sources.filter((source) => source.type === "newspaper");
    if (mode === "development") return sources.filter((source) => source.type === "development");
    return sources.filter((source) => source.type === "government");
  }, [mode, sources]);

  function toggleSource(id: string) {
    setSelectedIds((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
    setMode("custom");
  }

  async function runScan() {
    setScanning(true);
    setMessage("");
    const sourceIds = mode === "custom" && selectedIds.length ? selectedIds : visibleSources.map((source) => source.id);

    try {
      if (scanApiUrl) {
        const token = await auth.currentUser?.getIdToken();
        const response = await fetch(scanApiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ mode, sourceIds, scanType: "quick" }),
        });
        if (!response.ok) throw new Error(`Live scanner returned ${response.status}`);
        const result = await response.json().catch(() => ({}));
        requestSnapshotRefresh();
        setMessage(result?.message || "Live source scan started. Newly discovered opportunities will appear as the scan completes.");
      } else {
        requestSnapshotRefresh();
        await new Promise((resolve) => window.setTimeout(resolve, 650));
        setMessage("Latest published procurement snapshot checked. Background source collectors refresh every two hours; the instant server scan endpoint is ready to connect when the scanner service is deployed.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The scan could not be started.");
    } finally {
      setScanning(false);
    }
  }

  return (
    <div className="scan-center-page page-stack">
      <section className="scan-hero">
        <div>
          <span className="eyebrow">LIVE DISCOVERY</span>
          <h1>Scan Uganda&apos;s procurement landscape.</h1>
          <p>Check the newest public opportunities across government portals, current newspaper tender pages and development partners. Select exactly where Bid Finder should look, then refresh the latest intelligence in one workspace.</p>
        </div>
        <div className="scan-hero-state">
          <strong>{bids.length}</strong>
          <span>eligible opportunities in the current search window</span>
          <small>{healthy} live source{healthy === 1 ? "" : "s"} reporting healthy</small>
        </div>
      </section>

      <div className="scan-workspace">
        <div className="scan-main">
          <section className="scan-section">
            <div className="scan-section-head">
              <div><h2>Where should we scan?</h2><p>Use a broad scan or focus on a specific procurement channel.</p></div>
            </div>
            <div className="scan-mode-grid">
              {modes.map(({ id, label, description, icon: Icon }) => (
                <button key={id} className={`scan-mode ${mode === id ? "active" : ""}`} onClick={() => setMode(id)}>
                  <Icon size={19} /><strong>{label}</strong><span>{description}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="scan-section">
            <div className="scan-section-head">
              <div><h2>Source selection</h2><p>Health and last-check information come from the live collection network.</p></div>
              <span className="enrichment-badge"><Radar size={14} /> {visibleSources.length} available</span>
            </div>
            <div className="scan-source-list">
              {loading ? <div className="premium-loading-card" /> : visibleSources.map((source) => (
                <label className="scan-source-row" key={source.id}>
                  <input
                    type="checkbox"
                    checked={mode !== "custom" || selectedIds.length === 0 ? true : selectedIds.includes(source.id)}
                    onChange={() => toggleSource(source.id)}
                  />
                  <span>
                    <strong>{source.name}</strong>
                    <small>{source.recordsFound || 0} notices seen · checked {relativeTime(source.lastAttemptedCrawlAt)}</small>
                  </span>
                  <span className={`scan-health ${source.health}`}>{source.health}</span>
                </label>
              ))}
            </div>
            <div className="scan-run-bar">
              <button className="scan-run-button" onClick={runScan} disabled={scanning || loading}>
                {scanning ? <RefreshCw size={16} className="spin" /> : <Radar size={16} />}
                {scanning ? "Checking sources…" : "Scan newest bids"}
              </button>
              <span className="scan-run-note">Background refresh: every 2 hours · Last network check: {relativeTime(newestCheck)}</span>
            </div>
            {message && <div className="scan-result">{message}</div>}
          </section>
        </div>

        <aside className="scan-side">
          <section className="scan-section">
            <div className="scan-section-head"><div><h2>Network readiness</h2><p>Only sources that actually respond are treated as healthy.</p></div></div>
            <div className="scan-side-stat-grid">
              <div className="scan-side-stat"><strong>{healthy}</strong><span>Healthy sources</span></div>
              <div className="scan-side-stat"><strong>{warning}</strong><span>Need attention</span></div>
              <div className="scan-side-stat"><strong>{newspaperSources.length}</strong><span>Paper sources</span></div>
              <div className="scan-side-stat"><strong>90d</strong><span>Maximum deadline window</span></div>
            </div>
          </section>

          <section className="scan-section">
            <div className="scan-section-head"><div><h2>Current papers</h2><p>Jump directly to the latest official tender pages.</p></div></div>
            <div className="scan-paper-links">
              <a className="scan-paper-link" href="https://www.monitor.co.ug/uganda/jobs/tenders" target="_blank" rel="noreferrer"><Newspaper size={18} /><span><strong>Daily Monitor tenders</strong><span>Official current tender page</span></span><ExternalLink size={14} /></a>
              <a className="scan-paper-link" href="https://www.newvision.co.ug/opportunities/tenders" target="_blank" rel="noreferrer"><Newspaper size={18} /><span><strong>New Vision tenders</strong><span>Official opportunities page</span></span><ExternalLink size={14} /></a>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
