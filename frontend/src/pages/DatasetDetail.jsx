import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody, StatCard } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AQIBadge } from "@/components/AQIBadge";
import {
  Brain, Compass, FileText, Sparkle, MapPin, ChartLineUp, Broom, Cpu,
} from "@phosphor-icons/react";
import { toast } from "sonner";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, Radar,
} from "recharts";

export default function DatasetDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [ds, setDs]         = useState(null);
  const [eda, setEda]       = useState(null);
  const [clean, setClean]   = useState(null);
  const [fe, setFe]         = useState(null);
  const [insight, setInsight] = useState(null);
  const [loadingInsight, setLoadingInsight] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [dsRes, edaRes] = await Promise.all([
        api.get(`/datasets/${id}`),
        api.get(`/datasets/${id}/eda`),
      ]);
      setDs(dsRes.data); setEda(edaRes.data);
    } catch (err) { toast.error(unwrapError(err)); nav("/upload"); }
    finally { setLoading(false); }
  }, [id, nav]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const runClean = async () => {
    try {
      const { data } = await api.post(`/datasets/${id}/clean`);
      setClean(data);
      toast.success("Data cleaned.");
    } catch (err) { toast.error(unwrapError(err)); }
  };
  const runFE = async () => {
    try {
      const { data } = await api.post(`/datasets/${id}/feature-engineering`);
      setFe(data);
      toast.success(`Engineered ${data.count} features.`);
    } catch (err) { toast.error(unwrapError(err)); }
  };
  const runInsight = async () => {
    setLoadingInsight(true);
    try {
      const { data } = await api.post(`/datasets/${id}/insights`);
      setInsight(data);
      toast.success("AI insight generated.");
    } catch (err) { toast.error(unwrapError(err)); }
    finally { setLoadingInsight(false); }
  };
  const startTrain = () => nav(`/train?dataset=${id}`);
  const goPredict  = () => nav(`/predict?dataset=${id}`);

  if (loading || !ds || !eda) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  );

  const histKeys = Object.keys(eda.histograms || {});

  return (
    <>
      <PageHeader
        title={ds.name}
        subtitle={`${ds.rows} rows · ${ds.columns.length} columns · schema auto-detected`}
        actions={
          <>
            <Button variant="outline" onClick={runInsight} disabled={loadingInsight} data-testid="dataset-insight-btn">
              <Sparkle size={16} className="mr-1.5" /> {loadingInsight ? "Generating…" : "AI Insight"}
            </Button>
            <Button onClick={startTrain} data-testid="dataset-train-btn"><Brain size={16} className="mr-1.5" /> Train models</Button>
            {ds.trained && <Button variant="outline" onClick={goPredict} data-testid="dataset-predict-btn"><Compass size={16} className="mr-1.5" /> Predict</Button>}
          </>
        }
      />
      <PageBody>
        {/* Detected schema */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Rows" value={ds.rows} testid="stat-rows" />
          <StatCard label="Columns" value={ds.columns.length} testid="stat-cols" />
          <StatCard label="Date column" value={ds.schema?.date || "—"} mono={false} testid="stat-date-col" />
          <StatCard label="Location column" value={ds.schema?.location || "—"} mono={false} testid="stat-loc-col" />
        </div>

        {insight && (
          <div className="mt-6 aq-card p-6 border-primary/40" data-testid="ai-insight-panel">
            <div className="flex items-center gap-2">
              <Sparkle size={16} className="text-primary" weight="fill" />
              <h3 className="font-display text-lg font-semibold">AI Insight</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed whitespace-pre-line">{insight.insight}</p>
          </div>
        )}

        <Tabs defaultValue="preview" className="mt-6">
          <TabsList className="w-full md:w-auto grid grid-cols-3 md:inline-grid md:grid-cols-6 gap-1" data-testid="dataset-tabs">
            <TabsTrigger value="preview"       data-testid="tab-preview">Preview</TabsTrigger>
            <TabsTrigger value="eda"           data-testid="tab-eda">EDA</TabsTrigger>
            <TabsTrigger value="correlation"   data-testid="tab-correlation">Correlation</TabsTrigger>
            <TabsTrigger value="trends"        data-testid="tab-trends">Trends</TabsTrigger>
            <TabsTrigger value="cleaning"      data-testid="tab-cleaning">Cleaning</TabsTrigger>
            <TabsTrigger value="features"      data-testid="tab-features">Features</TabsTrigger>
          </TabsList>

          {/* Preview */}
          <TabsContent value="preview" className="mt-4">
            <div className="aq-card overflow-hidden">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <h3 className="font-display text-base font-semibold">First {ds.preview?.length || 0} rows</h3>
                <a href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/dataset/${id}/csv`} className="text-xs text-primary hover:underline" data-testid="download-csv-link">Download raw CSV</a>
              </div>
              <div className="overflow-auto max-h-[70vh]">
                <table className="min-w-full text-xs">
                  <thead className="bg-muted/60 sticky top-0">
                    <tr>
                      {ds.columns.map((c) => (
                        <th key={c} className="text-left px-3 py-2 font-semibold whitespace-nowrap">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ds.preview?.map((row, i) => (
                      <tr key={i} className="border-t border-border">
                        {ds.columns.map((c) => (
                          <td key={c} className="px-3 py-1.5 whitespace-nowrap font-mono">{row[c] ?? "—"}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>

          {/* EDA */}
          <TabsContent value="eda" className="mt-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {histKeys.map((k) => (
                <div key={k} className="aq-card p-5" data-testid={`hist-${k}`}>
                  <h4 className="font-display text-sm font-semibold mb-3">Distribution — {k}</h4>
                  <div className="h-56">
                    <ResponsiveContainer>
                      <BarChart data={eda.histograms[k].bins.map((b, i) => ({ bin: b, count: eda.histograms[k].counts[i] }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="bin" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} hide />
                        <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                        <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                        <Bar dataKey="count" fill="#2563EB" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ))}
              <div className="aq-card p-5">
                <h4 className="font-display text-sm font-semibold mb-3">AQI category distribution</h4>
                <div className="h-56">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={eda.aqi_distribution} dataKey="count" nameKey="category" innerRadius={40} outerRadius={70}>
                        {eda.aqi_distribution.map((s, i) => <Cell key={i} fill={s.color} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="aq-card p-5">
                <h4 className="font-display text-sm font-semibold mb-3">Pollutant averages</h4>
                <div className="h-56">
                  <ResponsiveContainer>
                    <RadarChart data={eda.pollutant_comparison}>
                      <PolarGrid stroke="hsl(var(--border))" />
                      <PolarAngleAxis dataKey="pollutant" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <Radar dataKey="mean" stroke="#06B6D4" fill="#06B6D4" fillOpacity={0.35} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Correlation */}
          <TabsContent value="correlation" className="mt-4">
            <div className="aq-card p-5">
              <h4 className="font-display text-sm font-semibold mb-3">Correlation heatmap</h4>
              {eda.correlation.labels.length === 0 ? (
                <p className="text-sm text-muted-foreground">Not enough numeric columns.</p>
              ) : (
                <div className="overflow-auto">
                  <table className="text-xs">
                    <thead>
                      <tr>
                        <th></th>
                        {eda.correlation.labels.map((l) => <th key={l} className="px-1 py-1 text-left font-medium whitespace-nowrap">{l}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {eda.correlation.matrix.map((row, i) => (
                        <tr key={i}>
                          <td className="pr-2 font-medium whitespace-nowrap">{eda.correlation.labels[i]}</td>
                          {row.map((v, j) => {
                            const abs = Math.min(1, Math.abs(v));
                            const bg = v >= 0
                              ? `rgba(37, 99, 235, ${abs})`
                              : `rgba(239, 68, 68, ${abs})`;
                            return (
                              <td key={j} className="p-1">
                                <div className="w-12 h-8 flex items-center justify-center rounded font-mono text-[11px]" style={{ background: bg, color: abs > 0.5 ? "#fff" : "hsl(var(--foreground))" }}>
                                  {v.toFixed(2)}
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Trends */}
          <TabsContent value="trends" className="mt-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="aq-card p-5">
                <h4 className="font-display text-sm font-semibold mb-3 flex items-center gap-2"><ChartLineUp size={16} /> Monthly AQI trend</h4>
                <div className="h-56">
                  {eda.monthly_trend.length ? (
                    <ResponsiveContainer>
                      <LineChart data={eda.monthly_trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="month" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                        <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                        <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                        <Line type="monotone" dataKey="AQI" stroke="#2563EB" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : <p className="text-sm text-muted-foreground">No date column detected.</p>}
                </div>
              </div>
              <div className="aq-card p-5">
                <h4 className="font-display text-sm font-semibold mb-3">Yearly AQI trend</h4>
                <div className="h-56">
                  {eda.yearly_trend.length ? (
                    <ResponsiveContainer>
                      <BarChart data={eda.yearly_trend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                        <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                        <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                        <Bar dataKey="AQI" fill="#06B6D4" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <p className="text-sm text-muted-foreground">No date column detected.</p>}
                </div>
              </div>
            </div>
            {eda.location_avg.length > 0 && (
              <div className="aq-card p-5">
                <h4 className="font-display text-sm font-semibold mb-3 flex items-center gap-2"><MapPin size={16} /> Location averages</h4>
                <div className="h-64">
                  <ResponsiveContainer>
                    <BarChart data={eda.location_avg} layout="vertical" margin={{ left: 40 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis dataKey="location" type="category" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                      <Bar dataKey="avg_aqi" fill="#F59E0B" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Cleaning */}
          <TabsContent value="cleaning" className="mt-4">
            <div className="aq-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-display text-lg font-semibold flex items-center gap-2"><Broom size={16} /> Auto data cleaning</h4>
                  <p className="text-sm text-muted-foreground mt-1">Removes duplicates, fills nulls, and detects IQR outliers.</p>
                </div>
                <Button onClick={runClean} data-testid="run-clean-btn">Run cleaning</Button>
              </div>
              {clean && (
                <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="Rows before" value={clean.rows_before} testid="clean-rows-before" />
                  <StatCard label="Rows after"  value={clean.rows_after} testid="clean-rows-after" />
                  <StatCard label="Duplicates removed" value={clean.duplicates_removed} testid="clean-dupes" />
                  <StatCard label="Outliers detected"  value={clean.outliers_detected} testid="clean-outliers" />
                </div>
              )}
            </div>
          </TabsContent>

          {/* Features */}
          <TabsContent value="features" className="mt-4">
            <div className="aq-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-display text-lg font-semibold flex items-center gap-2"><Cpu size={16} /> Feature engineering</h4>
                  <p className="text-sm text-muted-foreground mt-1">Date parts, lag & rolling features, seasonal indicators.</p>
                </div>
                <Button onClick={runFE} data-testid="run-fe-btn">Generate</Button>
              </div>
              {fe && (
                <div className="mt-4">
                  <p className="text-sm text-muted-foreground mb-2">{fe.count} features created:</p>
                  <div className="flex flex-wrap gap-2">
                    {fe.created_features.map((f) => (
                      <span key={f} className="rounded-md border border-border px-2 py-1 text-xs font-mono">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </PageBody>
    </>
  );
}
