"use client";

import Link from "next/link";
import { ArrowRight, Building2, Landmark, Newspaper, Radar, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { SourceGrid } from "@/components/sources/SourceGrid";
import { useSources } from "@/hooks/useSources";

const groups = [
  { label: "Government", description: "eGP, PPDA and public entity websites", icon: Landmark, href: "/bids?scope=government" },
  { label: "Current papers", description: "Daily Monitor and New Vision tender channels", icon: Newspaper, href: "/papers" },
  { label: "NGO & Development", description: "World Bank, UN and development partners", icon: UsersRound, href: "/bids?scope=development" },
  { label: "Private sector", description: "Companies, institutions and private procurement", icon: Building2, href: "/bids?scope=private" },
];

export default function SourcesPage() {
  const { sources, loading } = useSources();
  const healthy = sources.filter((source) => source.health === "healthy").length;
  const warnings = sources.filter((source) => source.health === "warning").length;

  return <div className="page-stack suite-sources-page">
    <PageHeader
      eyebrow="Collection network"
      title="Source network"
      description={`${healthy} source${healthy === 1 ? "" : "s"} currently reporting healthy${warnings ? ` · ${warnings} need attention` : ""}. Use Scan Center to choose exactly where Bid Finder should look.`}
      action={<Link href="/scan" className="button primary"><Radar size={15} /> Scan newest bids</Link>}
    />
    <section className="suite-source-groups-page">{groups.map(({ label, description, icon: Icon, href }) => <Link href={href} key={label}><span><Icon size={20} /></span><div><strong>{label}</strong><small>{description}</small></div><ArrowRight size={16} /></Link>)}</section>
    <section><div className="suite-section-title"><div><span className="eyebrow">SOURCE DIRECTORY</span><h2>Collection readiness</h2><p>Health is based on actual source responses. A blocked or dynamic publisher stays visible as a warning instead of being represented as successfully connected.</p></div></div><SourceGrid sources={sources} loading={loading} admin /></section>
  </div>;
}
