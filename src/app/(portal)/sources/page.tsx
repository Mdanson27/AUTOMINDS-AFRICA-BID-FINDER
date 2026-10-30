"use client";

import Link from "next/link";
import { ArrowRight, Building2, Landmark, Newspaper, Radar, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { SourceGrid } from "@/components/sources/SourceGrid";
import { useSources } from "@/hooks/useSources";

const groups = [
  { label: "Government", description: "eGP, GPP/PPDA and direct public institutions", icon: Landmark, href: "/bids?scope=government" },
  { label: "Current papers", description: "Daily Monitor and New Vision tender channels", icon: Newspaper, href: "/papers" },
  { label: "NGO & Development", description: "UN, multilaterals, development partners and NGOs", icon: UsersRound, href: "/bids?scope=development" },
  { label: "Private sector", description: "Companies and private procurement as the network expands", icon: Building2, href: "/bids?scope=private" },
];

export default function SourcesPage() {
  const { sources, loading } = useSources();
  const healthy = sources.filter((source) => source.health === "healthy").length;
  const warnings = sources.filter((source) => source.health === "warning").length;
  const monitored = sources.length || 30;

  return <div className="page-stack suite-sources-page">
    <PageHeader
      eyebrow="30-SOURCE COLLECTION NETWORK"
      title="Source network"
      description={loading
        ? "Loading health information for the 30-source Bid Finder collection network."
        : `${monitored} procurement sources monitored · ${healthy} healthy${warnings ? ` · ${warnings} need attention` : ""}. A source can be healthy with zero current notices; only genuine access or collector failures are flagged.`}
      action={<Link href="/scan" className="button primary"><Radar size={15} /> Scan newest bids</Link>}
    />
    <section className="suite-source-groups-page">{groups.map(({ label, description, icon: Icon, href }) => <Link href={href} key={label}><span><Icon size={20} /></span><div><strong>{label}</strong><small>{description}</small></div><ArrowRight size={16} /></Link>)}</section>
    <section><div className="suite-section-title"><div><span className="eyebrow">SOURCE DIRECTORY</span><h2>Collection readiness</h2><p>Every source reports independently. A blocked or unavailable publisher remains visible as a warning and cannot stop the other collectors from completing their scans.</p></div></div><SourceGrid sources={sources} loading={loading} admin /></section>
  </div>;
}
