import { AlertTriangle, CheckCircle2, Clock3, Globe2, Newspaper, PauseCircle, ShieldCheck, UsersRound } from "lucide-react";
import type { BidSource } from "@/lib/types";
import { formatDate } from "@/lib/date";

const icons = { healthy: CheckCircle2, warning: AlertTriangle, paused: PauseCircle, planned: Clock3 };
const roadmap = [
  { name: "eGP Uganda", type: "Government portal", group: "Government", icon: ShieldCheck },
  { name: "GPP / PPDA", type: "Procurement portal", group: "Government", icon: ShieldCheck },
  { name: "Daily Monitor", type: "Newspaper tenders", group: "Newspapers", icon: Newspaper },
  { name: "New Vision", type: "Newspaper tenders", group: "Newspapers", icon: Newspaper },
  { name: "URA & public entities", type: "Direct websites", group: "Government", icon: Globe2 },
  { name: "UN & development partners", type: "Development opportunities", group: "Development", icon: UsersRound },
  { name: "NGO procurement", type: "Organization websites", group: "Development", icon: UsersRound },
  { name: "Private sector", type: "Company procurement", group: "Private", icon: Globe2 },
];

export function SourceGrid({ sources, loading, admin = false }: { sources: BidSource[]; loading?: boolean; admin?: boolean }) {
  if (loading) return <div className="source-grid suite-source-grid"><div className="source-card skeleton-block" /><div className="source-card skeleton-block" /><div className="source-card skeleton-block" /></div>;
  if (!sources.length) return <div className="suite-source-roadmap">{roadmap.map(({ name, type, group, icon: Icon }) => <article key={name}><div className="suite-source-roadmap-head"><span><Icon size={18} /></span><em>Ready to connect</em></div><h3>{name}</h3><p>{type}</p><small>{group}</small>{admin && <div className="suite-adapter-note">Collector adapter has not reported a live run yet.</div>}</article>)}</div>;

  return <div className="source-grid suite-source-grid">{sources.map((source) => { const Icon = icons[source.health] || Clock3; return <article className="source-card suite-live-source-card" key={source.id}><div className="source-card-head"><span className={`source-health health-${source.health}`}><Icon size={17} /></span><span className="source-type">{source.type}</span></div><h3>{source.name}</h3><a href={source.baseUrl} target="_blank" rel="noreferrer">{source.baseUrl.replace(/^https?:\/\//, "")}</a><div className="source-metrics"><div><span>Last success</span><strong>{source.lastSuccessfulCrawlAt ? formatDate(source.lastSuccessfulCrawlAt, true) : "Not yet"}</strong></div><div><span>Records found</span><strong>{source.recordsFound ?? 0}</strong></div></div>{admin && <p className="source-note">{source.health === "planned" ? "Adapter is waiting for its first live connection." : source.lastError || "Collector is reporting normally."}</p>}</article>; })}</div>;
}
