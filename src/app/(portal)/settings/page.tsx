"use client";

import { useEffect, useState } from "react";
import { Check, Save, UserRound } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/components/auth/AuthProvider";

export default function SettingsPage() {
  const { user, profile } = useAuth();
  const [scope, setScope] = useState("all"); const [deadline, setDeadline] = useState("7"); const [density, setDensity] = useState("comfortable"); const [saved, setSaved] = useState(false);

  useEffect(() => { try { const stored = JSON.parse(localStorage.getItem("bidFinderPreferences") || "{}"); if (stored.scope) setScope(stored.scope); if (stored.deadline) setDeadline(stored.deadline); if (stored.density) setDensity(stored.density); } catch {} }, []);
  function savePreferences() { localStorage.setItem("bidFinderPreferences", JSON.stringify({ scope, deadline, density })); setSaved(true); window.setTimeout(() => setSaved(false), 1800); }

  return (
    <div className="page-stack suite-settings-page">
      <PageHeader eyebrow="Workspace" title="Settings" description="Set your default discovery preferences and manage how Bid Finder should work for you." />
      <div className="suite-settings-layout">
        <section className="panel suite-account-card"><span className="suite-account-icon"><UserRound size={22} /></span><div className="avatar-large">{(profile?.displayName || user?.email || "U").slice(0, 1).toUpperCase()}</div><div><h2>{profile?.displayName || "Bid Finder user"}</h2><p>{user?.email}</p><span className="soft-badge">{profile?.role || "viewer"}</span></div></section>
        <section className="panel suite-preferences-card"><div className="suite-section-title"><div><span className="eyebrow">DISCOVERY DEFAULTS</span><h2>Search preferences</h2><p>These preferences are saved on this device for the current preview.</p></div></div><div className="suite-preference-grid"><label><span>Default search coverage</span><select value={scope} onChange={(e) => setScope(e.target.value)}><option value="all">Everywhere</option><option value="government">Government</option><option value="newspapers">Newspapers</option><option value="development">NGO & Development</option><option value="private">Private sector</option></select></label><label><span>Closing-soon threshold</span><select value={deadline} onChange={(e) => setDeadline(e.target.value)}><option value="3">3 days</option><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option></select></label><label><span>Result density</span><select value={density} onChange={(e) => setDensity(e.target.value)}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label></div><button className="button primary suite-save-settings" onClick={savePreferences}>{saved ? <><Check size={15} /> Saved</> : <><Save size={15} /> Save preferences</>}</button></section>
      </div>
    </div>
  );
}
