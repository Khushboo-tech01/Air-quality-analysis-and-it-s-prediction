import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api, { API_BASE, unwrapError } from "@/lib/api";
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

const OPENWEATHER_API_KEY = process.env.REACT_APP_OPENWEATHER_API_KEY;
const LIVE_CACHE_TTL_MS = 10 * 60 * 1000;
const OPENWEATHER_AQI = {
  1: "Good",
  2: "Fair",
  3: "Moderate",
  4: "Poor",
  5: "Very Poor",
};

function buildLocationQuery({ country, state, city }) {
  return [city, state, country].map((v) => v.trim()).filter(Boolean).join(",");
}

function getValidLiveFeatures(features) {
  return Object.fromEntries(
    Object.entries(features).filter(([, value]) => value !== undefined && value !== null && !Number.isNaN(Number(value)))
  );
}

async function fetchJson(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.message || "Unable to fetch live weather data.");
  }
  return data;
}

async function fetchLiveWeather(locationInput) {
  if (!OPENWEATHER_API_KEY) {
    throw new Error("OpenWeather API key is missing. Set REACT_APP_OPENWEATHER_API_KEY in frontend/.env.");
  }

  const query = buildLocationQuery(locationInput);
  const cacheKey = `aeropulse-live-weather:${query.toLowerCase()}`;
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      if (Date.now() - parsed.cachedAt < LIVE_CACHE_TTL_MS) return { ...parsed.data, cached: true };
    } catch {
      localStorage.removeItem(cacheKey);
    }
  }

  const geoUrl = `https://api.openweathermap.org/geo/1.0/direct?q=${encodeURIComponent(query)}&limit=1&appid=${OPENWEATHER_API_KEY}`;
  const geo = await fetchJson(geoUrl);
  const place = geo?.[0];
  if (!place) throw new Error("Location not found. Check country, state, and city.");

  const coords = { lat: place.lat, lon: place.lon };
  const airUrl = `https://api.openweathermap.org/data/2.5/air_pollution?lat=${coords.lat}&lon=${coords.lon}&appid=${OPENWEATHER_API_KEY}`;
  const weatherUrl = `https://api.openweathermap.org/data/2.5/weather?lat=${coords.lat}&lon=${coords.lon}&units=metric&appid=${OPENWEATHER_API_KEY}`;
  const [air, weather] = await Promise.all([fetchJson(airUrl), fetchJson(weatherUrl)]);
  const airEntry = air?.list?.[0];
  if (!airEntry?.components) throw new Error("Air pollution data is unavailable for this location.");

  const components = airEntry.components;
  const data = {
    features: {
      pm25: components.pm2_5,
      pm10: components.pm10,
      no2: components.no2,
      so2: components.so2,
      co: components.co != null ? components.co / 1000 : undefined,
      o3: components.o3,
      temp: weather?.main?.temp,
      humidity: weather?.main?.humidity,
      pressure: weather?.main?.pressure,
      wind: weather?.wind?.speed,
    },
    location: [place.name, place.state, place.country].filter(Boolean).join(", "),
    coordinates: coords,
    currentAqi: airEntry.main?.aqi,
    lastUpdated: new Date((airEntry.dt || weather?.dt || Date.now() / 1000) * 1000).toISOString(),
    source: "OpenWeather Air Pollution API and Weather API",
  };

  localStorage.setItem(cacheKey, JSON.stringify({ cachedAt: Date.now(), data }));
  return { ...data, cached: false };
}

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
  const [mode, setMode] = useState("manual");
  const [liveLocation, setLiveLocation] = useState({ country: "", state: "", city: "" });
  const [liveMeta, setLiveMeta] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState("");
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
  const setLiveField = (key) => (e) => {
    setLiveLocation((v) => ({ ...v, [key]: e.target.value }));
    setLiveMeta(null);
    setLiveError("");
  };

  const loadLiveData = async () => {
    if (!liveLocation.country.trim() || !liveLocation.city.trim()) {
      setLiveError("Country and city are required.");
      return;
    }
    setLiveLoading(true);
    setLiveError("");
    try {
      const data = await fetchLiveWeather(liveLocation);
      setFeatures((current) => ({ ...current, ...getValidLiveFeatures(data.features) }));
      setLocation(data.location);
      setLiveMeta(data);
      toast.success(data.cached ? "Loaded cached live data." : "Live weather data loaded.");
    } catch (err) {
      const message = err?.message || "Unable to load live data.";
      setLiveError(message);
      toast.error(message);
    } finally {
      setLiveLoading(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!datasetId) return toast.error("Select a trained dataset first.");
    if (!date) return toast.error("Select a prediction date.");
    if (mode === "live" && !liveMeta) {
      setLiveError("Fetch live data before running a live prediction.");
      return toast.error("Fetch live data before predicting.");
    }
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
                <Label>Prediction Mode</Label>
                <div className="mt-1.5 grid grid-cols-2 rounded-md border border-border p-1">
                  <button type="button" onClick={() => setMode("manual")} className={`rounded px-3 py-2 text-sm font-medium transition-colors ${mode === "manual" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`} data-testid="predict-mode-manual">Manual Mode</button>
                  <button type="button" onClick={() => setMode("live")} className={`rounded px-3 py-2 text-sm font-medium transition-colors ${mode === "live" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`} data-testid="predict-mode-live">Live Data Mode</button>
                </div>
              </div>

              <div>
                <Label>Trained model</Label>
                <Select value={datasetId} onValueChange={setDatasetId}>
                  <SelectTrigger className="mt-1.5" data-testid="predict-dataset-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {datasets.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>

              {mode === "live" && (
                <div className="rounded-md border border-border p-4 space-y-4" data-testid="live-data-panel">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <Label htmlFor="live-country">Country</Label>
                      <Input id="live-country" value={liveLocation.country} onChange={setLiveField("country")} className="mt-1.5" placeholder="India" data-testid="live-country-input" />
                    </div>
                    <div>
                      <Label htmlFor="live-state">State <span className="text-muted-foreground font-normal">(optional)</span></Label>
                      <Input id="live-state" value={liveLocation.state} onChange={setLiveField("state")} className="mt-1.5" placeholder="Delhi" data-testid="live-state-input" />
                    </div>
                    <div>
                      <Label htmlFor="live-city">City</Label>
                      <Input id="live-city" value={liveLocation.city} onChange={setLiveField("city")} className="mt-1.5" placeholder="New Delhi" data-testid="live-city-input" />
                    </div>
                  </div>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <Button type="button" variant="outline" onClick={loadLiveData} disabled={liveLoading} data-testid="fetch-live-data-btn">
                      {liveLoading ? "Fetching live data..." : liveMeta ? "Retry / Refresh Live Data" : "Fetch Live Data"}
                    </Button>
                    {liveError && <p className="text-sm text-destructive">{liveError}</p>}
                  </div>
                  {liveMeta && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div><span className="text-muted-foreground">Last Updated:</span> {new Date(liveMeta.lastUpdated).toLocaleString()}</div>
                      <div><span className="text-muted-foreground">Data Source:</span> {liveMeta.source}{liveMeta.cached ? " (cached)" : ""}</div>
                      <div><span className="text-muted-foreground">Coordinates:</span> {liveMeta.coordinates.lat.toFixed(4)}, {liveMeta.coordinates.lon.toFixed(4)}</div>
                      <div><span className="text-muted-foreground">Current AQI:</span> {OPENWEATHER_AQI[liveMeta.currentAqi] || "Unavailable"}</div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {mode === "manual" && (
                  <div>
                    <Label htmlFor="loc">Location</Label>
                    <div className="relative mt-1.5">
                      <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <Input id="loc" value={location} onChange={(e) => setLocation(e.target.value)} className="pl-8" placeholder="e.g. Delhi" data-testid="predict-location-input" />
                    </div>
                  </div>
                )}
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
                <Button type="submit" size="lg" disabled={loading || liveLoading} data-testid="predict-submit-btn">
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
                    href={`${API_BASE}/reports/prediction/${result.id}`}
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
