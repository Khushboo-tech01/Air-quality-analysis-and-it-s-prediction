import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody, StatCard } from "@/components/Page";
import { Button } from "@/components/ui/button";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
import { Brain, Trophy, Clock, ArrowRight, ChartLineUp } from "@phosphor-icons/react";
import { toast } from "sonner";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

export default function Train() {
  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState("");
  const [results, setResults] = useState(null);
  const [best, setBest] = useState(null);
  const [training, setTraining] = useState(false);
  const [loading, setLoading] = useState(true);
  const [params] = useSearchParams();
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/datasets");
        setDatasets(data);
        const pre = params.get("dataset");
        if (pre && data.some((d) => d.id === pre)) setDatasetId(pre);
        else if (data.length) setDatasetId(data[0].id);
      } catch { /* silent */ }
      finally { setLoading(false); }
    })();
  }, [params]);

  useEffect(() => {
    if (!datasetId) return;
    (async () => {
      try {
        const { data } = await api.get(`/datasets/${datasetId}/models`);
        if (data.trained) {
          setResults(data.results);
          setBest(data.best_model);
        } else {
          setResults(null); setBest(null);
        }
      } catch { /* ignore */ }
    })();
  }, [datasetId]);

  const train = async () => {
    if (!datasetId) return;
    setTraining(true);
    try {
      const { data } = await api.post(`/datasets/${datasetId}/train`);
      setResults(data.results);
      setBest(data.best_model);
      toast.success(`Trained ${data.results.length} models. Best: ${data.best_model}`);
    } catch (err) { toast.error(unwrapError(err)); }
    finally { setTraining(false); }
  };

  return (
    <>
      <PageHeader
        title="Train & compare models"
        subtitle="Linear · Decision Tree · Random Forest · Gradient Boosting · XGBoost — trained on your dataset."
      />
      <PageBody>
        <div className="aq-card p-5 flex flex-col md:flex-row md:items-end gap-4">
          <div className="flex-1">
            <label className="text-xs uppercase text-muted-foreground tracking-wider">Dataset</label>
            <Select value={datasetId} onValueChange={setDatasetId}>
              <SelectTrigger className="mt-1.5" data-testid="train-dataset-select"><SelectValue placeholder="Choose a dataset" /></SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.id} value={d.id}>{d.name} — {d.rows} rows</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button size="lg" onClick={train} disabled={!datasetId || training} data-testid="train-run-btn">
            <Brain size={16} className="mr-1.5" /> {training ? "Training…" : "Train all models"}
          </Button>
        </div>

        {loading && <div className="mt-6 text-sm text-muted-foreground">Loading…</div>}

        {training && (
          <div className="mt-6 aq-card p-8 flex flex-col items-center gap-3">
            <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            <p className="text-sm">Training 5 models — this may take up to 30 seconds…</p>
          </div>
        )}

        {results && !training && (
          <>
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Best model" value={best} mono={false} icon={Trophy} testid="best-model-stat" />
              <StatCard label="Best R²" value={Math.max(...results.map((r) => r.r2)).toFixed(3)} testid="best-r2" />
              <StatCard label="Lowest RMSE" value={Math.min(...results.map((r) => r.rmse)).toFixed(2)} testid="best-rmse" />
              <StatCard label="Fastest predict" value={`${Math.min(...results.map((r) => r.predict_ms)).toFixed(1)} ms`} icon={Clock} testid="fastest-predict" />
            </div>

            <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 aq-card p-5">
                <h4 className="font-display text-lg font-semibold flex items-center gap-2"><ChartLineUp size={16} /> Metric comparison</h4>
                <div className="h-64 mt-4">
                  <ResponsiveContainer>
                    <BarChart data={results}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="rmse" fill="#EF4444" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="mae"  fill="#F59E0B" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="aq-card p-5">
                <h4 className="font-display text-lg font-semibold">R² scores</h4>
                <div className="mt-4 space-y-3">
                  {results.map((r) => (
                    <div key={r.name}>
                      <div className="flex items-center justify-between text-sm">
                        <span className={r.name === best ? "font-semibold text-primary" : ""}>{r.name}</span>
                        <span className="font-mono">{r.r2.toFixed(4)}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted mt-1 overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: `${Math.max(0, Math.min(1, r.r2)) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 aq-card overflow-hidden">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <h4 className="font-display text-lg font-semibold">All metrics</h4>
                <a href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/model/${datasetId}`} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline" data-testid="download-model-pdf">Download PDF report</a>
              </div>
              <div className="overflow-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      {["Model","RMSE","MAE","R²","CV R²","Train (ms)","Predict (ms)"].map((h) => (
                        <th key={h} className="text-left px-4 py-3 font-semibold text-xs uppercase tracking-wider text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => (
                      <tr key={r.name} className={`border-t border-border ${r.name === best ? "bg-primary/5" : ""}`} data-testid={`model-row-${r.name.replace(/\s+/g, "-")}`}>
                        <td className="px-4 py-3 font-medium">
                          {r.name === best ? <Trophy size={14} className="inline mr-1 text-primary" weight="fill" /> : null}
                          {r.name}
                        </td>
                        <td className="px-4 py-3 font-mono">{r.rmse}</td>
                        <td className="px-4 py-3 font-mono">{r.mae}</td>
                        <td className="px-4 py-3 font-mono">{r.r2}</td>
                        <td className="px-4 py-3 font-mono">{r.cv_r2}</td>
                        <td className="px-4 py-3 font-mono text-muted-foreground">{r.train_ms}</td>
                        <td className="px-4 py-3 font-mono text-muted-foreground">{r.predict_ms}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button onClick={() => nav(`/predict?dataset=${datasetId}`)} data-testid="go-predict-btn">
                Predict with this model <ArrowRight size={14} className="ml-1.5" />
              </Button>
            </div>
          </>
        )}
      </PageBody>
    </>
  );
}
