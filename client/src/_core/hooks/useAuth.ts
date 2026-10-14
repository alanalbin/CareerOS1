import { trpc } from "@/lib/trpc";
import { useCallback, useEffect, useMemo, useState } from "react";

type UseAuthOptions = {
  redirectOnUnauthenticated?: boolean;
  redirectPath?: string;
};

export const getPersistedUser = () => {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("careeros_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const setPersistedUser = (user: any, token?: string) => {
  if (typeof window === "undefined") return;
  try {
    if (user) {
      localStorage.setItem("careeros_user", JSON.stringify(user));
      if (token) localStorage.setItem("careeros_token", token);
    } else {
      localStorage.removeItem("careeros_user");
      localStorage.removeItem("careeros_token");
      localStorage.removeItem("careeros_github");
      localStorage.removeItem("careeros_linkedin");
    }
    window.dispatchEvent(new Event("careeros:auth-change"));
  } catch {}
};

export function useAuth(options?: UseAuthOptions) {
  const { redirectOnUnauthenticated = false, redirectPath } = options ?? {};
  const [localUser, setLocalUser] = useState<any>(() => getPersistedUser());

  useEffect(() => {
    const handleAuthChange = () => {
      setLocalUser(getPersistedUser());
    };
    window.addEventListener("careeros:auth-change", handleAuthChange);
    return () => window.removeEventListener("careeros:auth-change", handleAuthChange);
  }, []);

  const meQuery = trpc.auth.me.useQuery(undefined, {
    retry: 1,
    refetchOnWindowFocus: true,
  });

  const logoutMutation = trpc.auth.logout.useMutation({
    onSuccess: () => {
      setPersistedUser(null);
    },
  });

  const logout = useCallback(async () => {
    try {
      setPersistedUser(null);
      await logoutMutation.mutateAsync({});
    } catch (error) {
      // Ignored
    } finally {
      window.location.href = "/login";
    }
  }, [logoutMutation]);

  // Synchronize server user with state
  useEffect(() => {
    const serverUser = meQuery.data?.user;
    if (serverUser) {
      if (JSON.stringify(serverUser) !== JSON.stringify(localUser)) {
        setPersistedUser(serverUser);
      }
    } else if (meQuery.isFetched && !meQuery.isLoading && !serverUser && localUser) {
      // Server returned no user, clear stale local session
      setPersistedUser(null);
    }
  }, [meQuery.data?.user, meQuery.isFetched, meQuery.isLoading, localUser]);

  const state = useMemo(() => {
    const user = meQuery.data?.user ?? (meQuery.isLoading ? localUser : null);
    const profile = meQuery.data?.profile ?? null;

    return {
      user,
      profile,
      loading: meQuery.isLoading && !user,
      error: meQuery.error ?? null,
      isAuthenticated: Boolean(user),
    };
  }, [
    meQuery.data,
    meQuery.error,
    meQuery.isLoading,
    localUser,
  ]);

  useEffect(() => {
    if (!redirectOnUnauthenticated) return;
    if (state.loading) return;
    if (state.user) return;
    if (typeof window === "undefined") return;

    const target = redirectPath || "/login";
    if (window.location.pathname !== target) {
      window.location.href = target;
    }
  }, [
    redirectOnUnauthenticated,
    redirectPath,
    state.loading,
    state.user,
  ]);

  return {
    ...state,
    refresh: () => meQuery.refetch(),
    logout,
  };
}
