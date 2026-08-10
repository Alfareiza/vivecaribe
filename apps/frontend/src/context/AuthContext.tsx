"use client";

import PageLoading from "@/components/ui/loading/PageLoading";
import {
  login as apiLogin,
  logout as apiLogout,
  refreshAccessToken,
} from "@/lib/api";
import { getAccessToken } from "@/lib/auth/token";
import { safeCallbackUrl } from "@/lib/config";
import { useRouter, useSearchParams } from "next/navigation";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (getAccessToken()) {
        if (!cancelled) setStatus("authenticated");
        return;
      }
      const ok = await refreshAccessToken();
      if (!cancelled) {
        setStatus(ok ? "authenticated" : "unauthenticated");
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = encodeURIComponent(
        `${window.location.pathname}${window.location.search}`,
      );
      router.replace(`/signin?callbackUrl=${next}`);
    }
  }, [status, router]);

  const login = useCallback(async (email: string, password: string) => {
    await apiLogin(email, password);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setStatus("unauthenticated");
  }, []);

  const value = useMemo(
    () => ({ status, login, logout }),
    [status, login, logout],
  );

  if (status === "loading") {
    return <PageLoading label="Verificando sesión…" />;
  }

  if (status !== "authenticated") {
    return null;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

/** Redirect authenticated users away from /signin. */
export function SignInGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      if (getAccessToken()) {
        router.replace(safeCallbackUrl(searchParams.get("callbackUrl")));
        return;
      }
      const ok = await refreshAccessToken();
      if (cancelled) return;
      if (ok) {
        router.replace(safeCallbackUrl(searchParams.get("callbackUrl")));
        return;
      }
      setReady(true);
    }

    void check();
    return () => {
      cancelled = true;
    };
  }, [router, searchParams]);

  if (!ready) {
    return <PageLoading label="Verificando sesión…" className="flex-1" />;
  }

  return <>{children}</>;
}
