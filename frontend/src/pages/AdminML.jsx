import { useEffect, useMemo, useState } from "react";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody, StatCard } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { Activity, Brain, Database, GitBranch, Play, RefreshCw, TrendingDown } from "lucide-react";
import { toast } from "sonner";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function fmt(value) {
  if (value == null || value === "") return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function number(value) {
  return value == null ? "-" : value;
}

function Panel({ title, children, action }) {
  return (
    <section className="rounded-md border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export default function AdminML() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [stats, setStats] = useState({});
  const [metrics, setMetrics] = useState({});
  const [status, setStatus] = useState({});
  const [history, setHistory] = useState([]);
  const [versions, setVersions] = useState([]);
  const [importance, setImportance] = useState([]);
  const [report, setReport] = useState({});

  const refresh = async () => {
    setLoading(true);
    try {
      const [statsRes, metricsRes, statusRes, historyRes, versionsRes, importanceRes, reportRes] = await Promise.all([
        api.get("/admin/dataset-statistics"),
        api.get("/admin/model-metrics"),
        api.get("/admin/training-status"),
        api.get("/admin/training-history"),
        api.get("/admin/model-versions"),
        api.get("/admin/feature-importance"),
        api.get("/admin/training-report"),
      ]);
      setStats(statsRes.data || {});
      setMetrics(metricsRes.data || {});
      setStatus(statusRes.data || {});
      setHistory(historyRes.data || []);
      setVersions(versionsRes.data || []);
      setImportance(importanceRes.data || []);
      setReport(reportRes.data || {});
    } catch (err) {
      toast.error(unwrapError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const runAction = async (name, request) => {
    setBusy(name);
    try {
      await request();
      toast.success(name === "collect" ? "Historical data collection completed." : "Model training completed.");
      await refresh();
    } catch (err) {
      toast.error(unwrapError(err));
    } finally {
      setBusy(null);
    }
  };

  const cityRows = useMemo(() => (stats.cities || []).slice(0, 10), [stats]);
  const importanceRows = useMemo(
    () => importance.slice(0, 12).map((item) => ({ ...item, pct: Math.round(Number(item.importance || 0) * 1000) / 10 })),
    [importance]
  );

  if (user?.role !== "admin") {
    return (
      <>
        <PageHeader title="ML Operations" subtitle="Admin access is required." />
        <PageBody>
          <div className="rounded-md border border-border bg-card p-8 text-sm text-muted-foreground">This workspace is available to administrators only.</div>
        </PageBody>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="ML Operations"
        subtitle="Automated data collection, training, model versioning, and production quality controls."
        actions={
          <Button variant="outline" onClick={refresh} disabled={loading || busy}>
            <RefreshCw size={16} className="mr-1.5" /> Refresh
          </Button>
        }
      />
      <PageBody>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Training Rows" value={number(stats.training_rows)} icon={Database} />
          <StatCard label="Historical Rows" value={number(stats.historical_rows)} icon={Activity} />
          <StatCard label="Production RMSE" value={metrics.rmse ?? "-"} icon={TrendingDown} />
          <StatCard label="Model Version" value={metrics.model_version || "-"} icon={GitBranch} />
        </div>

        <div className="mt-6 grid grid-cols-1 xl:grid-cols-3 gap-5">
          <Panel title="Pipeline Controls">
            <div className="space-y-3">
              <Button className="w-full justify-start" disabled={!!busy} onClick={() => runAction("collect", () => api.post("/admin/collect-data", { days: 90 }))}>
                <Database size={16} className="mr-2" /> {busy === "collect" ? "Collecting..." : "Collect Historical API Data"}
              </Button>
              <Button className="w-full justify-start" variant="outline" disabled={!!busy} onClick={() => runAction("train", () => api.post("/admin/train-model"))}>
                <Play size={16} className="mr-2" /> {busy === "train" ? "Training..." : "Train and Promote Best Model"}
              </Button>
              <div className="rounded-md border border-border p-3 text-sm">
                <p className="text-muted-foreground">Latest status</p>
                <p className="font-medium">{status.latest_log?.type || "-"} / {status.latest_log?.status || "-"}</p>
                <p className="text-xs text-muted-foreground">{fmt(status.latest_log?.created_at)}</p>
              </div>
            </div>
          </Panel>

          <Panel title="Model Metrics">
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ["Algorithm", metrics.algorithm],
                ["RMSE", metrics.rmse],
                ["MAE", metrics.mae],
                ["R2", metrics.r2],
                ["MAPE", metrics.mape],
                ["Dataset", metrics.dataset_size],
                ["Promoted", metrics.promoted == null ? "-" : metrics.promoted ? "Yes" : "No"],
                ["Training Date", fmt(metrics.training_date)],
              ].map(([label, value]) => (
                <div key={label} className="rounded-md border border-border p-3">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="mt-1 break-words font-medium">{value ?? "-"}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Dataset Coverage">
            <div className="h-72">
              <ResponsiveContainer>
                <BarChart data={cityRows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="city" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6 }} />
                  <Bar dataKey="count" fill="#0f766e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>

        <div className="mt-6 grid grid-cols-1 xl:grid-cols-2 gap-5">
          <Panel title="Feature Importance" action={<Brain size={18} className="text-muted-foreground" />}>
            <div className="h-80">
              <ResponsiveContainer>
                <BarChart data={importanceRows} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis type="category" dataKey="feature" width={96} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip formatter={(value) => `${value}%`} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6 }} />
                  <Bar dataKey="pct" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <Panel title="Model Versions">
            <div className="max-h-80 overflow-auto divide-y divide-border">
              {versions.length ? versions.map((item) => (
                <div key={item.id || item.model_version} className="py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{item.model_version}</p>
                    <span className="text-xs text-muted-foreground">{item.promoted ? "Promoted" : "Archived"}</span>
                  </div>
                  <p className="text-muted-foreground">{item.algorithm} | RMSE {item.rmse} | {fmt(item.training_date)}</p>
                </div>
              )) : <p className="py-8 text-center text-sm text-muted-foreground">No model versions yet.</p>}
            </div>
          </Panel>
        </div>

        <Panel title="Training Report">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 text-sm">
            <div className="rounded-md border border-border p-4">
              <p className="text-xs uppercase text-muted-foreground">Chosen Model</p>
              <p className="mt-1 font-semibold">{report.chosen_model || report.algorithm || "-"}</p>
              <p className="mt-2 text-muted-foreground">{report.selection_reason || "No report generated yet."}</p>
            </div>
            <div className="rounded-md border border-border p-4">
              <p className="text-xs uppercase text-muted-foreground">Target Distribution</p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {Object.entries(report.target_distribution?.bins || {}).map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-2"><span>{label}</span><span className="font-mono">{value}</span></div>
                ))}
              </div>
            </div>
            <div className="rounded-md border border-border p-4">
              <p className="text-xs uppercase text-muted-foreground">Feature List</p>
              <p className="mt-2 text-muted-foreground">{(report.feature_list || []).join(", ") || "-"}</p>
            </div>
          </div>
        </Panel>

        <Panel title="Training Logs">
          <div className="overflow-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                <tr><th className="py-2">Time</th><th>Type</th><th>Status</th><th>Details</th><th>Duration</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((item) => (
                  <tr key={item.id}>
                    <td className="py-2">{fmt(item.created_at)}</td>
                    <td>{item.type}</td>
                    <td>{item.status}</td>
                    <td>{item.model_version || item.locations?.join(", ") || item.error || "-"}</td>
                    <td>{item.duration_seconds != null ? `${item.duration_seconds}s` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!history.length && <p className="py-8 text-center text-sm text-muted-foreground">No training logs yet.</p>}
          </div>
        </Panel>
      </PageBody>
    </>
  );
}
