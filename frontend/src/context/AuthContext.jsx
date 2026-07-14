import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";

const AuthCtx = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const bootstrap = useCallback(async () => {
    try { const { data } = await api.get("/auth/me"); setUser(data); }
    catch { setUser(null); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { bootstrap(); }, [bootstrap]);
  const login = async (email, password) => {
    try { const { data } = await api.post("/auth/login", { email, password }); setUser(data); return { ok: true }; }
    catch (error) { return { ok: false, error: error?.response?.data?.detail || "Unable to sign in." }; }
  };
  const register = async (email, password, name) => {
    try { const { data } = await api.post("/auth/register", { email, password, name }); setUser(data); return { ok: true }; }
    catch (error) { return { ok: false, error: error?.response?.data?.detail || "Unable to create account." }; }
  };
  const logout = async () => { try { await api.post("/auth/logout"); } finally { setUser(null); } };
  return <AuthCtx.Provider value={{ user, loading, refresh: bootstrap, login, register, logout }}>{children}</AuthCtx.Provider>;
}
export const useAuth = () => useContext(AuthCtx);
