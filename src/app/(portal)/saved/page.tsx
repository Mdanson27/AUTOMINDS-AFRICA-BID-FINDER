"use client";

import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";
import { useSavedBids } from "@/hooks/useSavedBids";

export default function SavedPage() {
  const { bids, loading } = useBids();
  const { savedIds } = useSavedBids();
  return <div className="page-stack"><PageHeader eyebrow="Watchlist" title="Saved bids" description="Opportunities you want to follow closely." /><BidList bids={bids.filter((bid) => savedIds.has(bid.id))} loading={loading} /></div>;
}
