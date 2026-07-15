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
        title="AQI Forecast"
        subtitle="Seven-day AQI forecast generated from the latest monitored location."
        actions={<Button asChild><Link to="/predict"><Compass size={16} className="mr-1.5" />Monitor Location</Link></Button>}
      />
      <PageBody>
        <div className="aq-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-semibold flex items-center gap-2"><ChartLineUp size={18} />Latest Forecast</h2>
              <p className="text-sm text-muted-foreground">{data.location ? `${data.location} · generated ${new Date(data.created_at).toLocaleString()}` : "Run an AQI prediction to generate a forecast."}</p>
            </div>
          </div>
          <div className="h-80 mt-6">
            {loading ? (
              <div className="h-full grid place-items-center text-sm text-muted-foreground">Loading forecast...</div>
            ) : data.forecast.length ? (
              <ResponsiveContainer>
                <LineChart data={data.forecast}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="day" tickFormatter={(day) => `D${day}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                  <Line type="monotone" dataKey="aqi" stroke="#2563EB" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full grid place-items-center text-center text-sm text-muted-foreground">
                <div>
                  <p>No forecast available yet.</p>
                  <Link to="/predict" className="text-primary hover:underline">Choose a location to generate one.</Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </PageBody>
    </>
  );
}
