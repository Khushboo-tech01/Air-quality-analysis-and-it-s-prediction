import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, PageBody, StatCard } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { AQIBadge } from "@/components/AQIBadge";
import { UploadSimple, Brain, Compass, Database, ChartLineUp, ArrowRight, Sparkle } from "@phosphor-icons/react";
import { motion } from "framer-motion";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function Dashboard() {
  const { user } = useAuth();
  const [datasets, setDatasets]   = useState([]);
  const [predictions, setPreds]   = useState([]);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [ds, hs] = await Promise.all([api.get("/datasets"), api.get("/history")]);
        setDatasets(ds.data);
        setPreds(hs.data);
      } finally { setLoading(false); }
    })();
  }, []);

  const trainedCount = datasets.filter((d) => d.trained).length;
  const chartData = [...predictions].reverse().map((p, i) => ({
    idx: i + 1,
    aqi: p.aqi,
  }));

  return (
    <>
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] || "there"}`}
        subtitle="Your air-quality workspace at a glance. Upload a dataset, train models, or run a prediction."
        actions={
          <>
            <Button asChild variant="outline" data-testid="dashboard-upload-btn"><Link to="/upload"><UploadSimple size={16} className="mr-1.5" />Upload CSV</Link></Button>
            <Button asChild data-testid="dashboard-predict-btn"><Link to="/predict"><Compass size={16} className="mr-1.5" />New Prediction</Link></Button>
          </>
        }
      />
      <PageBody>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Datasets"    value={datasets.length}   icon={Database}     testid="stat-datasets" />
          <StatCard label="Trained"     value={trainedCount}      icon={Brain}        testid="stat-trained" />
          <StatCard label="Predictions" value={predictions.length}icon={Compass}      testid="stat-predictions" />
          <StatCard label="Best avg AQI" value={
            predictions.length
              ? Math.round(predictions.reduce((s, p) => s + p.aqi, 0) / predictions.length)
              : "—"
          } icon={ChartLineUp} testid="stat-avg-aqi" />
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Chart: recent predictions */}
          <div className="lg:col-span-2 aq-card p-6" data-testid="chart-recent-predictions">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display text-xl font-semibold">Recent predictions</h2>
                <p className="text-sm text-muted-foreground">AQI trend across your last {chartData.length || 0} predictions.</p>
              </div>
              <Button variant="ghost" size="sm" asChild><Link to="/predict">New <ArrowRight size={14} className="ml-1" /></Link></Button>
            </div>
            <div className="h-64 mt-4">
              {chartData.length > 0 ? (
                <ResponsiveContainer>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="dashArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#2563EB" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#2563EB" stopOpacity={0}   />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="idx" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6 }} />
                    <Area type="monotone" dataKey="aqi" stroke="#2563EB" fill="url(#dashArea)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                  No predictions yet — <Link to="/predict" className="text-primary hover:underline ml-1">create your first</Link>.
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="aq-card p-6 flex flex-col" data-testid="quick-actions">
            <h2 className="font-display text-xl font-semibold">Quick actions</h2>
            <div className="mt-4 space-y-2 flex-1">
              {[
                { to: "/upload",  icon: UploadSimple, title: "Upload dataset", body: "Any CSV up to 25 MB" },
                { to: "/train",   icon: Brain,        title: "Train models",    body: "Compare 5 regressors" },
                { to: "/predict", icon: Compass,      title: "Predict AQI",     body: "Instant classification" },
                { to: "/reports", icon: Sparkle,      title: "Download reports",body: "PDF · CSV exports" },
              ].map((a) => (
                <Link key={a.to} to={a.to} className="flex items-center gap-3 p-3 -mx-2 rounded-md hover:bg-accent transition-colors">
                  <div className="h-9 w-9 rounded-md bg-primary/10 text-primary flex items-center justify-center"><a.icon size={16} /></div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{a.title}</div>
                    <div className="text-xs text-muted-foreground truncate">{a.body}</div>
                  </div>
                  <ArrowRight size={14} className="text-muted-foreground" />
                </Link>
              ))}
            </div>
          </div>
        </div>

        {/* Recent items */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="aq-card p-6" data-testid="recent-datasets">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl font-semibold">Recent datasets</h2>
              <Button variant="ghost" size="sm" asChild><Link to="/upload">Manage <ArrowRight size={14} className="ml-1" /></Link></Button>
            </div>
            <div className="mt-3 divide-y divide-border">
              {loading ? (
                <div className="py-8 text-sm text-muted-foreground text-center">Loading…</div>
              ) : datasets.length === 0 ? (
                <div className="py-8 text-sm text-muted-foreground text-center">No datasets yet. <Link to="/upload" className="text-primary hover:underline">Upload one</Link>.</div>
              ) : datasets.slice(0, 5).map((d) => (
                <Link key={d.id} to={`/dataset/${d.id}`} className="flex items-center justify-between py-3 hover:bg-accent -mx-2 px-2 rounded-md">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{d.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">{d.rows} rows · {d.columns?.length ?? "?"} cols</div>
                  </div>
                  <div className="text-xs">
                    {d.trained
                      ? <span className="text-success">● trained</span>
                      : <span className="text-muted-foreground">○ not trained</span>}
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div className="aq-card p-6" data-testid="recent-predictions">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl font-semibold">Recent predictions</h2>
              <Button variant="ghost" size="sm" asChild><Link to="/reports">Reports <ArrowRight size={14} className="ml-1" /></Link></Button>
            </div>
            <div className="mt-3 divide-y divide-border">
              {predictions.length === 0 ? (
                <div className="py-8 text-sm text-muted-foreground text-center">No predictions yet.</div>
              ) : predictions.slice(0, 5).map((p) => (
                <motion.div key={p.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between py-3">
                  <div className="min-w-0">
                    <div className="font-mono text-lg font-semibold" style={{ color: p.color }}>{Math.round(p.aqi)}</div>
                    <div className="text-xs text-muted-foreground truncate">{p.location || "—"} · {p.dataset_name}</div>
                  </div>
                  <AQIBadge aqi={p.aqi} />
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </PageBody>
    </>
  );
}
