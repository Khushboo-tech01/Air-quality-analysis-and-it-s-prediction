import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Wind, Eye, EyeSlash } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const res = await login(email.trim(), password);
    setLoading(false);
    if (res.ok) {
      toast.success("Welcome back!");
      const nextParam = searchParams.get("next");
      const to = nextParam || location.state?.from?.pathname || "/dashboard";
      nav(to, { replace: true });
    } else {
      toast.error(res.error);
    }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2">
      {/* Left promo panel */}
      <div className="hidden md:flex flex-col justify-between p-10 border-r border-border bg-card relative overflow-hidden">
        <div className="absolute inset-0 aq-grid-bg opacity-25" />
        <Link to="/" className="relative flex items-center gap-2" data-testid="auth-brand">
          <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center"><Wind size={18} weight="fill" /></div>
          <span className="font-display text-lg font-bold">AeroPulse</span>
        </Link>
        <div className="relative">
          <h2 className="font-display text-4xl font-bold tracking-tight max-w-md">
            The full AQI pipeline. In one workspace.
          </h2>
          <p className="mt-4 text-muted-foreground max-w-md">
            Upload · Analyse · Train · Predict · Report — with beautiful charts and PDF exports.
          </p>
        </div>
        <div className="relative text-xs text-muted-foreground">© {new Date().getFullYear()} AeroPulse</div>
      </div>

      {/* Form */}
      <div className="flex flex-col items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          <div className="md:hidden flex items-center gap-2 mb-6">
            <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center"><Wind size={18} weight="fill" /></div>
            <span className="font-display text-lg font-bold">AeroPulse</span>
          </div>
          <h1 className="font-display text-3xl font-bold tracking-tight">Sign in to your account</h1>
          <p className="text-sm text-muted-foreground mt-2">New to AeroPulse? <Link to="/register" className="text-primary font-semibold hover:underline" data-testid="link-to-register">Create an account</Link></p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email" type="email" required autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email-input"
                className="mt-1.5"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link to="/forgot" className="text-xs text-primary hover:underline" data-testid="link-forgot">Forgot?</Link>
              </div>
              <div className="relative mt-1.5">
                <Input
                  id="password" type={show ? "text" : "password"} required autoComplete="current-password"
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  data-testid="login-password-input"
                  placeholder="••••••••"
                />
                <button type="button" onClick={() => setShow((s) => !s)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground" data-testid="toggle-password">
                  {show ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} data-testid="remember-me" />
              Remember me
            </label>
            <Button type="submit" className="w-full" size="lg" disabled={loading} data-testid="login-submit-btn">
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <div className="mt-6 rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
            <div className="font-medium text-foreground mb-1">Demo admin</div>
            <div className="font-mono">admin@aqi.io · admin123</div>
          </div>
        </div>
      </div>
    </div>
  );
}
