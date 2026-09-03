"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LockKeyhole, Mail, SearchCheck, ShieldCheck } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { BidScoutMascot, MascotMode } from "./BidScoutMascot";
import { BrandLogo } from "@/components/ui/BrandLogo";

export function LoginScreen() {
  const { user, loading: authLoading, signIn, resetPassword } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [focused, setFocused] = useState<"email" | "password" | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [resetSent, setResetSent] = useState(false);

  useEffect(() => { if (!authLoading && user) router.replace("/dashboard"); }, [authLoading, router, user]);

  const mascotMode: MascotMode = useMemo(() => {
    if (busy) return "loading";
    if (focused === "password" && !showPassword) return "password";
    if (focused === "email") return "email";
    return "idle";
  }, [busy, focused, showPassword]);

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setMessage(""); setBusy(true);
    try { await signIn(email, password); router.replace("/dashboard"); }
    catch (error) { setMessage(firebaseMessage(error)); setBusy(false); }
  }

  async function forgot() {
    if (!email.trim()) { setMessage("Enter your email first, then choose reset password."); return; }
    try { await resetPassword(email); setResetSent(true); setMessage(""); }
    catch (error) { setMessage(firebaseMessage(error)); }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <div className="story-brand"><BrandLogo light /></div>
        <div className="story-content">
          <span className="story-kicker"><SearchCheck size={16} /> Uganda procurement intelligence</span>
          <h1>Find the opportunity<br />before the deadline finds you.</h1>
          <p>Monitor Uganda’s procurement landscape from one focused workspace — government portals, newspapers, organizations and more.</p>
          <div className="story-points"><span><ShieldCheck size={17} /> Verified source trail</span><span><SearchCheck size={17} /> One normalized bid record</span></div>
        </div>
        <div className="network-art" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
        <p className="story-footer">AutoMinds Africa · Work smarter. Grow faster.</p>
      </section>

      <section className="login-form-side">
        <div className="mobile-brand"><BrandLogo /></div>
        <div className="login-card">
          <BidScoutMascot mode={mascotMode} emailProgress={Math.min(email.length / 25, 1)} />
          <div className="login-heading">
            <h2>Welcome back</h2>
            <p>Sign in to your Bid Finder workspace.</p>
          </div>
          <form onSubmit={submit} className="login-form">
            <label className={`login-field ${focused === "email" ? "active" : ""}`}><Mail size={18} /><span><small>Email address</small><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} onFocus={() => setFocused("email")} onBlur={() => setFocused(null)} placeholder="you@company.com" required autoComplete="email" /></span></label>
            <label className={`login-field ${focused === "password" ? "active" : ""}`}><LockKeyhole size={18} /><span><small>Password</small><input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} onFocus={() => setFocused("password")} onBlur={() => setFocused(null)} placeholder="Enter your password" required autoComplete="current-password" /></span><button type="button" className="password-toggle" onMouseDown={(e) => e.preventDefault()} onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></label>
            <div className="login-meta"><label className="remember"><input type="checkbox" /> <span>Keep me signed in</span></label><button type="button" className="link-button" onClick={forgot}>Forgot password?</button></div>
            {message && <p className="form-error">{message}</p>}
            {resetSent && <p className="form-success">Password reset email sent.</p>}
            <button className="login-submit" disabled={busy}>{busy ? <><span className="tiny-spinner" /> Checking today’s opportunities…</> : "Sign in to Bid Finder"}</button>
          </form>
          <p className="login-security"><ShieldCheck size={14} /> Access is protected by Firebase Authentication and Firestore rules.</p>
        </div>
      </section>
    </main>
  );
}

function firebaseMessage(error: unknown) {
  const text = error instanceof Error ? error.message : "Sign in failed.";
  if (text.includes("invalid-credential")) return "That email or password does not match our records.";
  if (text.includes("too-many-requests")) return "Too many attempts. Please try again shortly.";
  if (text.includes("network-request-failed")) return "Network error. Check your connection and try again.";
  return text.replace("Firebase: ", "").replace(/\s*\(auth\/[^)]+\)\.?$/, "");
}
