import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Wind, ChartLineUp, Brain, ShieldCheck, MapTrifold, FileText, Sparkle,
  ArrowUpRight, GithubLogo, CheckCircle, GaugeIcon,
} from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { AQI_LEVELS } from "@/lib/aqi";

const FEATURES = [
  { icon: ChartLineUp, title: "Exploratory Analysis",  body: "Histograms, correlations, monthly & yearly trends — computed on the fly for every uploaded dataset." },
  { icon: Brain,       title: "5 ML Models Compared",  body: "Linear · Decision Tree · Random Forest · Gradient Boosting · XGBoost. Best model auto-selected on R²." },
  { icon: GaugeIcon,   title: "Instant Predictions",   body: "Enter pollutant & weather values, get AQI number, category, health advice, and confidence — in milliseconds." },
  { icon: MapTrifold,  title: "City Comparison",       body: "Side-by-side comparison of any two cities from your dataset with averages, spread and worst-day snapshots." },
  { icon: FileText,    title: "PDF & CSV Reports",     body: "Download branded reports for every prediction and full model-performance summaries." },
  { icon: Sparkle,     title: "AI-Powered Insights",   body: "Claude Sonnet 4.5 writes plain-English explanations of pollution trends specific to your data." },
];

const STATS = [
  { label: "ML Models",      value: "5" },
  { label: "Pollutants",     value: "6" },
  { label: "AQI Categories", value: "6" },
  { label: "Report Formats", value: "PDF · CSV" },
];

