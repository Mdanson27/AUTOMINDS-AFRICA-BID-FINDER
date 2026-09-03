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

  useEffect(() => {
    let active = true;

    const unsubscribe = onAuthStateChanged(
      auth,
      (nextUser) => {
        if (!active) return;
        setUser(nextUser);

        if (!nextUser) {
          setProfile(null);
          setLoading(false);
          return;
        }

        // A valid authenticated session is enough to open the application.
        // Profile hydration must never hold the protected route on a spinner,
        // especially while the procurement data store is being provisioned.
        const initial = fallbackProfile(nextUser);
        setProfile(initial);
        setLoading(false);

        void (async () => {
          try {
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
                // Keep the in-memory profile. Persistence is optional for boot.
              }
              return;
            }

            const data = snapshot.data();
            if (!active) return;
            setProfile({
              uid: nextUser.uid,
              email: data.email || nextUser.email || "",
              displayName: data.displayName || nextUser.displayName || "",
              role: data.role === "admin" ? "admin" : "viewer",
            });
          } catch {
            // Keep the safe fallback profile and leave the workspace usable.
          }
        })();
      },
      () => {
        if (!active) return;
        setUser(null);
        setProfile(null);
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

  const value = useMemo(
    () => ({ user, profile, loading, signIn, signOut, resetPassword }),
    [user, profile, loading, signIn, signOut, resetPassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
