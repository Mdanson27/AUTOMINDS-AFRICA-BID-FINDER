"use client";

import Link from "next/link";
import { ArrowRight, Bookmark, ClipboardCheck, Send, Telescope } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";
import { useSavedBids } from "@/hooks/useSavedBids";

export default function SavedPage() {
  const { bids, loading } = useBids();
  const { savedIds } = useSavedBids();
  const saved = bids.filter((bid) => savedIds.has(bid.id));
  return <div className="page-stack suite-saved-page"><PageHeader eyebrow="Opportunity pipeline" title="Saved bids" description="Keep the opportunities worth pursuing close and prepare for a full bid workflow as the platform expands." action={<Link href="/bids" className="button primary">Find more bids <ArrowRight size={15} /></Link>} />
    <section className="suite-pipeline-preview"><article className="active"><Bookmark size={18} /><div><strong>Watching</strong><span>{saved.length} saved opportunity{saved.length === 1 ? "" : "ies"}</span></div></article><article><Telescope size={18} /><div><strong>Considering</strong><span>Bid / no-bid workspace</span></div></article><article><ClipboardCheck size={18} /><div><strong>Preparing</strong><span>Requirements & checklist</span></div></article><article><Send size={18} /><div><strong>Submitted</strong><span>Submission tracking</span></div></article></section>
    <section><div className="suite-section-title"><div><span className="eyebrow">WATCHLIST</span><h2>Your saved opportunities</h2><p>Saved bids stay here so you can return to them quickly.</p></div></div><BidList bids={saved} loading={loading} /></section>
  </div>;
}
