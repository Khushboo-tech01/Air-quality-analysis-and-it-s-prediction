import { useEffect, useMemo, useState } from "react";
import api, { API_BASE, unwrapError } from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { POLLUTANT_META, POLLUTANT_ORDER } from "@/lib/aqi";
import { ChartLineUp, Crosshair, Database, FileText, MapPin, Pulse, ThermometerSimple, Wind } from "@phosphor-icons/react";
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
  const aiForecast = result?.ai_forecast || {};
  const live = result?.live_data || {};
  const modelMetrics = result?.model_performance || {};
  const forecast = result?.forecast || aiForecast.days || [];
  const tomorrow = forecast[0] || {};

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
      toast.success(`Tomorrow forecast: AQI ${Math.round(data.predicted_aqi)}`);
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
        title="AI Air Quality Forecast"
        subtitle="Choose a location to fetch live environmental measurements and forecast future AQI with the production ML model."
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
                    <MapPin size={16} className="mr-1.5" /> {loading ? "Forecasting..." : "Generate Forecast"}
                  </Button>
                </form>
              ) : (
                <form onSubmit={submitCoordinates} className="grid flex-1 grid-cols-1 gap-3 md:grid-cols-[1fr_auto]">
                  <div>
                    <Label>Latitude, Longitude</Label>
                    <Input className="mt-1.5" value={coordinateText} onChange={(e) => setCoordinateText(e.target.value)} placeholder="28.61390, 77.20900" />
                  </div>
                  <Button type="submit" size="lg" disabled={loading} className="self-end">
                    <Crosshair size={16} className="mr-1.5" /> {loading ? "Forecasting..." : "Generate Forecast"}
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
                    <h3 className="font-display text-xl font-semibold">Current Environmental Conditions</h3>
                    <p className="text-sm text-muted-foreground">Live measurements only. AI forecasting starts with tomorrow.</p>
                  </div>
                  <Database size={22} className="text-muted-foreground" />
                </div>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-3">
                  <InfoCard label="Location" value={result.location} icon={MapPin} />
                  <InfoCard label="Temperature" value={features.temp != null ? `${features.temp} C` : "-"} icon={ThermometerSimple} />
                  <InfoCard label="Humidity" value={features.humidity != null ? `${features.humidity}%` : "-"} />
                  <InfoCard label="Pressure" value={features.pressure != null ? `${features.pressure} hPa` : "-"} />
                  <InfoCard label="Wind Speed" value={features.wind != null ? `${features.wind} m/s` : "-"} icon={Wind} />
                  <InfoCard label="Visibility" value={features.visibility != null ? `${features.visibility} m` : "-"} />
                  <InfoCard label="Weather" value={live.weather_condition} />
                  <InfoCard label="Coordinates" value={`${live.location?.latitude?.toFixed(4)}, ${live.location?.longitude?.toFixed(4)}`} />
                  <InfoCard label="Source" value={live.source} />
                  <InfoCard label="Last Updated" value={formatDate(live.timestamp, true)} />
                </div>
                <div className="mt-4">
                  <PollutantCards features={features} />
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 aq-card p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-display text-xl font-semibold">AI AQI Forecast</h3>
                      <p className="text-sm text-muted-foreground">Future AQI predicted from forecast weather and estimated pollutant behavior.</p>
                    </div>
                    <ChartLineUp size={22} className="text-muted-foreground" />
                  </div>
                  <div className="mt-6 space-y-4">
                    <div className="rounded-md border border-border p-4" style={{ borderLeft: `4px solid ${tomorrow.color || "#2563EB"}` }}>
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Tomorrow</p>
                          <p className="mt-1 text-3xl font-semibold">{tomorrow.predicted_aqi != null ? Math.round(tomorrow.predicted_aqi) : "-"}</p>
                          <p className="text-sm text-muted-foreground">{tomorrow.category || "-"} - {tomorrow.confidence != null ? `${tomorrow.confidence}% confidence` : "confidence unavailable"}</p>
                        </div>
                        <div className="max-w-xl text-sm leading-relaxed">
                          <p className="font-medium text-foreground">Health Advice</p>
                          <p className="text-muted-foreground">{tomorrow.health_advice || "-"}</p>
                          <p className="mt-3 font-medium text-foreground">Prediction Explanation</p>
                          <p className="text-muted-foreground">{tomorrow.explanation || "-"}</p>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {forecast.slice(1).map((day) => (
                        <div key={day.day} className="rounded-md border border-border p-4" style={{ borderLeft: `4px solid ${day.color}` }}>
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold">{day.label}</p>
                              <p className="text-xs text-muted-foreground">{day.date}</p>
                            </div>
                            <p className="font-mono text-xl font-semibold">{Math.round(day.predicted_aqi)}</p>
                          </div>
                          <div className="mt-3 space-y-1 text-sm">
                            <p><span className="text-muted-foreground">Category:</span> {day.category}</p>
                            <p><span className="text-muted-foreground">Risk:</span> {day.risk}</p>
                            <p><span className="text-muted-foreground">Weather:</span> {day.weather_summary}</p>
                            <p><span className="text-muted-foreground">Confidence:</span> {day.confidence}%</p>
                          </div>
                          <p className="mt-3 text-sm text-muted-foreground">{day.health_advice}</p>
                        </div>
                      ))}
                    </div>
                    <a href={`${API_BASE}/reports/prediction/${result.id}`} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium hover:bg-accent">
                      <FileText size={14} /> Export PDF Report
                    </a>
                  </div>
                </div>

                <div className="aq-card p-6">
                  <h3 className="font-display text-lg font-semibold">Model Info</h3>
                  <div className="mt-4 space-y-3 text-sm">
                    {[
                      ["Model Name", aiForecast.model_name],
                      ["Algorithm", modelMetrics.algorithm],
                      ["Training Accuracy", modelMetrics.training_accuracy != null ? `${modelMetrics.training_accuracy}%` : "-"],
                      ["RMSE", modelMetrics.rmse],
                      ["MAE", modelMetrics.mae],
                      ["R2 Score", modelMetrics.r2_score],
                      ["Model Version", aiForecast.model_version || modelMetrics.model_version],
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
                      <p className="text-sm text-muted-foreground">Future model outputs with confidence decreasing by forecast horizon.</p>
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
              <p className="mt-3 font-medium text-foreground">Select a location to generate a future AQI forecast.</p>
              <p className="text-sm">No CSV upload, dataset selection, or manual pollutant entry is required.</p>
            </div>
          )}
        </div>
      </PageBody>
    </>
  );
}
