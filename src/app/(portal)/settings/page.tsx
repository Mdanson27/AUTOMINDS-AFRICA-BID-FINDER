"use client";

import { useEffect, useState } from "react";
import { BellRing, Check, Clock3, KeyRound, Loader2, Save, Search, ShieldCheck, SlidersHorizontal, UserRound } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/components/auth/AuthProvider";
import { saveUserPreferences, subscribeUserPreferences, type UserPreferences } from "@/lib/userWorkspace";

export default function SettingsPage() {
  const { user, profile, resetPassword } = useAuth();
  const [scope, setScope] = useState<UserPreferences["scope"]>("all");
  const [deadline, setDeadline] = useState<UserPreferences["closingSoonDays"]>(14);
  const [sort, setSort] = useState<UserPreferences["defaultSort"]>("deadline");
  const [activeOnly, setActiveOnly] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [message, setMessage] = useState("");
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    if (!user?.uid) return;
    return subscribeUserPreferences(user.uid, (preferences) => {
      setScope(preferences.scope);
      setDeadline(preferences.closingSoonDays);
      setSort(preferences.defaultSort);
      setActiveOnly(preferences.activeOnly);
      setLoading(false);
    }, (error) => { setMessage(error); setLoading(false); });
  }, [user?.uid]);

  async function savePreferences() {
    if (!user?.uid) return;
    setSaving(true); setSaved(false); setMessage("");
    try {
      await saveUserPreferences(user.uid, { scope, closingSoonDays: deadline, defaultSort: sort, activeOnly });
      setSaved(true);
      setMessage("Your workspace defaults are synced to your Bid Finder account.");
      window.setTimeout(() => setSaved(false), 2000);
    } catch { setMessage("Your settings could not be saved. Please check your connection and try again."); }
    finally { setSaving(false); }
  }

  async function sendReset() {
    if (!user?.email) return;
    setResetting(true); setMessage("");
    try {
      await resetPassword(user.email);
      setMessage(`Password reset instructions were sent to ${user.email}.`);
    } catch { setMessage("Password reset could not be sent. Please try again."); }
    finally { setResetting(false); }
  }

  return (
    <div className="page-stack suite-settings-page">
      <PageHeader eyebrow="Workspace" title="Settings" description="Control your account, discovery defaults and deadline behaviour across Bid Finder." />

      <div className="suite-settings-layout production-settings">
        <aside className="suite-settings-sidebar">
          <section className="panel suite-account-card"><span className="suite-account-icon"><UserRound size={22} /></span><div className="avatar-large">{(profile?.displayName || user?.email || "U").slice(0, 1).toUpperCase()}</div><div><h2>{profile?.displayName || "Bid Finder user"}</h2><p>{user?.email}</p><span className="soft-badge">{profile?.role || "viewer"}</span></div></section>
          <section className="panel suite-security-card"><div className="suite-settings-mini-head"><span><ShieldCheck size={18} /></span><div><strong>Account security</strong><small>Manage access to this account.</small></div></div><button className="button secondary" type="button" onClick={sendReset} disabled={resetting || !user?.email}>{resetting ? <Loader2 className="spin" size={14} /> : <KeyRound size={14} />} Send password reset</button></section>
          <section className="panel suite-settings-status"><div><span className="status-dot healthy" /> <strong>Production workspace</strong></div><p>Your preferences are stored in Firestore under your authenticated account, not only on this browser.</p></section>
        </aside>

        <div className="suite-settings-main">
          <section className="panel suite-preferences-card">
            <div className="suite-section-title"><div><span className="eyebrow">DISCOVERY DEFAULTS</span><h2>Search preferences</h2><p>These defaults are applied when you open Find bids.</p></div><Search size={21} /></div>
            {loading ? <div className="suite-inline-loading"><Loader2 className="spin" size={16} /> Loading preferences…</div> : <div className="suite-preference-grid wide">
              <label><span>Default source coverage</span><select value={scope} onChange={(e) => setScope(e.target.value as UserPreferences["scope"])}><option value="all">Everywhere</option><option value="government">Government</option><option value="newspapers">Newspapers</option><option value="development">NGO & Development</option><option value="private">Private sector</option></select><small>Controls the source group selected when Find bids opens.</small></label>
              <label><span>Default sort order</span><select value={sort} onChange={(e) => setSort(e.target.value as UserPreferences["defaultSort"])}><option value="deadline">Nearest deadline</option><option value="newest">Newest discovered</option><option value="organization">Organization</option></select><small>Sets how search results are ordered initially.</small></label>
            </div>}
          </section>

          <section className="panel suite-preferences-card">
            <div className="suite-section-title"><div><span className="eyebrow">DEADLINE BEHAVIOUR</span><h2>Opportunity urgency</h2><p>Choose what Bid Finder considers urgent and whether completed opportunities should stay out of your normal search.</p></div><Clock3 size={21} /></div>
            <div className="suite-preference-grid wide">
              <label><span>Closing-soon threshold</span><select value={deadline} onChange={(e) => setDeadline(Number(e.target.value) as UserPreferences["closingSoonDays"])}><option value={3}>3 days</option><option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option></select><small>The Closing soon page uses this exact window.</small></label>
              <label className="suite-toggle-setting"><span>Default result policy</span><button type="button" className={activeOnly ? "setting-toggle on" : "setting-toggle"} onClick={() => setActiveOnly((value) => !value)} aria-pressed={activeOnly}><i /><b>{activeOnly ? "Open opportunities only" : "Include all current statuses"}</b></button><small>Expired opportunities remain excluded by the live-data safety gate.</small></label>
            </div>
          </section>

          <section className="panel suite-preferences-card suite-settings-summary">
            <div className="suite-settings-mini-head"><span><SlidersHorizontal size={18} /></span><div><strong>Current workspace defaults</strong><small>What will be applied across the live Bid Finder workspace.</small></div></div>
            <div className="suite-settings-summary-grid"><div><span>Coverage</span><strong>{scope === "all" ? "Everywhere" : scope === "development" ? "NGO & Development" : scope.charAt(0).toUpperCase() + scope.slice(1)}</strong></div><div><span>Closing soon</span><strong>{deadline} days</strong></div><div><span>Sort</span><strong>{sort === "deadline" ? "Nearest deadline" : sort === "newest" ? "Newest discovered" : "Organization"}</strong></div><div><span>Search policy</span><strong>{activeOnly ? "Open only" : "All current"}</strong></div></div>
          </section>

          {message && <div className={`suite-form-message ${message.includes("could not") ? "error" : "success"}`}>{message}</div>}
          <div className="suite-settings-actions"><div><BellRing size={15} /><span>Changes apply to Find bids and Closing soon after saving.</span></div><button className="button primary suite-save-settings" onClick={savePreferences} disabled={saving || loading}>{saving ? <><Loader2 className="spin" size={15} /> Saving…</> : saved ? <><Check size={15} /> Saved</> : <><Save size={15} /> Save settings</>}</button></div>
        </div>
      </div>
    </div>
  );
}
