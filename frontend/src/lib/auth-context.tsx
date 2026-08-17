"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { logout as apiLogout, restoreSession, type UserProfile } from "@/lib/api";

interface AuthState {
  user: UserProfile | null;
  /** True until the initial session restore finishes. */
  loading: boolean;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // On first load the access token is gone (it lives in memory only), so the
  // session is rebuilt from the httpOnly refresh cookie. Until that resolves,
  // `loading` is true and guarded pages must not decide anything — otherwise a
  // signed-in user gets bounced to /login on every refresh.
  useEffect(() => {
    let cancelled = false;
    restoreSession()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signOut = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    setUser(await restoreSession());
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
