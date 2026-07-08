import { useState } from "react";
import { Link } from "react-router-dom";
import api, { unwrapError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Wind } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Forgot() {
  const [email, setEmail] = useState("");
  const [sent, setSent]   = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
      toast.success("If this account exists, a reset link has been sent.");
    } catch (err) {
      toast.error(unwrapError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12 bg-background">
      <div className="w-full max-w-md aq-card p-8">
        <Link to="/" className="flex items-center gap-2 mb-6" data-testid="forgot-brand">
          <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center"><Wind size={18} weight="fill" /></div>
          <span className="font-display text-lg font-bold">AeroPulse</span>
        </Link>
        <h1 className="font-display text-3xl font-bold tracking-tight">Reset your password</h1>
        <p className="mt-2 text-sm text-muted-foreground">Enter your email and we&apos;ll send you a reset link.</p>
        {!sent ? (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1.5" data-testid="forgot-email-input" />
            </div>
            <Button type="submit" className="w-full" size="lg" disabled={loading} data-testid="forgot-submit-btn">
              {loading ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        ) : (
          <div className="mt-6 rounded-md border border-border p-4 text-sm">
            Check your email — if that account exists, you&apos;ll receive a reset link within a minute.
          </div>
        )}
        <div className="mt-6 text-center">
          <Link to="/login" className="text-sm text-primary hover:underline" data-testid="back-to-login">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
