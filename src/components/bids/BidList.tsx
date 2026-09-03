"use client";

import Link from "next/link";
import { Bookmark, BookmarkCheck, CalendarDays, ExternalLink } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useSavedBids } from "@/hooks/useSavedBids";
import type { Bid } from "@/lib/types";
import { daysUntil, formatDate } from "@/lib/date";

export function BidList({ bids, loading, compact = false }: { bids: Bid[]; loading?: boolean; compact?: boolean }) {
  const { user } = useAuth(); const { savedIds, toggle } = useSavedBids();
  if (loading) return <div className="bid-list"><div className="bid-row skeleton-row" /><div className="bid-row skeleton-row" /><div className="bid-row skeleton-row" /></div>;
  if (!bids.length) return <div className="empty-inline">No opportunities match this view yet.</div>;
  return (
    <div className={`bid-list ${compact ? "compact" : ""}`}>
      {bids.map((bid) => {
        const remaining = daysUntil(bid.deadlineAt); const saved = savedIds.has(bid.id);
        return <article className="bid-row" key={bid.id}>
          <div className="bid-main"><div className="bid-topline"><span className={`status-badge status-${bid.status}`}>{bid.status}</span><span className="bid-source">{bid.sources[0]?.name || "Unassigned source"}{bid.sources.length > 1 ? ` +${bid.sources.length - 1}` : ""}</span></div><Link href={`/bids/${bid.id}`} className="bid-title">{bid.title}</Link><p>{bid.organization}</p><div className="bid-meta"><span>{bid.referenceNumber || "No reference"}</span>{bid.category && <span>{bid.category}</span>}</div></div>
          <div className="bid-deadline"><span><CalendarDays size={15} /> Deadline</span><strong>{formatDate(bid.deadlineAt)}</strong><small className={remaining <= 3 && remaining >= 0 ? "urgent" : ""}>{remaining >= 0 ? `${remaining} day${remaining === 1 ? "" : "s"} left` : "Closed"}</small></div>
          <div className="bid-actions"><button onClick={() => user && toggle(bid.id)} className={`icon-button ${saved ? "saved" : ""}`} aria-label={saved ? "Remove saved bid" : "Save bid"}>{saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}</button><Link href={`/bids/${bid.id}`} className="icon-button" aria-label="View bid"><ExternalLink size={18} /></Link></div>
        </article>;
      })}
    </div>
  );
}
