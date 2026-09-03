"use client";

import { useEffect } from "react";
import { useAuth } from "./AuthProvider";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading || user) return;
    const target = `${basePath}/login/`;
    if (window.location.pathname !== target) window.location.replace(target);
  }, [loading, user]);

  if (loading || !user) {
    return <div className="auth-loading"><div className="loader-ring" /><span>Opening Bid Finder…</span></div>;
  }

  return children;
}
