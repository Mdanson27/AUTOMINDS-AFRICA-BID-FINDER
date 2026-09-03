"use client";

import Link from "next/link";
import { ArrowRight, CalendarClock, DatabaseZap, FileSearch, RadioTower } from "lucide-react";
import { BidList } from "@/components/bids/BidList";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { useBids } from "@/hooks/useBids";
import { daysUntil, isSameLocalDay } from "@/lib/date";

export default function DashboardPage() {
  const { bids, loading, error } = useBids();
  const now = new Date();
  const open = bids.filter((bid) => bid.status === "open" && daysUntil(bid.deadlineAt) >= 0);
  const newToday = bids.filter((bid) => isSameLocalDay(bid.firstSeenAt, now));
  const closing = open.filter((bid) => daysUntil(bid.deadlineAt) <= 7);
  const organizations = new Set(bids.map((bid) => bid.organization.trim()).filter(Boolean));

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Procurement intelligence"
        title="Good morning. Here is today’s bid landscape."
        description="One place to track opportunities, deadlines, sources and changes across Uganda."
        action={<Link href="/bids" className="button primary">Find bids <ArrowRight size={16} /></Link>}
      />

      <section className="stats-grid" aria-label="Bid summary">
        <StatCard label="Open bids" value={loading ? "—" : open.length} icon={<FileSearch />} hint="Currently active opportunities" />
        <StatCard label="New today" value={loading ? "—" : newToday.length} icon={<RadioTower />} hint="First seen today" />
        <StatCard label="Closing in 7 days" value={loading ? "—" : closing.length} icon={<CalendarClock />} hint="Needs attention" />
        <StatCard label="Organizations" value={loading ? "—" : organizations.size} icon={<DatabaseZap />} hint="Entities in the database" />
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Priority queue</span>
            <h2>Closing soon</h2>
          </div>
          <Link href="/closing-soon" className="text-link">View all <ArrowRight size={15} /></Link>
        </div>

        {error ? (
          <EmptyState title="Firestore is not ready yet" description={error} />
        ) : !loading && closing.length === 0 ? (
          <EmptyState
            title="No live bids yet"
            description="The interface is connected to Firestore and waiting for real bid records. Once the collectors start writing, opportunities will appear here automatically."
            action={<Link href="/admin/bids/new" className="button secondary">Add a test bid</Link>}
          />
        ) : (
          <BidList bids={closing.slice(0, 6)} loading={loading} compact />
        )}
      </section>
    </div>
  );
}
