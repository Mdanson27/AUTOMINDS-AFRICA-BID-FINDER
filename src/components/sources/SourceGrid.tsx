import { AlertTriangle, CheckCircle2, Clock3, Globe2, PauseCircle } from "lucide-react";
import type { BidSource } from "@/lib/types";
import { formatDate } from "@/lib/date";

const icons = { healthy: CheckCircle2, warning: AlertTriangle, paused: PauseCircle, planned: Clock3 };
export function SourceGrid({ sources, loading, admin = false }: { sources: BidSource[]; loading?: boolean; admin?: boolean }) {
  if (loading) return <div className="source-grid"><div className="source-card skeleton-block" /><div className="source-card skeleton-block" /></div>;
  if (!sources.length) return <div className="panel empty-state"><span className="empty-icon"><Globe2 size={24} /></span><h3>No source records yet</h3><p>Create source records in Firestore as each collector is connected. Recommended first adapters: eGP Uganda, GPP/PPDA, Daily Monitor and New Vision.</p></div>;
  return <div className="source-grid">{sources.map((source) => { const Icon = icons[source.health] || Clock3; return <article className="source-card" key={source.id}><div className="source-card-head"><span className={`source-health health-${source.health}`}><Icon size={17} /></span><span className="source-type">{source.type}</span></div><h3>{source.name}</h3><a href={source.baseUrl} target="_blank" rel="noreferrer">{source.baseUrl.replace(/^https?:\/\//, "")}</a><div className="source-metrics"><div><span>Last success</span><strong>{source.lastSuccessfulCrawlAt ? formatDate(source.lastSuccessfulCrawlAt, true) : "Not yet"}</strong></div><div><span>Records</span><strong>{source.recordsFound ?? 0}</strong></div></div>{admin && <p className="source-note">{source.health === "planned" ? "Adapter not connected yet." : source.lastError || "Collector is reporting normally."}</p>}</article>; })}</div>;
}
