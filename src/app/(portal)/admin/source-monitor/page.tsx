"use client";

import Link from "next/link";
import { Plus, ShieldCheck } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import { SourceGrid } from "@/components/sources/SourceGrid";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useSources } from "@/hooks/useSources";

export default function SourceMonitorPage() {
  const { profile } = useAuth();
  const { sources, loading } = useSources();
  if (profile?.role !== "admin") return <EmptyState title="Admin access required" description="Source health and collector controls are restricted to administrators." />;
  return (
    <div className="page-stack">
      <PageHeader eyebrow="Administration" title="Source monitor" description="Watch source health, crawl timing and collection readiness." action={<Link href="/admin/bids/new" className="button primary"><Plus size={16} /> Add test bid</Link>} />
      <div className="notice-card"><ShieldCheck size={20} /><div><strong>Collector-safe foundation</strong><p>Normalized records and the collector workspace are separated so a source failure cannot take down the user-facing Bid Finder experience.</p></div></div>
      <SourceGrid sources={sources} loading={loading} admin />
    </div>
  );
}
