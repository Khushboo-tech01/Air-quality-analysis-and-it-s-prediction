import { useEffect, useMemo, useState } from "react";
import api, { API_BASE, unwrapError } from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { AQIGauge } from "@/components/AQIGauge";
import { POLLUTANT_META, POLLUTANT_ORDER } from "@/lib/aqi";
import { ChartLineUp, Crosshair, Database, FileText, Gauge, MapPin, Pulse, ShieldCheck } from "@phosphor-icons/react";
import { toast } from "sonner";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar } from "recharts";

const REFRESH_MS = 7 * 60 * 1000;

function formatDate(value, seconds = false) {
  if (!value) return "-";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: seconds ? "medium" : "short" });
}

function InfoCard({ label, value, icon: Icon = Pulse }) {
  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <Icon size={16} className="text-muted-foreground" />
      </div>
      <p className="mt-2 truncate font-semibold">{value ?? "-"}</p>
    </div>
  );
}

function PollutantCards({ features }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {POLLUTANT_ORDER.map((key) => (
        <div key={key} className="rounded-md border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">{POLLUTANT_META[key].label}</p>
          <p className="mt-1 font-mono text-xl font-semibold">{features?.[key] ?? "-"}</p>
          <p className="text-xs text-muted-foreground">{POLLUTANT_META[key].unit}</p>
        </div>
      ))}
    </div>
  );
}

