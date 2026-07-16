import { useEffect, useState } from "react";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { ChartLineUp, Compass } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function Forecast() {
  const [data, setData] = useState({ forecast: [], location: null, created_at: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const response = await api.get("/forecast/latest");
        setData(response.data);
      } catch (error) {
        toast.error(unwrapError(error));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <>
      <PageHeader
        title="AI AQI Forecast"
        subtitle="Seven-day future AQI predictions generated from the latest monitored location."
        actions={<Button asChild><Link to="/predict"><Compass size={16} className="mr-1.5" />Monitor Location</Link></Button>}
      />
      <PageBody>
        <div className="aq-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-semibold flex items-center gap-2"><ChartLineUp size={18} />7-Day AQI Line Chart</h2>
              <p className="text-sm text-muted-foreground">
                {data.location ? `${data.location} - generated ${new Date(data.created_at).toLocaleString()}` : "Generate an AI forecast to see future AQI."}
              </p>
            </div>
          </div>
          <div className="mt-6 h-80 min-w-0">
            {loading ? (
              <div className="h-full grid place-items-center text-sm text-muted-foreground">Loading forecast...</div>
            ) : data.forecast.length ? (
              <ResponsiveContainer>
                <LineChart data={data.forecast}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="day" tickFormatter={(day) => `D${day}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                  <Line type="monotone" dataKey="aqi" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full grid place-items-center text-center text-sm text-muted-foreground">
                <div>
                  <p>No AI forecast available yet.</p>
                  <Link to="/predict" className="text-primary hover:underline">Choose a location to generate one.</Link>
                </div>
              </div>
            )}
          </div>
        </div>

        {!loading && data.forecast.length ? (
          <div className="aq-scrollbar mt-6 grid max-h-[560px] grid-cols-1 gap-4 overflow-y-auto overflow-x-hidden pr-1 md:grid-cols-2 xl:grid-cols-4">
            {data.forecast.map((day) => (
              <div key={day.day} className="rounded-md border border-border bg-card p-4" style={{ borderLeft: `4px solid ${day.color}` }}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{day.label}</p>
                    <p className="text-xs text-muted-foreground">{day.date}</p>
                  </div>
                  <p className="font-mono text-2xl font-semibold">{Math.round(day.predicted_aqi)}</p>
                </div>
                <div className="mt-3 space-y-1 text-sm">
                  <p><span className="text-muted-foreground">Category:</span> {day.category}</p>
                  <p><span className="text-muted-foreground">Risk:</span> {day.risk}</p>
                  <p><span className="text-muted-foreground">Confidence:</span> {day.confidence}%</p>
                  <p><span className="text-muted-foreground">Weather:</span> {day.weather_summary}</p>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{day.health_advice}</p>
              </div>
            ))}
          </div>
        ) : null}
      </PageBody>
    </>
  );
}
