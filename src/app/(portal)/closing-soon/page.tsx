"use client";

import { BidList } from "@/components/bids/BidList";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";
import { daysUntil } from "@/lib/date";

export default function ClosingSoonPage() {
  const { bids, loading } = useBids();
  const closing = bids.filter((bid) => bid.status === "open" && daysUntil(bid.deadlineAt) >= 0 && daysUntil(bid.deadlineAt) <= 14);
  return <div className="page-stack"><PageHeader eyebrow="Deadlines" title="Closing soon" description="Open opportunities with deadlines in the next 14 days." /><BidList bids={closing} loading={loading} /></div>;
}