export default function Predict() {
  const [location, setLocation] = useState({ country: "", state: "", city: "" });
  const [coordinateText, setCoordinateText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastRequest, setLastRequest] = useState(null);
  const [mode, setMode] = useState("place");

  const features = useMemo(() => result?.live_data?.measurements || {}, [result]);
  const ai = result?.ai_prediction || {};
  const live = result?.live_data || {};
  const modelMetrics = result?.model_performance || {};
  const forecast = result?.forecast || [];

  const chartFeatures = useMemo(
    () => POLLUTANT_ORDER.filter((key) => features[key] != null).map((key) => ({ name: POLLUTANT_META[key].label, value: Number(features[key]) })),
    [features]
  );

  const runPrediction = async (payload) => {
    setLoading(true);
    try {
      const { data } = await api.post("/predict/location", payload);
      setResult(data);
      setLastRequest(payload);
      toast.success(`AI predicted AQI ${Math.round(data.predicted_aqi)}`);
    } catch (err) {
      toast.error(unwrapError(err));
    } finally {
      setLoading(false);
    }
  };

  const submitPlace = (event) => {
    event.preventDefault();
    if (!location.country.trim() || !location.city.trim()) return toast.error("Country and city are required.");
    runPrediction({ country: location.country.trim(), state: location.state.trim() || null, city: location.city.trim() });
  };

  const submitCoordinates = (event) => {
    event.preventDefault();
    const [lat, lon] = coordinateText.split(",").map((part) => Number(part.trim()));
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return toast.error("Enter coordinates as latitude, longitude.");
    runPrediction({ latitude: lat, longitude: lon });
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) return toast.error("GPS location is not available in this browser.");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setMode("coords");
        const payload = { latitude: position.coords.latitude, longitude: position.coords.longitude };
        setCoordinateText(`${payload.latitude.toFixed(5)}, ${payload.longitude.toFixed(5)}`);
        runPrediction(payload);
      },
      () => toast.error("Unable to read current GPS location."),
      { enableHighAccuracy: true, timeout: 12000 }
    );
  };

  useEffect(() => {
    if (!lastRequest) return undefined;
    const id = window.setInterval(() => runPrediction(lastRequest), REFRESH_MS);
    return () => window.clearInterval(id);
  }, [lastRequest]);

  return (
    <>
      <PageHeader
        title="Live AI Air Quality Monitor"
        subtitle="Choose a location once. Weather, pollution, prediction, forecast, and advice are generated automatically."
        actions={
          <Button variant="outline" onClick={() => lastRequest && runPrediction(lastRequest)} disabled={!lastRequest || loading}>
            <Pulse size={16} className="mr-1.5" /> Refresh
          </Button>
        }
      />
      <PageBody>
        <div className="space-y-6">
          <div className="aq-card p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
              <div className="flex rounded-md border border-border p-1">
                <button type="button" onClick={() => setMode("place")} className={`rounded px-3 py-2 text-sm font-medium ${mode === "place" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}>Place</button>
                <button type="button" onClick={() => setMode("coords")} className={`rounded px-3 py-2 text-sm font-medium ${mode === "coords" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}>Coordinates</button>
              </div>

              {mode === "place" ? (
                <form onSubmit={submitPlace} className="grid flex-1 grid-cols-1 gap-3 md:grid-cols-4">
                  <div>
                    <Label>Country</Label>
                    <Input className="mt-1.5" value={location.country} onChange={(e) => setLocation((v) => ({ ...v, country: e.target.value }))} placeholder="India" />
                  </div>
                  <div>
                    <Label>State</Label>
                    <Input className="mt-1.5" value={location.state} onChange={(e) => setLocation((v) => ({ ...v, state: e.target.value }))} placeholder="Delhi" />
                  </div>
                  <div>
                    <Label>City</Label>
                    <Input className="mt-1.5" value={location.city} onChange={(e) => setLocation((v) => ({ ...v, city: e.target.value }))} placeholder="New Delhi" />
                  </div>
                  <Button type="submit" size="lg" disabled={loading} className="self-end">
                    <MapPin size={16} className="mr-1.5" /> {loading ? "Analyzing..." : "Analyze Location"}
                  </Button>
                </form>
              ) : (
                <form onSubmit={submitCoordinates} className="grid flex-1 grid-cols-1 gap-3 md:grid-cols-[1fr_auto]">
                  <div>
                    <Label>Latitude, Longitude</Label>
                    <Input className="mt-1.5" value={coordinateText} onChange={(e) => setCoordinateText(e.target.value)} placeholder="28.61390, 77.20900" />
                  </div>
                  <Button type="submit" size="lg" disabled={loading} className="self-end">
                    <Crosshair size={16} className="mr-1.5" /> {loading ? "Analyzing..." : "Analyze Coordinates"}
                  </Button>
                </form>
              )}

              <Button variant="outline" size="lg" onClick={useCurrentLocation} disabled={loading}>
                <Crosshair size={16} className="mr-1.5" /> Current GPS
              </Button>
            </div>
          </div>

          <div className="rounded-md border border-border bg-card p-4 text-sm text-muted-foreground">
            Live measurements refresh every 7 minutes after the first successful lookup. OpenWeather responses are cached by the backend to reduce API usage.
          </div>

          {loading && !result ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">{Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-28" />)}</div>
          ) : result ? (
            <>
              <div className="aq-card p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-display text-xl font-semibold">Current AQI Inputs</h3>
                    <p className="text-sm text-muted-foreground">Official live measurements used as model inputs.</p>
                  </div>
                  <Database size={22} className="text-muted-foreground" />
                </div>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-3">
                  <InfoCard label="Location" value={result.location} icon={MapPin} />
                  <InfoCard label="Coordinates" value={`${live.location?.latitude?.toFixed(4)}, ${live.location?.longitude?.toFixed(4)}`} />
                  <InfoCard label="Last Updated" value={formatDate(live.timestamp, true)} />
                  <InfoCard label="Weather" value={live.weather_condition} />
                  <InfoCard label="Timezone" value={live.timezone != null ? `UTC ${live.timezone / 3600}` : "-"} />
                  <InfoCard label="Sunrise" value={formatDate(live.sunrise)} />
                  <InfoCard label="Sunset" value={formatDate(live.sunset)} />
                  <InfoCard label="Source" value={live.source} />
                </div>
                <div className="mt-4">
                  <PollutantCards features={features} />
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 aq-card p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-display text-xl font-semibold">AI Prediction Dashboard</h3>
                      <p className="text-sm text-muted-foreground">Prediction generated by the production ML model.</p>
                    </div>
                    <Gauge size={22} className="text-muted-foreground" />
                  </div>
                  <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <AQIGauge aqi={ai.predicted_aqi} />
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <InfoCard label="Predicted AQI" value={Math.round(ai.predicted_aqi)} icon={Gauge} />
                        <InfoCard label="Category" value={ai.category} icon={ShieldCheck} />
                        <InfoCard label="Confidence" value={ai.confidence != null ? `${ai.confidence}%` : "-"} icon={Pulse} />
                        <InfoCard label="Risk Level" value={ai.risk_level} />
                        <InfoCard label="Model Used" value={ai.model_name} />
                        <InfoCard label="Generated At" value={formatDate(ai.generated_at)} />
                      </div>
                      <div className="rounded-md border border-border p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Health Advice</p>
                        <p className="mt-2 text-sm leading-relaxed">{ai.health_advice}</p>
                      </div>
                      <div className="rounded-md border border-border p-4">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Prediction Explanation</p>
                        <p className="mt-2 text-sm leading-relaxed">{ai.explanation}</p>
                      </div>
                      <a href={`${API_BASE}/reports/prediction/${result.id}`} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-accent">
                        <FileText size={14} /> Export PDF Report
                      </a>
                    </div>
                  </div>
                </div>

                <div className="aq-card p-6">
                  <h3 className="font-display text-lg font-semibold">Model Info</h3>
                  <div className="mt-4 space-y-3 text-sm">
                    {[
                      ["Model Name", ai.model_name],
                      ["Algorithm", modelMetrics.algorithm],
                      ["Training Accuracy", modelMetrics.training_accuracy != null ? `${modelMetrics.training_accuracy}%` : "-"],
                      ["RMSE", modelMetrics.rmse],
                      ["MAE", modelMetrics.mae],
                      ["R2 Score", modelMetrics.r2_score],
                      ["Model Version", modelMetrics.model_version],
                      ["Training Date", formatDate(modelMetrics.training_date)],
                    ].map(([label, value]) => (
                      <div key={label} className="flex justify-between gap-4 border-b border-border pb-2 last:border-0">
                        <span className="text-muted-foreground">{label}</span>
                        <span className="text-right font-medium">{value ?? "-"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <div className="aq-card p-6">
                  <h3 className="font-display text-lg font-semibold">Pollution Trend Snapshot</h3>
                  <div className="h-72 mt-4">
                    <ResponsiveContainer>
                      <BarChart data={chartFeatures}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                        <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                        <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                        <Bar dataKey="value" fill="#2563EB" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="aq-card p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-display text-lg font-semibold flex items-center gap-2"><ChartLineUp size={16} /> 7-Day AQI Forecast</h3>
                      <p className="text-sm text-muted-foreground">Trend-adjusted future predictions, not repeated from today.</p>
                    </div>
                  </div>
                  <div className="h-72 mt-4">
                    <ResponsiveContainer>
                      <LineChart data={forecast}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="day" tickFormatter={(day) => `D${day}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                        <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                        <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                        <Line type="monotone" dataKey="aqi" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="aq-card p-12 text-center text-muted-foreground">
              <MapPin size={32} className="mx-auto" />
              <p className="mt-3 font-medium text-foreground">Select a location to start monitoring.</p>
              <p className="text-sm">No CSV upload, dataset selection, or manual pollutant entry is required.</p>
            </div>
          )}
        </div>
      </PageBody>
    </>
  );
}
