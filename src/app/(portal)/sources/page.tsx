"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { SourceGrid } from "@/components/sources/SourceGrid";
import { useSources } from "@/hooks/useSources";

export default function SourcesPage() {
  const { sources, loading } = useSources();
  return <div className="page-stack"><PageHeader eyebrow="Collection network" title="Sources" description="The publications, portals and organization websites feeding Bid Finder." /><SourceGrid sources={sources} loading={loading} /></div>;
}
