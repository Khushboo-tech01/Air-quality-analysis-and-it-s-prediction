import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { UploadSimple, FileCsv, Trash, Database, Sparkle, ArrowRight } from "@phosphor-icons/react";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";

export default function Upload() {
  const [datasets, setDatasets] = useState([]);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/datasets");
      setDatasets(data);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onDrop = useCallback(async (files) => {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) return toast.error("Only .csv files are supported.");
    setUploading(true);
    setProgress(5);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/datasets/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 90) + 5);
        },
      });
      setProgress(100);
      toast.success(`Uploaded ${data.rows} rows.`);
      await load();
      nav(`/dataset/${data.id}`);
    } catch (err) {
      toast.error(unwrapError(err));
    } finally {
      setUploading(false);
      setTimeout(() => setProgress(0), 400);
    }
  }, [load, nav]);

  const seed = async () => {
    setUploading(true);
    try {
      const { data } = await api.post("/datasets/seed-sample");
      toast.success(`Sample dataset created — ${data.rows} rows.`);
      await load();
      nav(`/dataset/${data.id}`);
    } catch (err) {
      toast.error(unwrapError(err));
    } finally { setUploading(false); }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this dataset?")) return;
    try {
      await api.delete(`/datasets/${id}`);
      toast.success("Dataset deleted.");
      load();
    } catch (err) { toast.error(unwrapError(err)); }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: false, accept: { "text/csv": [".csv"] },
  });

  return (
    <>
      <PageHeader
        title="Datasets"
        subtitle="Drop a CSV to begin. AeroPulse auto-detects date, location, and pollutant columns."
        actions={<Button variant="outline" onClick={seed} disabled={uploading} data-testid="seed-sample-btn"><Sparkle size={16} className="mr-1.5" /> Use sample dataset</Button>}
      />
      <PageBody>
        <div
          {...getRootProps()}
          className={`aq-card border-2 border-dashed p-10 text-center cursor-pointer transition-colors ${
            isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
          }`}
          data-testid="upload-dropzone"
        >
          <input {...getInputProps()} data-testid="upload-file-input" />
          <div className="mx-auto h-12 w-12 rounded-md bg-primary/10 text-primary flex items-center justify-center">
            <UploadSimple size={22} weight="bold" />
          </div>
          <p className="mt-4 font-display text-lg font-semibold">
            {isDragActive ? "Drop the file here" : "Drag & drop your CSV, or click to browse"}
          </p>
          <p className="text-sm text-muted-foreground mt-1">Kaggle · OpenAQ · UCI · CPCB compatible. Max 25 MB.</p>
          {uploading && (
            <div className="mt-6 max-w-md mx-auto">
              <Progress value={progress} data-testid="upload-progress" />
              <p className="text-xs text-muted-foreground mt-2">Uploading… {progress}%</p>
            </div>
          )}
        </div>

        <div className="mt-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-xl font-semibold">Your datasets</h2>
            <span className="text-sm text-muted-foreground">{datasets.length} total</span>
          </div>

          {loading ? (
            <div className="aq-card p-12 text-center text-muted-foreground">Loading…</div>
          ) : datasets.length === 0 ? (
            <div className="aq-card p-12 text-center">
              <Database size={28} className="mx-auto text-muted-foreground" />
              <p className="mt-3 font-medium">No datasets yet</p>
              <p className="text-sm text-muted-foreground">Upload a CSV or seed a sample to explore the pipeline.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {datasets.map((d) => (
                <div key={d.id} className="aq-card p-5 aq-hover-lift" data-testid={`dataset-card-${d.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <Link to={`/dataset/${d.id}`} className="flex items-center gap-2 min-w-0 flex-1">
                      <div className="h-8 w-8 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0"><FileCsv size={16} weight="fill" /></div>
                      <div className="min-w-0">
                        <div className="truncate font-medium">{d.name}</div>
                        <div className="text-xs text-muted-foreground font-mono">{d.rows} rows · {d.columns?.length ?? 0} cols</div>
                      </div>
                    </Link>
                    <button onClick={() => remove(d.id)} className="text-muted-foreground hover:text-destructive p-1" data-testid={`delete-dataset-${d.id}`}>
                      <Trash size={16} />
                    </button>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs">
                      {d.trained ? <span className="text-success">● trained</span> : <span className="text-muted-foreground">○ not trained</span>}
                    </span>
                    <Button size="sm" variant="ghost" asChild data-testid={`open-dataset-${d.id}`}>
                      <Link to={`/dataset/${d.id}`}>Open <ArrowRight size={14} className="ml-1" /></Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </PageBody>
    </>
  );
}
