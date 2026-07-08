import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { AQIGauge } from "@/components/AQIGauge";
import { POLLUTANT_META, POLLUTANT_ORDER } from "@/lib/aqi";
import { Compass, FileText, CalendarBlank, MapPin, ChartLineUp } from "@phosphor-icons/react";
import { toast } from "sonner";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function Predict() {
  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState("");
  const [features, setFeatures] = useState({});
  const [featureKeys, setFeatureKeys] = useState(POLLUTANT_ORDER);
  const [location, setLocation] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [params] = useSearchParams();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/datasets");
        const trained = data.filter((d) => d.trained);
        setDatasets(trained);
        const pre = params.get("dataset");
        if (pre && trained.some((d) => d.id === pre)) setDatasetId(pre);
        else if (trained.length) setDatasetId(trained[0].id);
      } catch { /* silent */ }
    })();
  }, [params]);

  useEffect(() => {
    if (!datasetId) return;
    (async () => {
      try {
        const { data } = await api.get(`/datasets/${datasetId}/models`);
        setFeatureKeys(data.feature_keys?.length ? data.feature_keys : POLLUTANT_ORDER);
      } catch { /* ignore */ }
      setForecast(null);
      setResult(null);
    })();
  }, [datasetId]);

  const fields = useMemo(() => featureKeys.filter((k) => POLLUTANT_META[k]), [featureKeys]);

  const set = (k) => (e) => setFeatures((f) => ({ ...f, [k]: e.target.value === "" ? undefined : Number(e.target.value) }));

  const submit = async (e) => {
    e.preventDefault();
    if (!datasetId) return toast.error("Select a trained dataset first.");
    setLoading(true);
    setResult(null);
    try {
      const clean = {};
      for (const k of fields) if (features[k] !== undefined && !Number.isNaN(features[k])) clean[k] = features[k];
      const { data } = await api.post("/predict", {
        dataset_id: datasetId, features: clean,
        location: location || null, date: date || null,
      });
      setResult(data);
      toast.success(`Predicted AQI ${Math.round(data.aqi)}`);
    } catch (err) { toast.error(unwrapError(err)); }
    finally { setLoading(false); }
  };

  const runForecast = async () => {
    if (!datasetId) return;
    try {
      const { data } = await api.post(`/forecast/${datasetId}`);
      setForecast(data);
    } catch (err) { toast.error(unwrapError(err)); }
  };

  return (
    <>
      <PageHeader
        title="Predict AQI"
        subtitle="Enter pollutant and weather values to get an instant AQI classification and health advice."
      />
      <PageBody>
        {datasets.length === 0 ? (
          <div className="aq-card p-10 text-center">
            <Compass size={28} className="mx-auto text-muted-foreground" />
            <p className="mt-3 font-medium">No trained models yet</p>
            <p className="text-sm text-muted-foreground">Upload a dataset and train models before predicting.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <form onSubmit={submit} className="lg:col-span-2 aq-card p-6 space-y-4" data-testid="predict-form">
              <div>
                <Label>Trained model</Label>
                <Select value={datasetId} onValueChange={setDatasetId}>
                  <SelectTrigger className="mt-1.5" data-testid="predict-dataset-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {datasets.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="loc">Location</Label>
                  <div className="relative mt-1.5">
                    <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                    <Input id="loc" value={location} onChange={(e) => setLocation(e.target.value)} className="pl-8" placeholder="e.g. Delhi" data-testid="predict-location-input" />
                  </div>
                </div>
                <div>
                  <Label htmlFor="date">Date</Label>
                  <div className="relative mt-1.5">
                    <CalendarBlank size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                    <Input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} className="pl-8" data-testid="predict-date-input" />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {fields.map((k) => (
                  <div key={k}>
                    <Label htmlFor={k}>{POLLUTANT_META[k].label} <span className="text-muted-foreground font-normal">({POLLUTANT_META[k].unit})</span></Label>
                    <Input
                      id={k} type="number" step={POLLUTANT_META[k].step}
                      value={features[k] ?? ""} onChange={set(k)}
                      placeholder={POLLUTANT_META[k].placeholder}
                      data-testid={`feat-${k}`}
                      className="mt-1.5 font-mono"
                    />
                  </div>
                ))}
              </div>

              <div className="flex justify-end">
                <Button type="submit" size="lg" disabled={loading} data-testid="predict-submit-btn">
                  <Compass size={16} className="mr-1.5" /> {loading ? "Predicting…" : "Predict AQI"}
                </Button>
              </div>
            </form>

            <div className="aq-card p-6 flex flex-col" data-testid="predict-result-panel">
              {!result ? (
                <div className="text-center flex-1 flex flex-col items-center justify-center text-muted-foreground">
                  <Compass size={28} />
                  <p className="mt-3 text-sm">Fill the form and click predict.</p>
                </div>
              ) : (
                <>
                  <AQIGauge aqi={result.aqi} />
                  <div className="mt-4 space-y-2 text-sm">
                    <div className="text-muted-foreground text-xs uppercase tracking-wider">Health advice</div>
                    <p className="text-sm leading-relaxed">{result.advice}</p>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div><div className="text-xs text-muted-foreground">Model</div><div className="font-medium">{result.model}</div></div>
                    <div><div className="text-xs text-muted-foreground">Category</div><div className="font-medium">{result.category}</div></div>
                    <div><div className="text-xs text-muted-foreground">Location</div><div className="font-medium">{result.location || "—"}</div></div>
                    <div><div className="text-xs text-muted-foreground">Date</div><div className="font-medium">{result.date || "—"}</div></div>
                  </div>
                  <a
                    href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/prediction/${result.id}`}
                    target="_blank" rel="noreferrer"
                    className="mt-6 inline-flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-accent"
                    data-testid="download-prediction-pdf"
                  >
                    <FileText size={14} /> Download PDF report
                  </a>
                </>
              )}
            </div>
          </div>
        )}

        {/* 7-day forecast */}
        {datasetId && (
          <div className="mt-6 aq-card p-6" data-testid="forecast-panel">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-semibold flex items-center gap-2"><ChartLineUp size={16} /> 7-day AQI forecast</h3>
                <p className="text-sm text-muted-foreground">Naive projection using last known pollutant levels & the trained model.</p>
              </div>
              <Button variant="outline" onClick={runForecast} data-testid="run-forecast-btn">Generate forecast</Button>
            </div>
            {forecast && (
              <div className="h-64 mt-4">
                <ResponsiveContainer>
                  <LineChart data={forecast}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="day" tickFormatter={(d) => `D${d}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                    <Line type="monotone" dataKey="aqi" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </PageBody>
    </>
  );
}
