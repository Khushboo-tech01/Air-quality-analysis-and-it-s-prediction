import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { unwrapError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
export default function Reset() {
  const [params] = useSearchParams(), nav = useNavigate(); const [password, setPassword] = useState(""); const [loading, setLoading] = useState(false);
  const submit = async (e) => { e.preventDefault(); const token = params.get("token"); if (!token) return toast.error("A reset token is required."); setLoading(true); try { await api.post("/auth/reset-password", { token, password }); toast.success("Password updated. Please sign in."); nav("/login"); } catch (err) { toast.error(unwrapError(err)); } finally { setLoading(false); } };
  return <div className="min-h-screen flex items-center justify-center p-6"><form onSubmit={submit} className="aq-card p-8 w-full max-w-md space-y-5"><h1 className="font-display text-3xl font-bold">Choose a new password</h1><div><Label htmlFor="password">New password</Label><Input id="password" className="mt-2" type="password" minLength={6} value={password} onChange={e=>setPassword(e.target.value)} required /></div><Button className="w-full" disabled={loading}>{loading ? "Updating…" : "Update password"}</Button><Link className="block text-center text-sm text-primary" to="/login">Back to sign in</Link></form></div>;
}
