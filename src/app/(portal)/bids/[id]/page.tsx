"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CalendarDays, ExternalLink, Landmark, Tag } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { useBids } from "@/hooks/useBids";
import { daysUntil, formatDate } from "@/lib/date";

export default function BidDetailPage() {
  const params = useParams<{ id: string }>();
  const { bids, loading, error } = useBids();
  const bid = bids.find((item) => item.id === params.id);

  if (loading) return <div className="panel skeleton-block" />;
  if (error) return <EmptyState title="Could not load this bid" description={error} />;
  if (!bid) return <EmptyState title="Bid not found" description="This opportunity may have been removed or is not available to your account." action={<Link href="/bids" className="button secondary">Back to bids</Link>} />;

  const remaining = daysUntil(bid.deadlineAt);

  return (
    <div className="page-stack">
      <Link href="/bids" className="back-link"><ArrowLeft size={16} /> Back to bids</Link>
      <section className="detail-hero">
        <div>
          <div className="badge-row"><span className={`status-badge status-${bid.status}`}>{bid.status}</span>{bid.procurementType && <span className="soft-badge">{bid.procurementType}</span>}</div>
          <h1>{bid.title}</h1>
          <p className="detail-org"><Landmark size={18} /> {bid.organization}</p>
        </div>
        <div className="deadline-card">
          <span>Deadline</span>
          <strong>{formatDate(bid.deadlineAt, true)}</strong>
          <small>{remaining >= 0 ? `${remaining} day${remaining === 1 ? "" : "s"} remaining` : "Closed"}</small>
        </div>
      </section>

      <div className="detail-grid">
        <section className="panel detail-main">
          <h2>Opportunity details</h2>
          <div className="meta-grid">
            <div><span>Reference</span><strong>{bid.referenceNumber || "Not provided"}</strong></div>
            <div><span>Category</span><strong><Tag size={15} /> {bid.category || "Uncategorized"}</strong></div>
            <div><span>Published</span><strong><CalendarDays size={15} /> {formatDate(bid.publishedAt)}</strong></div>
            <div><span>First seen</span><strong>{formatDate(bid.firstSeenAt)}</strong></div>
          </div>
          <div className="description-block">
            <h3>Description</h3>
            <p>{bid.description || "No description has been extracted yet. Open the original notice for complete procurement information."}</p>
          </div>
        </section>

        <aside className="panel source-panel">
          <h2>Detected sources</h2>
          <p className="muted">One normalized bid can be backed by several source notices.</p>
          <div className="source-list">
            {bid.sources.length ? bid.sources.map((source) => (
              <a href={source.url} target="_blank" rel="noreferrer" key={`${source.name}-${source.url}`} className="source-link-card">
                <span><strong>{source.name}</strong><small>{source.detectedAt ? `Seen ${formatDate(source.detectedAt)}` : "Source notice"}</small></span><ExternalLink size={16} />
              </a>
            )) : <span className="muted">No source links stored yet.</span>}
          </div>
        </aside>
      </div>
    </div>
  );
}
