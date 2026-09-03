"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, router, user]);
  if (loading || !user) return <div className="auth-loading"><div className="loader-ring" /><span>Opening Bid Finder…</span></div>;
  return children;
}
