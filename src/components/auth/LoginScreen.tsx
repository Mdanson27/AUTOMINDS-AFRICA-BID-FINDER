"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, Eye, EyeOff, LockKeyhole, Mail, Search, ShieldCheck, Target, Telescope } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { BidScoutMascot, MascotMode } from "./BidScoutMascot";
import { BrandLogo } from "@/components/ui/BrandLogo";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const dashboardUrl = `${basePath}/dashboard/`;

export function LoginScreen() {
  const { user, loading: authLoading, signIn, resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [focused, setFocused] = useState<"email" | "password" | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [resetSent, setResetSent] = useState(false);
  const [result, setResult] = useState<"idle" | "error" | "success">("idle");

  useEffect(() => {
    if (!authLoading && user && window.location.pathname !== dashboardUrl) {
      window.location.replace(dashboardUrl);
    }
  }, [authLoading, user]);

  const mascotMode: MascotMode = useMemo(() => {
    if (result === "success") return "success";
    if (result === "error") return "error";
    if (busy) return "loading";
    if (focused === "password" && !showPassword) return "password";
    if (focused === "email") return "email";
    return "idle";
  }, [busy, focused, result, showPassword]);

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setMessage(""); setResetSent(false); setResult("idle"); setBusy(true);
    try {
      await signIn(email, password);
      setBusy(false); setResult("success");
      await new Promise((resolve) => setTimeout(resolve, 360));
      window.location.replace(dashboardUrl);
    } catch (error) {
      setMessage(authMessage(error)); setBusy(false); setResult("error");
    }
  }

  async function forgot() {
    if (!email.trim()) { setMessage("Enter your email first, then choose reset password."); setResult("error"); return; }
    try { await resetPassword(email); setResetSent(true); setMessage(""); setResult("idle"); }
    catch (error) { setMessage(authMessage(error)); setResult("error"); }
  }

  return (
    <main className="suite-login-page">
      <section className="suite-login-story">
        <div className="suite-grid-art" aria-hidden="true" />
        <div className="suite-login-brand">
          <span className="suite-logo-tile"><BrandLogo /></span>
          <div><strong>AUTOMINDS AFRICA</strong><small>BID FINDER</small></div>
        </div>

        <div className="suite-story-content">
          <span className="suite-story-kicker">PROCUREMENT INTELLIGENCE WORKSPACE</span>
          <h1>Find the right opportunity.<br /><em>Move before the deadline.</em></h1>
          <h2>Search wider. Decide faster. Bid smarter.</h2>
          <p>Bring Uganda’s procurement landscape into one focused workspace — public portals, newspapers, organizations and development partners.</p>
          <div className="suite-story-features">
            <article><Search size={20} /><strong>Search every source</strong><span>One place to discover opportunities.</span></article>
            <article><Target size={20} /><strong>Track what matters</strong><span>Keep priority bids and deadlines close.</span></article>
            <article><BarChart3 size={20} /><strong>Build intelligence</strong><span>Turn scattered notices into decisions.</span></article>
          </div>
        </div>

        <div className="suite-story-footer"><span>© 2026 AutoMinds Africa</span><span>Work smarter. Grow faster.</span></div>
      </section>

      <section className="suite-login-form-side">
        <div className="suite-login-card">
          <BidScoutMascot mode={mascotMode} emailProgress={Math.min(email.length / 25, 1)} />
          <div className="suite-login-heading">
            <span className="suite-security-icon"><ShieldCheck size={22} /></span>
            <h2>Welcome back!</h2>
            <p>Use your account to continue to the Bid Finder workspace.</p>
          </div>

          <form onSubmit={submit} className="suite-login-form">
            <label><span>Email address</span><div className={`suite-login-input ${focused === "email" ? "active" : ""}`}><Mail size={19} /><input type="email" value={email} onChange={(e) => { setEmail(e.target.value); setResult("idle"); }} onFocus={() => setFocused("email")} onBlur={() => setFocused(null)} required autoComplete="email" /></div></label>
            <label><span>Password</span><div className={`suite-login-input ${focused === "password" ? "active" : ""}`}><LockKeyhole size={19} /><input type={showPassword ? "text" : "password"} value={password} onChange={(e) => { setPassword(e.target.value); setResult("idle"); }} onFocus={() => setFocused("password")} onBlur={() => setFocused(null)} required autoComplete="current-password" /><button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={19} /> : <Eye size={19} />}</button></div></label>
            <div className="suite-login-meta"><label className="suite-remember"><input type="checkbox" /> <span>Remember this device</span></label><button type="button" onClick={forgot}>Forgot password?</button></div>
            {message && <p className="form-error">{message}</p>}
            {resetSent && <p className="form-success">Password reset email sent.</p>}
            <button className="suite-login-submit" disabled={busy}>{busy ? <><span className="tiny-spinner" /> Opening workspace…</> : <><Telescope size={18} /> Sign in securely</>}</button>
          </form>

          <div className="suite-secure-note"><ShieldCheck size={19} /><div><strong>Secure workspace access</strong><span>Your account and procurement workspace are protected with industry-standard controls.</span></div></div>
        </div>
      </section>
    </main>
  );
}

function authMessage(error: unknown) {
  const text = error instanceof Error ? error.message : "Sign in failed.";
  if (text.includes("invalid-credential")) return "That email or password does not match our records.";
  if (text.includes("too-many-requests")) return "Too many attempts. Please try again shortly.";
  if (text.includes("network-request-failed")) return "Network error. Check your connection and try again.";
  return text.replace("Firebase: ", "").replace(/\s*\(auth\/[^)]+\)\.?$/, "");
}
