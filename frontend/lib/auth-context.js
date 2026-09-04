"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api, setTokens, clearTokens, getAccessToken, onSessionExpired } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // When a request surfaces an unrecoverable 401 (expired session), drop the
    // user state; RequireAuth then redirects to /login?next=…
    onSessionExpired(() => {
      clearTokens();
      setUser(null);
    });
    return () => onSessionExpired(null);
  }, []);

  useEffect(() => {
    async function init() {
      if (getAccessToken()) {
        try {
          setUser(await api.me());
        } catch {
          clearTokens();
        }
      }
      setLoading(false);
    }
    init();
  }, []);

  async function login(email, password) {
    const tokens = await api.login({ email, password });
    setTokens(tokens);
    const me = await api.me();
    setUser(me);
    return me;
  }

  async function register(full_name, email, password, tenant_name) {
    const tokens = await api.register({ full_name, email, password, tenant_name });
    setTokens(tokens);
    const me = await api.me();
    setUser(me);
    return me;
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      clearTokens();
    }
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
