"use client";

import { Building2 } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useBids } from "@/hooks/useBids";

export default function OrganizationsPage() {
  const { bids, loading } = useBids();
  const counts = bids.reduce<Record<string, number>>((acc, bid) => { acc[bid.organization] = (acc[bid.organization] || 0) + 1; return acc; }, {});
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <div className="page-stack">
      <PageHeader eyebrow="Market map" title="Organizations" description="Procuring entities discovered across connected sources." />
      <section className="panel">
        {loading ? <div className="skeleton-lines" /> : rows.length === 0 ? <EmptyState title="No organizations yet" description="Organizations will be generated from real bid data as it enters Firestore." /> : (
          <div className="organization-grid">{rows.map(([name, count]) => <div className="organization-card" key={name}><span className="org-icon"><Building2 size={20} /></span><div><strong>{name}</strong><small>{count} opportunity{count === 1 ? "" : "ies"}</small></div></div>)}</div>
        )}
      </section>
    </div>
  );
}
