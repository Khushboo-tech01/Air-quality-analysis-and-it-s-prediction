import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Wind } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const nav = useNavigate();

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 6) return toast.error("Password must be at least 6 characters.");
    if (form.password !== form.confirmPassword) return toast.error("Passwords do not match.");
    setLoading(true);
    const res = await register(form.email.trim(), form.password, form.name.trim());
    setLoading(false);
    if (res.ok) {
      toast.success("Account created — welcome to AeroPulse!");
      nav("/dashboard");
    } else {
      toast.error(res.error);
    }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between p-10 border-r border-border bg-card relative overflow-hidden">
        <div className="absolute inset-0 aq-grid-bg opacity-25" />
        <Link to="/" className="relative flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center"><Wind size={18} weight="fill" /></div>
          <span className="font-display text-lg font-bold">AeroPulse</span>
        </Link>
        <div className="relative">
          <h2 className="font-display text-4xl font-bold tracking-tight max-w-md">
            Free forever for personal projects.
          </h2>
          <p className="mt-4 text-muted-foreground max-w-md">
            A synthetic sample dataset ships with every account. Explore the whole pipeline in under 60 seconds.
          </p>
        </div>
        <div className="relative text-xs text-muted-foreground">© {new Date().getFullYear()} AeroPulse</div>
      </div>

      <div className="flex flex-col items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          <h1 className="font-display text-3xl font-bold tracking-tight">Create your account</h1>
          <p className="text-sm text-muted-foreground mt-2">Already registered? <Link to="/login" className="text-primary font-semibold hover:underline" data-testid="link-to-login">Sign in</Link></p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <Label htmlFor="name">Full name</Label>
              <Input id="name" required value={form.name} onChange={set("name")} data-testid="register-name-input" className="mt-1.5" placeholder="Ada Lovelace" />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required value={form.email} onChange={set("email")} data-testid="register-email-input" className="mt-1.5" placeholder="you@example.com" />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required minLength={6} value={form.password} onChange={set("password")} data-testid="register-password-input" className="mt-1.5" placeholder="Min 6 characters" />
            </div>
            <div>
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input id="confirmPassword" type="password" required minLength={6} value={form.confirmPassword} onChange={set("confirmPassword")} data-testid="register-confirm-password-input" className="mt-1.5" placeholder="Repeat password" />
            </div>
            <Button type="submit" className="w-full" size="lg" disabled={loading} data-testid="register-submit-btn">
              {loading ? "Creating…" : "Create account"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
