import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";

const AuthCtx = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const bootstrap = useCallback(async () => {
    // 1) Try existing session
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      setLoading(false);
      return;
    } catch { /* fallthrough to guest login */ }
    // 2) No session — silently log in as guest
    try {
      const { data } = await api.post("/auth/guest");
      setUser(data);
    } catch { setUser(null); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { bootstrap(); }, [bootstrap]);

  return (
    <AuthCtx.Provider value={{ user, loading, refresh: bootstrap }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
