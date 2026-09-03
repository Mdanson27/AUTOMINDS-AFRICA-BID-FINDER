"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/components/auth/AuthProvider";

export default function SettingsPage() {
  const { user, profile } = useAuth();
  return (
    <div className="page-stack narrow-page">
      <PageHeader eyebrow="Account" title="Settings" description="Your Bid Finder identity and access level." />
      <section className="panel settings-card">
        <div className="avatar-large">{(profile?.displayName || user?.email || "U").slice(0, 1).toUpperCase()}</div>
        <div><h2>{profile?.displayName || "Bid Finder user"}</h2><p>{user?.email}</p><span className="soft-badge">{profile?.role || "viewer"}</span></div>
      </section>
    </div>
  );
}
