import { useEffect, useState } from "react";
import api from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { AQIBadge } from "@/components/AQIBadge";
import { FileText, FilePdf, FileCsv } from "@phosphor-icons/react";

export default function Reports() {
  const [datasets, setDatasets]     = useState([]);
  const [predictions, setPreds]     = useState([]);

  useEffect(() => {
    (async () => {
      const [ds, hs] = await Promise.all([api.get("/datasets"), api.get("/history")]);
      setDatasets(ds.data);
      setPreds(hs.data);
    })();
  }, []);

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Download PDF and CSV exports for your predictions, trained models, and raw datasets."
      />
      <PageBody className="space-y-6">
        <section>
          <h3 className="font-display text-lg font-semibold mb-3">Prediction reports</h3>
          {predictions.length === 0 ? (
            <div className="aq-card p-8 text-sm text-muted-foreground text-center">No predictions yet.</div>
          ) : (
            <div className="aq-card overflow-hidden">
              <table className="min-w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    {["Date","Location","Dataset","AQI","Category","PDF"].map((h) => (
                      <th key={h} className="text-left px-4 py-3 font-semibold text-xs uppercase tracking-wider text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((p) => (
                    <tr key={p.id} className="border-t border-border" data-testid={`prediction-row-${p.id}`}>
                      <td className="px-4 py-3 font-mono text-xs">{p.date || (p.created_at || "").slice(0, 10)}</td>
                      <td className="px-4 py-3">{p.location || "—"}</td>
                      <td className="px-4 py-3 text-xs truncate max-w-[220px]">{p.dataset_name}</td>
                      <td className="px-4 py-3 font-mono font-semibold" style={{ color: p.color }}>{Math.round(p.aqi)}</td>
                      <td className="px-4 py-3"><AQIBadge aqi={p.aqi} /></td>
                      <td className="px-4 py-3">
                        <a
                          href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/prediction/${p.id}`}
                          target="_blank" rel="noreferrer"
                          className="text-primary hover:underline text-xs inline-flex items-center gap-1"
                          data-testid={`download-pred-${p.id}`}
                        >
                          <FilePdf size={14} /> PDF
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h3 className="font-display text-lg font-semibold mb-3">Dataset & model reports</h3>
          {datasets.length === 0 ? (
            <div className="aq-card p-8 text-sm text-muted-foreground text-center">No datasets yet.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {datasets.map((d) => (
                <div key={d.id} className="aq-card p-5" data-testid={`report-card-${d.id}`}>
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{d.name}</div>
                      <div className="text-xs text-muted-foreground font-mono">{d.rows} rows · {d.trained ? d.best_model : "not trained"}</div>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <a
                      href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/dataset/${d.id}/csv`}
                      className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
                      data-testid={`download-csv-${d.id}`}
                    >
                      <FileCsv size={14} /> Raw CSV
                    </a>
                    {d.trained && (
                      <a
                        href={`${process.env.REACT_APP_BACKEND_URL}/api/reports/model/${d.id}`}
                        target="_blank" rel="noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent"
                        data-testid={`download-model-pdf-${d.id}`}
                      >
                        <FilePdf size={14} /> Model metrics PDF
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </PageBody>
    </>
  );
}
