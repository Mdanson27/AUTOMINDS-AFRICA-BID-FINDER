"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, Bookmark, CalendarDays, ExternalLink, FileCheck2, Landmark, ReceiptText, Send, Share2, ShieldCheck, Tag } from "lucide-react";
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
    if (candidate.length > 430 && current) { paragraphs.push(current); current = sentence; } else { current = candidate; }
  }
  if (current) paragraphs.push(current);
  return paragraphs.slice(0, 7);
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

  if (!mounted || loading) return <div className="premium-loading"><div className="premium-loading-head" /><div className="premium-loading-toolbar" /><div className="premium-loading-card" /></div>;
  if (error) return <EmptyState title="Could not load this bid" description={error} />;
  if (!bid) return <EmptyState title="Bid not found" description="This opportunity may have expired, fallen outside the current financial-year window, or been removed from its source." action={<Link href="/bids" className="button secondary">Back to bids</Link>} />;

  const remaining = daysUntil(bid.deadlineAt);
  const urgent = Number.isFinite(remaining) && remaining <= 3 && remaining >= 0;
  const primarySource = bid.sources[0];
  const intelligence = bid.intelligence;

  return (
    <div className="page-stack suite-bid-detail">
      <Link href="/bids" className="back-link"><ArrowLeft size={16} /> Back to search</Link>

      <section className="suite-detail-hero">
        <div className="suite-detail-heading">
          <div className="badge-row">
            <span className={`status-badge status-${bid.status}`}>{bid.status}</span>
            {bid.procurementType && <span className="soft-badge">{bid.procurementType}</span>}
            {intelligence?.enrichmentStatus && <span className="enrichment-badge"><FileCheck2 size={13} /> {intelligence.enrichmentStatus} intelligence</span>}
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

      {bid.deadlineChanged && <div className="notice-card"><AlertTriangle size={20} /><div><strong>Deadline change detected</strong><p>The deadline changed after this opportunity was first discovered. The current deadline shown above is the latest value collected.</p></div></div>}

      <div className="suite-detail-layout">
        <div className="suite-detail-main">
          <section className="panel suite-opportunity-overview">
            <div className="suite-section-title"><div><span className="eyebrow">PROCUREMENT BRIEF</span><h2>Opportunity intelligence</h2><p>Structured facts extracted from the public notice. Missing fields are left blank rather than guessed.</p></div></div>

            <div className="intelligence-summary">
              <article><span>Reference</span><strong>{bid.referenceNumber || "Not provided"}</strong></article>
              <article><span>Category</span><strong>{bid.category || "Uncategorized"}</strong></article>
              <article><span>Published</span><strong>{formatDate(bid.publishedAt)}</strong></article>
              <article><span>Last checked</span><strong>{formatDate(bid.lastSeenAt, true)}</strong></article>
            </div>

            <div className="intelligence-section">
              <h3>Commercial requirements</h3>
              <div className="intelligence-summary">
                <article><span>Bid security</span><strong>{intelligence?.bidSecurity || "Not found in collected text"}</strong></article>
                <article><span>Tender / document fee</span><strong>{intelligence?.tenderFee || "Not found in collected text"}</strong></article>
                <article><span>Submission method</span><strong>{intelligence?.submissionMethod || "Not yet extracted"}</strong></article>
                <article><span>Extraction confidence</span><strong>{intelligence?.confidence || "Low"}</strong></article>
              </div>
            </div>

            <div className="intelligence-section">
              <h3>Mandatory requirements detected</h3>
              {intelligence?.mandatoryRequirements?.length ? <div className="requirement-chips">{intelligence.mandatoryRequirements.map((item) => <span key={item}>{item}</span>)}</div> : <p>No structured mandatory requirements have been detected from the currently collected notice text. Open the original notice for the complete procurement document.</p>}
            </div>

            {intelligence?.eligibility?.length ? <div className="intelligence-section"><h3>Eligibility signals</h3><div className="requirement-chips">{intelligence.eligibility.map((item) => <span key={item}>{item}</span>)}</div></div> : null}

            {intelligence?.keyDates?.length ? <div className="intelligence-section"><h3>Additional dates & milestones</h3><div className="requirement-chips">{intelligence.keyDates.map((item) => <span key={item}>{item}</span>)}</div></div> : null}

            <div className="intelligence-section description-block">
              <h3>Scope / description</h3>
              {descriptionParagraphs.length ? descriptionParagraphs.map((paragraph, index) => <p key={`${bid.id}-description-${index}`}>{paragraph}</p>) : <p>A structured description has not been extracted yet. Open the original notice for the complete procurement information.</p>}
            </div>
          </section>

          <section className="panel suite-prepared-sections">
            <div className="suite-section-title"><div><span className="eyebrow">BID PREPARATION</span><h2>Preparation checklist</h2></div></div>
            <div className="suite-prep-grid">
              <article><ShieldCheck size={20} /><strong>Security & fees</strong><span>{intelligence?.bidSecurity || intelligence?.tenderFee ? "Commercial security / fee information has been detected above." : "Security and fee information still needs deeper source-document enrichment."}</span></article>
              <article><CalendarDays size={20} /><strong>Dates</strong><span>{intelligence?.keyDates?.length ? `${intelligence.keyDates.length} additional milestone${intelligence.keyDates.length === 1 ? "" : "s"} detected.` : "Deadline captured; pre-bid and clarification dates will appear when detected."}</span></article>
              <article><Send size={20} /><strong>Submission</strong><span>{intelligence?.submissionMethod || "Submission instructions have not yet been structured."}</span></article>
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

          <section className="panel suite-source-trail">
            <div className="suite-section-title"><div><span className="eyebrow">COMMERCIAL CHECK</span><h2>What Bid Finder found</h2></div></div>
            <div className="requirement-chips">
              <span><ShieldCheck size={12} /> {intelligence?.bidSecurity ? "Security detected" : "Security not found"}</span>
              <span><ReceiptText size={12} /> {intelligence?.tenderFee ? "Fee detected" : "Fee not found"}</span>
              <span><Tag size={12} /> {intelligence?.enrichmentStatus || "basic"}</span>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
