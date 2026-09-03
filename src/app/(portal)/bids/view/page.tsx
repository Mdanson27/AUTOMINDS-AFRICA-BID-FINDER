"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, Bookmark, CalendarDays, ExternalLink, FileCheck2, Landmark, Share2, Tag } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { useBids } from "@/hooks/useBids";
import { daysUntil, deadlineLabel, formatDate } from "@/lib/date";

function splitDescription(value: string) {
  const text = value.replace(/\s*\|\s*/g, ". ").replace(/\s+/g, " ").trim();
  if (!text) return [];

  const sentences = text.split(/(?<=[.!?])\s+(?=[A-Z0-9])/);
  const paragraphs: string[] = [];
  let current = "";

  for (const sentence of sentences) {
    const candidate = current ? `${current} ${sentence}` : sentence;
    if (candidate.length > 430 && current) {
      paragraphs.push(current);
      current = sentence;
    } else {
      current = candidate;
    }
  }

  if (current) paragraphs.push(current);
  return paragraphs.slice(0, 5);
}

export default function BidDetailPage() {
  const { bids, loading, error } = useBids();
  const [bidId, setBidId] = useState("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setBidId(params.get("id") || "");
    setMounted(true);
  }, []);

  const bid = bids.find((item) => item.id === bidId);
  const descriptionParagraphs = useMemo(() => splitDescription(bid?.description || ""), [bid?.description]);

  if (!mounted || loading) return <div className="panel skeleton-block" />;
  if (error) return <EmptyState title="Could not load this bid" description={error} />;
  if (!bid) return <EmptyState title="Bid not found" description="This opportunity may have expired, fallen outside the current financial-year window, or been removed from its source." action={<Link href="/bids" className="button secondary">Back to bids</Link>} />;

  const remaining = daysUntil(bid.deadlineAt);
  const urgent = Number.isFinite(remaining) && remaining <= 3 && remaining >= 0;
  const primarySource = bid.sources[0];

  return (
    <div className="page-stack suite-bid-detail">
      <Link href="/bids" className="back-link"><ArrowLeft size={16} /> Back to search</Link>

      <section className="suite-detail-hero">
        <div className="suite-detail-heading">
          <div className="badge-row">
            <span className={`status-badge status-${bid.status}`}>{bid.status}</span>
            {bid.procurementType && <span className="soft-badge">{bid.procurementType}</span>}
            {bid.deadlineChanged && <span className="soft-badge deadline-change-badge"><AlertTriangle size={12} /> Deadline updated</span>}
          </div>
          <h1>{bid.title}</h1>
          <p><Landmark size={17} /> <span>{bid.organization}</span></p>
        </div>

        <div className="suite-detail-deadline">
          <span>DEADLINE</span>
          <strong>{formatDate(bid.deadlineAt, true)}</strong>
          <small className={urgent ? "urgent" : ""}>{deadlineLabel(bid.deadlineAt)}</small>
        </div>
      </section>

      {bid.deadlineChanged && <div className="notice-card"><AlertTriangle size={20} /><div><strong>Deadline change detected</strong><p>The deadline for this opportunity changed after it was first discovered{bid.deadlineChangedAt ? ` on ${formatDate(bid.deadlineChangedAt, true)}` : ""}. The current deadline shown above is the latest value collected.</p></div></div>}

      <div className="suite-detail-layout">
        <div className="suite-detail-main">
          <section className="panel suite-opportunity-overview">
            <div className="suite-section-title"><div><span className="eyebrow">OVERVIEW</span><h2>Opportunity details</h2></div></div>
            <div className="meta-grid suite-meta-grid">
              <div><span>Reference</span><strong>{bid.referenceNumber || "Not provided"}</strong></div>
              <div><span>Category</span><strong><Tag size={14} /> {bid.category || "Uncategorized"}</strong></div>
              <div><span>Published</span><strong><CalendarDays size={14} /> {formatDate(bid.publishedAt)}</strong></div>
              <div><span>Last checked</span><strong>{formatDate(bid.lastSeenAt, true)}</strong></div>
            </div>

            <div className="description-block">
              <h3>Description</h3>
              {descriptionParagraphs.length ? descriptionParagraphs.map((paragraph, index) => <p key={`${bid.id}-description-${index}`}>{paragraph}</p>) : <p>A structured description has not been extracted yet. Open the original notice for the complete procurement information.</p>}
            </div>
          </section>

          <section className="panel suite-prepared-sections">
            <div className="suite-section-title"><div><span className="eyebrow">BID PREPARATION</span><h2>Requirements & submission</h2></div></div>
            <div className="suite-prep-grid">
              <article><FileCheck2 size={20} /><strong>Mandatory requirements</strong><span>Eligibility documents and mandatory conditions will appear here as they are extracted from source documents.</span></article>
              <article><CalendarDays size={20} /><strong>Key dates</strong><span>Pre-bid meetings, clarification windows and submission milestones will be organized here.</span></article>
              <article><Landmark size={20} /><strong>Submission method</strong><span>Physical, electronic and delivery instructions will be summarized here when available.</span></article>
            </div>
          </section>
        </div>

        <aside className="suite-detail-side">
          <section className="panel suite-action-panel">
            <h2>Bid actions</h2>
            <button><Bookmark size={16} /> Save opportunity</button>
            {primarySource?.url && <a href={primarySource.url} target="_blank" rel="noreferrer"><ExternalLink size={16} /> Open original notice</a>}
            <button><Share2 size={16} /> Share</button>
          </section>

          <section className="panel suite-source-trail">
            <div className="suite-section-title"><div><span className="eyebrow">SOURCE TRAIL</span><h2>Detected notices</h2></div></div>
            {bid.sources.length ? bid.sources.map((source) => <a href={source.url} target="_blank" rel="noreferrer" key={`${source.name}-${source.url}`}><div><strong>{source.name}</strong><span>{source.detectedAt ? `Seen ${formatDate(source.detectedAt)}` : "Source notice"}</span></div><ExternalLink size={15} /></a>) : <p>No source links stored yet.</p>}
          </section>
        </aside>
      </div>
    </div>
  );
}
