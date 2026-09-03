"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  Bell,
  Bookmark,
  BriefcaseBusiness,
  Building2,
  CircleGauge,
  Clock3,
  Database,
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
  X,
} from "lucide-react";
import { BrandLogo } from "@/components/ui/BrandLogo";
import { useAuth } from "@/components/auth/AuthProvider";

const discovery = [
  ["/dashboard", "Overview", CircleGauge],
  ["/bids", "Find bids", Search],
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
  const { user, profile, signOut } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [quickSearch, setQuickSearch] = useState("");

  const pageTitle = useMemo(() => {
    const exact = pageNames[pathname];
    if (exact) return exact;
    if (pathname.startsWith("/bids/")) return "Bid intelligence";
    if (pathname.startsWith("/admin")) return "Source monitor";
    return "Bid Finder";
  }, [pathname]);

  async function logout() {
    await signOut();
    router.replace("/login");
  }

  function runSearch(event: React.FormEvent) {
    event.preventDefault();
    const query = quickSearch.trim();
    router.push(query ? `/bids?q=${encodeURIComponent(query)}` : "/bids");
  }

  function navLink(href: string, label: string, Icon: typeof Search) {
    const active = pathname === href || (href === "/bids" && pathname.startsWith("/bids/"));
    return (
      <Link
        key={href}
        href={href}
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
      <aside className={`sidebar suite-sidebar premium-sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="premium-sidebar-top">
          <div className="suite-sidebar-brand">
            <BrandLogo compact={collapsed} light />
            {!collapsed && (
              <div className="suite-sidebar-product">
                <strong>AutoMinds Africa</strong>
                <span>PROCUREMENT INTELLIGENCE</span>
              </div>
            )}
            <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={20} /></button>
          </div>

          <button className="premium-collapse" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>

          <Link href="/scan" className={`premium-new-scan ${pathname === "/scan" ? "active" : ""}`} title={collapsed ? "Scan newest bids" : undefined}>
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
              <Link href="/admin/source-monitor" title={collapsed ? "Source monitor" : undefined} className={pathname.startsWith("/admin") ? "active" : ""}>
                <Shield size={18} /><span>Source monitor</span>
              </Link>
            </div>
          )}
        </div>

        <div className="sidebar-footer premium-sidebar-footer">
          <div className="premium-live-state"><span className="premium-live-dot" />{!collapsed && <span>Collection network online</span>}</div>
          <Link href="/settings" title={collapsed ? "Settings" : undefined} className={pathname === "/settings" ? "active" : ""}><Settings size={18} /><span>Settings</span></Link>
          <button onClick={logout} title={collapsed ? "Sign out" : undefined}><LogOut size={18} /><span>Sign out</span></button>
          <div className="user-chip premium-user-chip">
            <div className="avatar">{(profile?.displayName || user?.email || "U")[0].toUpperCase()}</div>
            <div><strong>{profile?.displayName || "Bid Finder User"}</strong><small>{user?.email}</small></div>
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
            <Link href="/sources" className="suite-network-status premium-network-status"><span className="topbar-dot" /> Live sources</Link>
            <button className="suite-icon-action" aria-label="Notifications" title="Notifications"><Bell size={18} /></button>
            <Link href="/scan" className="suite-find-action premium-scan-action"><Radar size={16} /> <span>Scan now</span></Link>
          </div>
        </header>
        <main className="content-inner suite-content premium-content">{children}</main>
      </div>
    </div>
  );
}
