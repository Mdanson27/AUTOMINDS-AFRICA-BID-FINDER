"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { User, onAuthStateChanged, sendPasswordResetEmail, signInWithEmailAndPassword, signOut as firebaseSignOut, updateProfile } from "firebase/auth";
import { auth } from "@/lib/firebaseClient";
import type { UserProfile } from "@/lib/types";

type AuthContextValue = {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  profileResolved: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  updateDisplayName: (displayName: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function fallbackProfile(user: User): UserProfile {
  return {
    uid: user.uid,
    email: user.email || "",
    displayName: user.displayName || "",
    role: "viewer",
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileResolved, setProfileResolved] = useState(false);

  useEffect(() => {
    let active = true;

    const unsubscribe = onAuthStateChanged(
      auth,
      (nextUser) => {
        if (!active) return;
        setUser(nextUser);

        if (!nextUser) {
          setProfile(null);
          setProfileResolved(true);
          setLoading(false);
          return;
        }

        const initial = fallbackProfile(nextUser);
        setProfile(initial);
        setProfileResolved(false);
        setLoading(false);

        void (async () => {
          try {
            const [{ doc, getDoc, serverTimestamp, setDoc }, { db }] = await Promise.all([
              import("firebase/firestore"),
              import("@/lib/firebase"),
            ]);
            if (!active) return;

            const ref = doc(db, "users", nextUser.uid);
            const snapshot = await getDoc(ref);
            if (!active) return;

            if (!snapshot.exists()) {
              try {
                await setDoc(ref, {
                  ...initial,
                  createdAt: serverTimestamp(),
                  updatedAt: serverTimestamp(),
                });
              } catch {
                // Keep the in-memory profile; onboarding can retry persistence.
              }
              if (active) setProfile(initial);
              return;
            }

            const data = snapshot.data();
            if (!active) return;
            const resolvedDisplayName = String(data.displayName || nextUser.displayName || "").trim();
            const resolvedProfile: UserProfile = {
              uid: nextUser.uid,
              email: data.email || nextUser.email || "",
              displayName: resolvedDisplayName,
              role: data.role === "admin" ? "admin" : "viewer",
            };
            setProfile(resolvedProfile);

            if (!data.displayName && resolvedDisplayName) {
              try {
                await setDoc(ref, { displayName: resolvedDisplayName, updatedAt: serverTimestamp() }, { merge: true });
              } catch {
                // The auth profile name remains a safe fallback for this session.
              }
            }
          } catch {
            if (active) setProfile(initial);
          } finally {
            if (active) setProfileResolved(true);
          }
        })();
      },
      () => {
        if (!active) return;
        setUser(null);
        setProfile(null);
        setProfileResolved(true);
        setLoading(false);
      },
    );

    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email.trim(), password);
  }, []);

  const signOut = useCallback(async () => firebaseSignOut(auth), []);

  const resetPassword = useCallback(async (email: string) => {
    await sendPasswordResetEmail(auth, email.trim());
  }, []);

  const updateDisplayName = useCallback(async (displayName: string) => {
    const name = displayName.trim().replace(/\s+/g, " ");
    if (name.length < 2) throw new Error("Enter the account holder name.");
    if (name.length > 80) throw new Error("Keep the account holder name under 80 characters.");
    if (!auth.currentUser) throw new Error("Your session is no longer available. Please sign in again.");

    const currentUser = auth.currentUser;
    const [{ doc, serverTimestamp, setDoc }, { db }] = await Promise.all([
      import("firebase/firestore"),
      import("@/lib/firebase"),
    ]);

    const currentRole = profile?.role || "viewer";
    await setDoc(doc(db, "users", currentUser.uid), {
      uid: currentUser.uid,
      email: currentUser.email || profile?.email || "",
      displayName: name,
      role: currentRole,
      updatedAt: serverTimestamp(),
    }, { merge: true });

    try { await updateProfile(currentUser, { displayName: name }); } catch {}
    setProfile((current) => current ? { ...current, displayName: name } : {
      uid: currentUser.uid,
      email: currentUser.email || "",
      displayName: name,
      role: currentRole,
    });
    setProfileResolved(true);
  }, [profile?.email, profile?.role]);

  const value = useMemo(
    () => ({ user, profile, loading, profileResolved, signIn, signOut, resetPassword, updateDisplayName }),
    [user, profile, loading, profileResolved, signIn, signOut, resetPassword, updateDisplayName],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
