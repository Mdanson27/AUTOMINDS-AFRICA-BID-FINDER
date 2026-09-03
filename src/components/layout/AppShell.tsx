"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Bookmark, Building2, ChevronLeft, ChevronRight, CircleGauge, Clock3, Database, LogOut, Menu, Search, Settings, Shield, X } from "lucide-react";
import { BrandLogo } from "@/components/ui/BrandLogo";
import { useAuth } from "@/components/auth/AuthProvider";

const primary = [
  ["/dashboard", "Dashboard", CircleGauge], ["/bids", "Find bids", Search], ["/closing-soon", "Closing soon", Clock3],
  ["/saved", "Saved bids", Bookmark], ["/organizations", "Organizations", Building2], ["/sources", "Sources", Database],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter(); const { user, profile, signOut } = useAuth();
  const [collapsed, setCollapsed] = useState(false); const [mobileOpen, setMobileOpen] = useState(false);
  async function logout() { await signOut(); router.replace("/login"); }

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-head"><BrandLogo compact={collapsed} /><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={20} /></button></div>
        <button className="collapse-button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}</button>
        <nav className="sidebar-nav">{primary.map(([href, label, Icon]) => <Link key={href} href={href} onClick={() => setMobileOpen(false)} className={pathname === href || (href === "/bids" && pathname.startsWith("/bids/")) ? "active" : ""}><Icon size={19} /><span>{label}</span></Link>)}</nav>
        {profile?.role === "admin" && <div className="admin-nav"><span className="nav-label">Administration</span><Link href="/admin/source-monitor" className={pathname.startsWith("/admin") ? "active" : ""}><Shield size={19} /><span>Source monitor</span></Link></div>}
        <div className="sidebar-footer">
          <Link href="/settings" className={pathname === "/settings" ? "active" : ""}><Settings size={19} /><span>Settings</span></Link>
          <button onClick={logout}><LogOut size={19} /><span>Sign out</span></button>
          <div className="user-chip"><div className="avatar">{(profile?.displayName || user?.email || "U")[0].toUpperCase()}</div><div><strong>{profile?.displayName || "Bid Finder User"}</strong><small>{user?.email}</small></div></div>
        </div>
      </aside>
      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <div className="app-content">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu size={21} /></button><div><span className="topbar-dot" /> Live workspace</div><button className="topbar-signout" onClick={logout}><LogOut size={16} /> <span>Sign out</span></button></header>
        <main className="content-inner">{children}</main>
      </div>
    </div>
  );
}
