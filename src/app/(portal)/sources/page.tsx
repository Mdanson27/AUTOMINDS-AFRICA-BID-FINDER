"use client";

import Link from "next/link";
import { ArrowRight, Building2, Landmark, Newspaper, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { SourceGrid } from "@/components/sources/SourceGrid";
import { useSources } from "@/hooks/useSources";

const groups = [
  { label: "Government", description: "Public procurement portals and entity websites", icon: Landmark, href: "/bids?scope=government" },
  { label: "Newspapers", description: "Tender notices from major Ugandan publications", icon: Newspaper, href: "/bids?scope=newspapers" },
  { label: "NGO & Development", description: "Development partners, NGOs and international organizations", icon: UsersRound, href: "/bids?scope=development" },
  { label: "Private sector", description: "Companies, institutions and private procurement", icon: Building2, href: "/bids?scope=private" },
];

export default function SourcesPage() {
  const { sources, loading } = useSources();
  return <div className="page-stack suite-sources-page"><PageHeader eyebrow="Collection network" title="Sources" description="Control where Bid Finder looks and understand the coverage that will power your searches." action={<Link href="/bids" className="button primary">Search all sources <ArrowRight size={15} /></Link>} />
    <section className="suite-source-groups-page">{groups.map(({ label, description, icon: Icon, href }) => <Link href={href} key={label}><span><Icon size={20} /></span><div><strong>{label}</strong><small>{description}</small></div><ArrowRight size={16} /></Link>)}</section>
    <section><div className="suite-section-title"><div><span className="eyebrow">SOURCE DIRECTORY</span><h2>Collection network</h2><p>Live adapters appear with health information; planned sources remain visible so coverage can be expanded deliberately.</p></div></div><SourceGrid sources={sources} loading={loading} /></section>
  </div>;
}
