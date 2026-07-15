import { useEffect, useMemo, useState } from "react";
import api, { API_BASE, unwrapError } from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { AQIBadge } from "@/components/AQIBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FilePdf, Trash, Eye, ShareNetwork, Printer } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Reports() {
  const [predictions, setPredictions] = useState([]);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("newest");
  const [selected, setSelected] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get("/history");
      setPredictions(data);
    } catch (error) {
      toast.error(unwrapError(error));
    }
  };

  useEffect(() => { load(); }, []);

  const rows = useMemo(
    () => predictions
      .filter((prediction) => `${prediction.location || ""} ${prediction.model || ""} ${prediction.category || ""}`.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => sort === "aqi"
        ? b.aqi - a.aqi
        : sort === "oldest"
          ? String(a.created_at).localeCompare(String(b.created_at))
          : String(b.created_at).localeCompare(String(a.created_at))),
    [predictions, query, sort]
  );

  const del = async (id) => {
    if (!window.confirm("Delete this prediction report?")) return;
    try {
      await api.delete(`/history/${id}`);
      setPredictions((items) => items.filter((prediction) => prediction.id !== id));
      toast.success("Report deleted.");
    } catch (error) {
      toast.error(unwrapError(error));
    }
  };

  const share = async (prediction) => {
    const url = `${API_BASE}/reports/prediction/${prediction.id}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "AeroPulse AQI report", text: `AQI ${Math.round(prediction.aqi)} - ${prediction.category}`, url });
      } else {
        await navigator.clipboard.writeText(url);
        toast.success("Report link copied.");
      }
    } catch {
      // User cancelled native share.
    }
  };

  return (
    <>
      <PageHeader title="Reports" subtitle="Search, review, share, print, and download AI air-quality prediction reports." />
      <PageBody className="space-y-6">
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <h2 className="font-display text-lg font-semibold">Prediction History</h2>
            <div className="flex gap-2">
              <Input aria-label="Search reports" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search location or model" className="w-56" />
              <select value={sort} onChange={(event) => setSort(event.target.value)} className="rounded-md border border-input bg-background px-3 text-sm">
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="aqi">Highest AQI</option>
              </select>
            </div>
          </div>
          {rows.length === 0 ? (
            <div className="aq-card p-8 text-center text-sm text-muted-foreground">
              {predictions.length ? "No reports match your search." : "No predictions yet."}
            </div>
          ) : (
            <div className="aq-card overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="bg-muted/50">
                  <tr>{["Date", "Location", "Model", "AQI", "Category", "Actions"].map((heading) => <th key={heading} className="text-left p-3 text-xs uppercase text-muted-foreground">{heading}</th>)}</tr>
                </thead>
                <tbody>
                  {rows.map((prediction) => (
                    <tr key={prediction.id} className="border-t border-border">
                      <td className="p-3 font-mono text-xs">{prediction.date || prediction.created_at?.slice(0, 10)}</td>
                      <td className="p-3">{prediction.location || "-"}</td>
                      <td className="p-3 max-w-[200px] truncate">{prediction.model || "AI model"}</td>
                      <td className="p-3 font-semibold" style={{ color: prediction.color }}>{Math.round(prediction.aqi)}</td>
                      <td className="p-3"><AQIBadge aqi={prediction.aqi} /></td>
                      <td className="p-3 flex gap-1">
                        <Button size="icon" variant="ghost" title="View" onClick={() => setSelected(prediction)}><Eye size={16} /></Button>
                        <a className="inline-flex h-9 w-9 items-center justify-center" title="Download PDF" href={`${API_BASE}/reports/prediction/${prediction.id}`} target="_blank" rel="noreferrer"><FilePdf size={17} /></a>
                        <Button size="icon" variant="ghost" title="Share" onClick={() => share(prediction)}><ShareNetwork size={16} /></Button>
                        <Button size="icon" variant="ghost" title="Delete" onClick={() => del(prediction.id)}><Trash size={16} /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {selected && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" onClick={() => setSelected(null)}>
            <div className="aq-card p-6 max-w-md w-full" onClick={(event) => event.stopPropagation()}>
              <h2 className="font-display text-xl font-semibold">Prediction Report</h2>
              <p className="mt-4 text-4xl font-bold" style={{ color: selected.color }}>{Math.round(selected.aqi)} AQI</p>
              <p className="mt-1">{selected.category}</p>
              <p className="mt-5 text-sm text-muted-foreground">{selected.advice}</p>
              <div className="mt-5 flex gap-2">
                <Button onClick={() => window.open(`${API_BASE}/reports/prediction/${selected.id}`, "_blank")}>Download PDF</Button>
                <Button variant="outline" onClick={() => window.print()}><Printer size={15} className="mr-1" />Print</Button>
              </div>
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}
