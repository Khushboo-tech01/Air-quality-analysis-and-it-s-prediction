import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader, PageBody, StatCard } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { AQIBadge } from "@/components/AQIBadge";
import { ChartLineUp, Compass, Gauge, MapPin, Pulse, ShieldCheck } from "@phosphor-icons/react";
import { motion } from "framer-motion";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function Dashboard() {
  const { user } = useAuth();
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modelInfo, setModelInfo] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [history, model] = await Promise.all([api.get("/history"), api.get("/model/production")]);
        setPredictions(history.data);
        setModelInfo(model.data);
      } catch {
        // Auth interceptor handles expired sessions.
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const today = new Date().toISOString().slice(0, 10);
  const todaysForecasts = predictions.filter((p) => (p.date || p.created_at || "").slice(0, 10) === today).length;
  const lastForecast = predictions[0];
  const chartData = [...predictions].reverse().map((p, index) => ({ idx: index + 1, aqi: p.aqi }));
  const averageAqi = predictions.length
    ? Math.round(predictions.reduce((sum, item) => sum + Number(item.aqi || 0), 0) / predictions.length)
    : 0;

  return (
    <>
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] || "there"}`}
        subtitle="Your live environmental monitoring and AI AQI forecasting workspace."
        actions={
          <Button asChild data-testid="dashboard-predict-btn">
            <Link to="/predict"><MapPin size={16} className="mr-1.5" /> Monitor Location</Link>
          </Button>
        }
      />
      <PageBody>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Forecasts" value={predictions.length} icon={Compass} testid="stat-predictions" />
          <StatCard label="Today's Forecasts" value={todaysForecasts} icon={ChartLineUp} testid="stat-today-predictions" />
          <StatCard label="Avg Tomorrow AQI" value={averageAqi || "-"} icon={Gauge} testid="stat-average-aqi" />
          <StatCard label="Production Model" value={modelInfo?.loaded ? "Loaded" : "Fallback"} icon={ShieldCheck} testid="stat-model-status" />
        </div>

        <div className="mt-4 aq-card p-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between" data-testid="stat-last-prediction">
          <div>
            <p className="text-xs uppercase text-muted-foreground">Last AI Forecast</p>
            <p className="font-display text-lg font-semibold">
              {lastForecast ? `${Math.round(lastForecast.aqi)} AQI - ${lastForecast.category}` : "No forecasts yet"}
            </p>
            {lastForecast && <p className="text-sm text-muted-foreground">{lastForecast.location}</p>}
          </div>
          {lastForecast && <AQIBadge aqi={lastForecast.aqi} />}
        </div>

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 aq-card p-6" data-testid="chart-recent-predictions">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-display text-xl font-semibold">Recent AQI Forecasts</h2>
                <p className="text-sm text-muted-foreground">Tomorrow AQI trend across your latest monitored locations.</p>
              </div>
              <Button variant="ghost" size="sm" asChild><Link to="/predict">Monitor</Link></Button>
            </div>
            <div className="h-64 mt-4">
              {chartData.length > 0 ? (
                <ResponsiveContainer>
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="dashArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563EB" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
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
                  No monitored locations yet.
                </div>
              )}
            </div>
          </div>

          <div className="aq-card p-6">
            <h2 className="font-display text-xl font-semibold">Production Model</h2>
            <div className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-4 border-b border-border pb-2">
                <span className="text-muted-foreground">Model</span>
                <span className="font-medium text-right">{modelInfo?.model_name || "Fallback AQI Estimator"}</span>
              </div>
              <div className="flex justify-between gap-4 border-b border-border pb-2">
                <span className="text-muted-foreground">Version</span>
                <span className="font-medium text-right">{modelInfo?.model_version || "-"}</span>
              </div>
              <div className="flex justify-between gap-4 border-b border-border pb-2">
                <span className="text-muted-foreground">R2 Score</span>
                <span className="font-medium text-right">{modelInfo?.metrics?.r2 ?? "-"}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-muted-foreground">RMSE</span>
                <span className="font-medium text-right">{modelInfo?.metrics?.rmse ?? "-"}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 aq-card p-6" data-testid="recent-predictions">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold">Recent Monitoring Runs</h2>
            <Button variant="ghost" size="sm" asChild><Link to="/reports">Reports</Link></Button>
          </div>
          <div className="mt-3 divide-y divide-border">
            {loading ? (
              <div className="py-8 text-sm text-muted-foreground text-center">Loading...</div>
            ) : predictions.length === 0 ? (
              <div className="py-8 text-sm text-muted-foreground text-center">Choose a location to create your first AI AQI forecast.</div>
            ) : predictions.slice(0, 8).map((prediction) => (
              <motion.div key={prediction.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between py-3">
                <div className="min-w-0">
                  <div className="font-mono text-lg font-semibold" style={{ color: prediction.color }}>{Math.round(prediction.aqi)}</div>
                  <div className="text-xs text-muted-foreground truncate">{prediction.location || "-"} - {prediction.model || "AI model"}</div>
                </div>
                <div className="flex items-center gap-3">
                  {prediction.confidence != null && <span className="hidden sm:inline-flex items-center gap-1 text-xs text-muted-foreground"><Pulse size={13} /> {prediction.confidence}%</span>}
                  <AQIBadge aqi={prediction.aqi} />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </PageBody>
    </>
  );
}
