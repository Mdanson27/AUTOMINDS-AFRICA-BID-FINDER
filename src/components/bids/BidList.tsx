"use client";

import Link from "next/link";
import { AlertTriangle, Bookmark, BookmarkCheck, Building2, CalendarDays, ExternalLink, Layers3 } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useSavedBids } from "@/hooks/useSavedBids";
import type { Bid } from "@/lib/types";
import { daysUntil, deadlineLabel, formatDate } from "@/lib/date";

export function BidList({ bids, loading, compact = false }: { bids: Bid[]; loading?: boolean; compact?: boolean }) {
  const { user } = useAuth();
  const { savedIds, toggle } = useSavedBids();

  if (loading) {
    return <div className="suite-result-list"><div className="suite-result-card skeleton-row" /><div className="suite-result-card skeleton-row" /><div className="suite-result-card skeleton-row" /></div>;
  }

  if (!bids.length) {
    return <div className="suite-empty"><Layers3 size={24} /><strong>No opportunities match this view</strong><span>Try broadening the search coverage, removing a filter or checking another source group.</span></div>;
  }

  return (
    <div className={`suite-result-list ${compact ? "compact" : ""}`}>
      {bids.map((bid) => {
        const remaining = daysUntil(bid.deadlineAt);
        const saved = savedIds.has(bid.id);
        const primarySource = bid.sources[0];
        const detailHref = `/bids/view?id=${encodeURIComponent(bid.id)}`;
        const urgent = Number.isFinite(remaining) && remaining <= 3 && remaining >= 0;

        return <article className={`suite-result-card suite-result-card-${bid.status}`} key={bid.id}>
          <div className="suite-result-main">
            <div className="suite-result-topline">
              <span className={`status-badge status-${bid.status}`}>{bid.status}</span>
              {bid.procurementType && <span className="soft-badge">{bid.procurementType}</span>}
              {bid.deadlineChanged && <span className="soft-badge deadline-change-badge"><AlertTriangle size={12} /> Deadline updated</span>}
              <span className="suite-source-count"><Layers3 size={13} /> {bid.sources.length || 0} source{bid.sources.length === 1 ? "" : "s"}</span>
            </div>

            <Link href={detailHref} className="suite-result-title" title={bid.title}>{bid.title}</Link>
            <p className="suite-result-org"><Building2 size={15} /> <span>{bid.organization}</span></p>

            <div className="suite-result-meta">
              <span><strong>Reference</strong>{bid.referenceNumber || "Not provided"}</span>
              <span><strong>Category</strong>{bid.category || "Uncategorized"}</span>
              <span><strong>Published</strong>{formatDate(bid.publishedAt)}</span>
            </div>

            <div className="suite-source-badges">
              {bid.sources.slice(0, 3).map((item) => <span key={`${bid.id}-${item.name}`}>{item.name}</span>)}
              {bid.sources.length > 3 && <span>+{bid.sources.length - 3}</span>}
            </div>
          </div>

          <div className="suite-result-deadline">
            <span><CalendarDays size={15} /> Deadline</span>
            <strong>{formatDate(bid.deadlineAt)}</strong>
            <small className={urgent ? "urgent" : ""}>{deadlineLabel(bid.deadlineAt)}</small>
            {bid.deadlineChanged && <small className="deadline-change-note">Changed since first discovery</small>}
          </div>

          <div className="suite-result-actions">
            <button onClick={() => user && toggle(bid.id)} className={`suite-save-button ${saved ? "saved" : ""}`} aria-label={saved ? "Remove saved bid" : "Save bid"}>
              {saved ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}<span>{saved ? "Saved" : "Save"}</span>
            </button>
            <Link href={detailHref} className="suite-view-button">View bid</Link>
            {primarySource?.url && <a href={primarySource.url} target="_blank" rel="noreferrer" className="suite-open-source" aria-label="Open original notice"><ExternalLink size={16} /></a>}
          </div>
        </article>;
      })}
    </div>
  );
}
