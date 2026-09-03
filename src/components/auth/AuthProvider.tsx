"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { User, onAuthStateChanged, sendPasswordResetEmail, signInWithEmailAndPassword, signOut as firebaseSignOut } from "firebase/auth";
import { doc, getDoc, serverTimestamp, setDoc } from "firebase/firestore";
import { auth, db } from "@/lib/firebase";
import type { UserProfile } from "@/lib/types";

type AuthContextValue = {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => onAuthStateChanged(auth, async (nextUser) => {
    setUser(nextUser);
    if (!nextUser) { setProfile(null); setLoading(false); return; }
    const ref = doc(db, "users", nextUser.uid);
    const snapshot = await getDoc(ref);
    if (!snapshot.exists()) {
      const initial: UserProfile = { uid: nextUser.uid, email: nextUser.email || "", displayName: nextUser.displayName || "", role: "viewer" };
      await setDoc(ref, { ...initial, createdAt: serverTimestamp(), updatedAt: serverTimestamp() });
      setProfile(initial);
    } else {
      const data = snapshot.data();
      setProfile({ uid: nextUser.uid, email: data.email || nextUser.email || "", displayName: data.displayName || nextUser.displayName || "", role: data.role === "admin" ? "admin" : "viewer" });
    }
    setLoading(false);
  }), []);

  const signIn = useCallback(async (email: string, password: string) => { await signInWithEmailAndPassword(auth, email.trim(), password); }, []);
  const signOut = useCallback(async () => firebaseSignOut(auth), []);
  const resetPassword = useCallback(async (email: string) => { await sendPasswordResetEmail(auth, email.trim()); }, []);
  const value = useMemo(() => ({ user, profile, loading, signIn, signOut, resetPassword }), [user, profile, loading, signIn, signOut, resetPassword]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
