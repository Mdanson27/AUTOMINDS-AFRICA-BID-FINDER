"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  ArrowRight,
  Bell,
  Bookmark,
  BriefcaseBusiness,
  Building2,
  CircleGauge,
  ClipboardList,
  Clock3,
  Database,
  Gift,
  LogOut,
  Menu,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Radar,
  Search,
  Settings,
  Shield,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import { BrandLogo } from "@/components/ui/BrandLogo";
import { useAuth } from "@/components/auth/AuthProvider";

const discovery = [
  ["/dashboard", "Overview", CircleGauge],
  ["/bids", "Find bids", Search],
  ["/grants", "Grants", Gift],
  ["/plans", "Procurement plans", ClipboardList],
  ["/papers", "Current papers", Newspaper],
  ["/closing-soon", "Closing soon", Clock3],
  ["/saved", "Saved bids", Bookmark],
] as const;

const intelligence = [
  ["/sources", "Source network", Database],
  ["/organizations", "Organizations", Building2],
  ["/company", "My company", BriefcaseBusiness],
] as const;

const pageNames: Record<string, string> = {
  "/dashboard": "Procurement overview",
  "/bids": "Find bids",
  "/grants": "Grant opportunities",
  "/plans": "Procurement plans",
  "/papers": "Current papers",
  "/scan": "Scan center",
  "/closing-soon": "Closing soon",
  "/saved": "Saved bids",
  "/organizations": "Organizations",
  "/sources": "Source network",
  "/company": "My company",
  "/settings": "Settings",
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, profile, profileResolved, signOut, updateDisplayName } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [quickSearch, setQuickSearch] = useState("");
  const [nameDraft, setNameDraft] = useState("");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameError, setNameError] = useState("");

  const pageTitle = useMemo(() => {
    const exact = pageNames[pathname];
    if (exact) return exact;
    if (pathname.startsWith("/bids/")) return "Bid intelligence";
    if (pathname.startsWith("/admin")) return "Source monitor";
    return "Bid Finder";
  }, [pathname]);

  const needsAccountName = Boolean(user && profileResolved && !profile?.displayName?.trim());

  async function logout() {
    await signOut();
    router.replace("/login");
  }

  async function saveAccountName(event: React.FormEvent) {
    event.preventDefault();
    setNameError("");
    setNameSaving(true);
    try {
      await updateDisplayName(nameDraft);
      setNameDraft("");
    } catch (error) {
      setNameError(error instanceof Error ? error.message : "We could not save your name. Please try again.");
    } finally {
      setNameSaving(false);
    }
  }

  function runSearch(event: React.FormEvent) {
    event.preventDefault();
    const query = quickSearch.trim();
    router.push(query ? `/bids?q=${encodeURIComponent(query)}` : "/bids");
  }

  function warmRoute(href: string) {
    router.prefetch(href);
  }

  function navLink(href: string, label: string, Icon: typeof Search) {
    const active = pathname === href || (href === "/bids" && pathname.startsWith("/bids/"));
    return (
      <Link
        key={href}
        href={href}
        prefetch={false}
        onMouseEnter={() => warmRoute(href)}
        onFocus={() => warmRoute(href)}
        title={collapsed ? label : undefined}
        onClick={() => setMobileOpen(false)}
        className={active ? "active" : ""}
      >
        <Icon size={18} />
        <span>{label}</span>
      </Link>
    );
  }

  return (
    <div className={`app-shell suite-shell premium-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      {needsAccountName && (
        <div className="account-name-gate" role="dialog" aria-modal="true" aria-labelledby="account-name-title">
          <div className="account-name-card">
            <div className="account-name-icon"><UserRound size={24} /></div>
            <span className="eyebrow">FINISH ACCOUNT SETUP</span>
            <h2 id="account-name-title">What should Bid Finder call you?</h2>
            <p>Add the account holder name once. We’ll use it for your workspace identity and personal greetings.</p>
            <form onSubmit={saveAccountName}>
              <label>
                <span>Account holder name</span>
                <input
                  autoFocus
                  value={nameDraft}
                  onChange={(event) => { setNameDraft(event.target.value); setNameError(""); }}
                  placeholder="e.g. Danson Mushabe"
                  autoComplete="name"
                  minLength={2}
                  maxLength={80}
                  required
                />
              </label>
              {nameError && <div className="account-name-error">{nameError}</div>}
              <button type="submit" disabled={nameSaving || nameDraft.trim().length < 2}>
                {nameSaving ? "Saving your name…" : <>Continue to Bid Finder <ArrowRight size={17} /></>}
              </button>
            </form>
            <small>Signed in as {user?.email}</small>
          </div>
        </div>
      )}

      <aside className={`sidebar suite-sidebar premium-sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="premium-sidebar-top">
          <div className="suite-sidebar-brand modern-sidebar-brand">
            {!collapsed && <>
              <BrandLogo light />
              <div className="suite-sidebar-product">
                <strong>AutoMinds Africa</strong>
                <span>PROCUREMENT INTELLIGENCE</span>
              </div>
            </>}
            <div className="modern-sidebar-actions">
              <button className="premium-collapse" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
                {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
              </button>
              <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={20} /></button>
            </div>
          </div>

          <Link href="/scan" prefetch={false} onMouseEnter={() => warmRoute("/scan")} onFocus={() => warmRoute("/scan")} className={`premium-new-scan ${pathname === "/scan" ? "active" : ""}`} title={collapsed ? "Scan newest bids" : undefined}>
            <Sparkles size={18} />
            <span>Scan newest bids</span>
          </Link>
        </div>

        <div className="premium-nav-scroll">
          {!collapsed && <span className="suite-nav-label">DISCOVERY</span>}
          <nav className="sidebar-nav premium-nav">{discovery.map(([href, label, Icon]) => navLink(href, label, Icon))}</nav>

          {!collapsed && <span className="suite-nav-label premium-second-label">INTELLIGENCE</span>}
          <nav className="sidebar-nav premium-nav">{intelligence.map(([href, label, Icon]) => navLink(href, label, Icon))}</nav>

          {profile?.role === "admin" && (
            <div className="admin-nav premium-admin-nav">
              {!collapsed && <span className="suite-nav-label premium-second-label">ADMINISTRATION</span>}
              <Link href="/admin/source-monitor" prefetch={false} onMouseEnter={() => warmRoute("/admin/source-monitor")} onFocus={() => warmRoute("/admin/source-monitor")} title={collapsed ? "Source monitor" : undefined} className={pathname.startsWith("/admin") ? "active" : ""}>
                <Shield size={18} /><span>Source monitor</span>
              </Link>
            </div>
          )}
        </div>

        <div className="sidebar-footer premium-sidebar-footer">
          <div className="premium-live-state"><span className="premium-live-dot" />{!collapsed && <span>Collection network online</span>}</div>
          <Link href="/settings" prefetch={false} onMouseEnter={() => warmRoute("/settings")} onFocus={() => warmRoute("/settings")} title={collapsed ? "Settings" : undefined} className={pathname === "/settings" ? "active" : ""}><Settings size={18} /><span>Settings</span></Link>
          <button onClick={logout} title={collapsed ? "Sign out" : undefined}><LogOut size={18} /><span>Sign out</span></button>
          <div className="user-chip premium-user-chip">
            <div className="avatar">{(profile?.displayName || user?.email || "U")[0].toUpperCase()}</div>
            <div><strong>{profile?.displayName || "Account setup"}</strong><small>{user?.email}</small></div>
          </div>
        </div>
      </aside>

      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}

      <div className="app-content premium-app-content">
        <header className="topbar suite-topbar premium-topbar">
          <button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu size={21} /></button>
          <div className="premium-page-context"><span>AutoMinds Bid Finder</span><strong>{pageTitle}</strong></div>
          <form className="suite-global-search premium-global-search" onSubmit={runSearch}>
            <Search size={17} />
            <input value={quickSearch} onChange={(e) => setQuickSearch(e.target.value)} placeholder="Search procurement intelligence…" />
            <kbd>↵</kbd>
          </form>
          <div className="suite-topbar-actions premium-topbar-actions">
            <Link href="/sources" prefetch={false} onMouseEnter={() => warmRoute("/sources")} onFocus={() => warmRoute("/sources")} className="suite-network-status premium-network-status"><span className="topbar-dot" /> Live sources</Link>
            <button className="suite-icon-action" aria-label="Notifications" title="Notifications"><Bell size={18} /></button>
            <Link href="/scan" prefetch={false} onMouseEnter={() => warmRoute("/scan")} onFocus={() => warmRoute("/scan")} className="suite-find-action premium-scan-action"><Radar size={16} /> <span>Scan now</span></Link>
          </div>
        </header>
        <main className="content-inner suite-content premium-content">{children}</main>
      </div>
    </div>
  );
}
