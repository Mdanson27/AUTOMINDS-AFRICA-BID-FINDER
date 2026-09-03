"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Bell, Bookmark, BriefcaseBusiness, Building2, ChevronLeft, ChevronRight, CircleGauge, Clock3, Database, LogOut, Menu, Search, Settings, Shield, Sparkles, X } from "lucide-react";
import { BrandLogo } from "@/components/ui/BrandLogo";
import { useAuth } from "@/components/auth/AuthProvider";

const primary = [
  ["/dashboard", "Dashboard", CircleGauge], ["/bids", "Find bids", Search], ["/closing-soon", "Closing soon", Clock3],
  ["/saved", "Saved bids", Bookmark], ["/organizations", "Organizations", Building2], ["/sources", "Sources", Database],
  ["/company", "My company", BriefcaseBusiness],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter(); const { user, profile, signOut } = useAuth();
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false); const [quickSearch, setQuickSearch] = useState("");
  async function logout() { await signOut(); router.replace("/login"); }
  function runSearch(event: React.FormEvent) { event.preventDefault(); const query = quickSearch.trim(); router.push(query ? `/bids?q=${encodeURIComponent(query)}` : "/bids"); }

  return (
    <div className={`app-shell suite-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar suite-sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="suite-sidebar-brand">
          <BrandLogo compact={collapsed} light />
          {!collapsed && <div className="suite-sidebar-product"><strong>AutoMinds Africa</strong><span>Bid Finder</span></div>}
          <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={20} /></button>
        </div>
        <button className="collapse-button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}</button>
        {!collapsed && <span className="suite-nav-label">WORKSPACE</span>}
        <nav className="sidebar-nav">{primary.map(([href, label, Icon]) => <Link key={href} href={href} title={collapsed ? label : undefined} onClick={() => setMobileOpen(false)} className={pathname === href || (href === "/bids" && pathname.startsWith("/bids/")) ? "active" : ""}><Icon size={19} /><span>{label}</span></Link>)}</nav>
        {profile?.role === "admin" && <div className="admin-nav">{!collapsed && <span className="suite-nav-label">ADMINISTRATION</span>}<Link href="/admin/source-monitor" title={collapsed ? "Source monitor" : undefined} className={pathname.startsWith("/admin") ? "active" : ""}><Shield size={19} /><span>Source monitor</span></Link></div>}
        <div className="sidebar-footer">
          <Link href="/settings" title={collapsed ? "Settings" : undefined} className={pathname === "/settings" ? "active" : ""}><Settings size={19} /><span>Settings</span></Link>
          <button onClick={logout} title={collapsed ? "Sign out" : undefined}><LogOut size={19} /><span>Sign out</span></button>
          <div className="user-chip"><div className="avatar">{(profile?.displayName || user?.email || "U")[0].toUpperCase()}</div><div><strong>{profile?.displayName || "Bid Finder User"}</strong><small>{user?.email}</small></div></div>
        </div>
      </aside>
      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <div className="app-content">
        <header className="topbar suite-topbar">
          <button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu size={21} /></button>
          <form className="suite-global-search" onSubmit={runSearch}><Search size={17} /><input value={quickSearch} onChange={(e) => setQuickSearch(e.target.value)} placeholder="Search bids, organizations or references…" /><kbd>↵</kbd></form>
          <div className="suite-topbar-actions">
            <Link href="/sources" className="suite-network-status"><span className="topbar-dot" /> Source network</Link>
            <button className="suite-icon-action" aria-label="Notifications" title="Notifications"><Bell size={18} /></button>
            <Link href="/bids" className="suite-find-action"><Sparkles size={16} /> <span>Find a bid</span></Link>
          </div>
        </header>
        <main className="content-inner suite-content">{children}</main>
      </div>
    </div>
  );
}