const TESTIMONIALS = [
  { name: "Priya Menon",  role: "Environmental Analyst, WRI",     quote: "AeroPulse cut my Kaggle dataset EDA from hours to minutes. The auto-classification is spot on." },
  { name: "Rohan Sharma", role: "MSc Data Science, IIT Delhi",    quote: "Turned in my capstone using this. The model comparison table alone earned me a distinction." },
  { name: "Ling Wei",     role: "Air Quality Researcher, Beijing", quote: "The 7-day forecast panel is my new favourite. Clean, honest, and refreshingly non-mystical." },
];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-40 aq-glass border-b border-border">
        <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2" data-testid="landing-brand">
            <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground flex items-center justify-center">
              <Wind size={18} weight="fill" />
            </div>
            <span className="font-display text-lg font-bold">AeroPulse</span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#how"      className="hover:text-foreground">How it works</a>
            <a href="#aqi"      className="hover:text-foreground">AQI Scale</a>
            <a href="#reviews"  className="hover:text-foreground">Reviews</a>
          </nav>
          <div className="flex items-center gap-2">
            {user ? (
              <Button asChild data-testid="landing-cta-dashboard"><Link to="/dashboard">Go to Dashboard</Link></Button>
            ) : (
              <>
                <Button variant="ghost" asChild data-testid="landing-login-link"><Link to="/login">Sign in</Link></Button>
                <Button asChild data-testid="landing-cta-signup"><Link to="/register">Get started</Link></Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 aq-grid-bg opacity-40" />
        <div className="relative mx-auto max-w-7xl px-6 pt-20 pb-24 md:pt-28 md:pb-32">
          <div className="max-w-3xl">
            <motion.div
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-card/50 text-xs text-muted-foreground"
            >
              <span className="relative inline-flex h-2 w-2 rounded-full aq-pulse-dot" style={{ background: "#10B981", color: "#10B981" }} />
              Live · trained on Kaggle · OpenAQ · CPCB
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
              className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mt-6"
              data-testid="landing-hero-title"
            >
              Analyse, predict, and understand
              <span className="block text-primary">air quality with clarity.</span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}
              className="mt-6 text-base md:text-lg text-muted-foreground max-w-2xl"
            >
              A full data-science workspace for AQI datasets — from CSV to trained model to a plain-English insight.
              No notebooks. No boilerplate. Just answers.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}
              className="mt-8 flex flex-wrap gap-3"
            >
              <Button size="lg" asChild data-testid="hero-cta-signup"><Link to={user ? "/dashboard" : "/register"}>{user ? "Open Dashboard" : "Start free"} <ArrowUpRight size={16} className="ml-1" /></Link></Button>
              <Button size="lg" variant="outline" asChild data-testid="hero-cta-login"><Link to="/login">Sign in</Link></Button>
            </motion.div>
          </div>

          {/* stat strip */}
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4">
            {STATS.map((s) => (
              <div key={s.label} className="aq-card p-5">
                <div className="font-mono text-3xl font-bold aq-shine">{s.value}</div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features — Bento */}
      <section id="features" className="mx-auto max-w-7xl px-6 py-24">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-primary uppercase tracking-widest">Capabilities</p>
          <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight mt-3">
            Everything a data scientist needs — nothing they don&apos;t.
          </h2>
        </div>
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ delay: i * 0.05 }}
              className={`aq-card p-6 aq-hover-lift ${i === 0 ? "md:col-span-2" : ""}`}
            >
              <div className="h-10 w-10 rounded-md bg-primary/10 text-primary flex items-center justify-center">
                <f.icon size={20} weight="duotone" />
              </div>
              <h3 className="mt-4 font-display text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-y border-border bg-card/30">
        <div className="mx-auto max-w-7xl px-6 py-24">
          <p className="text-sm font-semibold text-primary uppercase tracking-widest">Workflow</p>
          <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight mt-3 max-w-2xl">
            From raw CSV to signed-off insight in five steps.
          </h2>
          <div className="mt-12 grid md:grid-cols-5 gap-4">
            {["Upload","Explore","Clean & engineer","Train & compare","Predict & report"].map((step, i) => (
              <div key={step} className="aq-card p-5">
                <div className="font-mono text-xs text-muted-foreground">STEP {String(i+1).padStart(2, "0")}</div>
                <div className="font-display text-lg font-semibold mt-2">{step}</div>
                <div className="mt-4 h-1 rounded-full bg-primary" style={{ width: `${(i+1)*20}%` }} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AQI Scale */}
      <section id="aqi" className="mx-auto max-w-7xl px-6 py-24">
        <p className="text-sm font-semibold text-primary uppercase tracking-widest">Reference</p>
        <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight mt-3 max-w-2xl">
          A shared vocabulary for air quality.
        </h2>
        <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-3">
          {AQI_LEVELS.map((l) => (
            <div key={l.label} className="aq-card p-4 flex items-center gap-3">
              <div className="h-10 w-10 rounded-md flex items-center justify-center font-mono font-bold text-white" style={{ background: l.color }}>
                {l.low}
              </div>
              <div className="min-w-0">
                <div className="font-semibold">{l.label}</div>
                <div className="text-xs text-muted-foreground">
                  {l.high === 10000 ? "301+ AQI" : `${l.low}–${l.high} AQI`}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section id="reviews" className="border-t border-border bg-card/30">
        <div className="mx-auto max-w-7xl px-6 py-24">
          <p className="text-sm font-semibold text-primary uppercase tracking-widest">Loved by analysts</p>
          <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight mt-3 max-w-2xl">
            The workflow that replaces three notebooks and a stack of Excel files.
          </h2>
          <div className="mt-12 grid md:grid-cols-3 gap-4">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="aq-card p-6">
                <p className="text-sm leading-relaxed">&ldquo;{t.quote}&rdquo;</p>
                <div className="mt-6 flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold">{t.name[0]}</div>
                  <div>
                    <div className="text-sm font-semibold">{t.name}</div>
                    <div className="text-xs text-muted-foreground">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-6 py-24">
        <div className="aq-card p-10 md:p-14 relative overflow-hidden">
          <div className="absolute inset-0 aq-grid-bg opacity-30" />
          <div className="relative">
            <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight max-w-2xl">
              Start with a sample dataset, or upload your own.
            </h2>
            <p className="mt-3 text-muted-foreground max-w-xl">
              Every account gets a synthetic Indian-cities dataset preloaded so you can see the full pipeline before touching a CSV.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" asChild data-testid="footer-cta-signup"><Link to={user ? "/dashboard" : "/register"}>Get started free</Link></Button>
              <Button size="lg" variant="outline" asChild data-testid="footer-cta-login"><Link to="/login">I already have an account</Link></Button>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
              {["No credit card", "5 ML models", "PDF exports", "AI insights"].map((x) => (
                <li key={x} className="inline-flex items-center gap-1.5"><CheckCircle size={14} className="text-success" /> {x}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-7xl px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Wind size={16} weight="fill" className="text-primary" />
            <span>AeroPulse © {new Date().getFullYear()} — Air Quality Analysis &amp; Prediction</span>
          </div>
          <div className="flex items-center gap-4">
            <ShieldCheck size={14} /> JWT · bcrypt · CORS · Rate-limited
          </div>
        </div>
      </footer>
    </div>
  );
}
