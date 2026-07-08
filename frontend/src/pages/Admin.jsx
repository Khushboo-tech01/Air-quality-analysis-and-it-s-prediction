import { useEffect, useState } from "react";
import api, { unwrapError } from "@/lib/api";
import { PageHeader, PageBody, StatCard } from "@/components/Page";
import { Button } from "@/components/ui/button";
import { AQIBadge } from "@/components/AQIBadge";
import { Users, Database, Compass, Brain, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Admin() {
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers]         = useState([]);
  const [datasets, setDatasets]   = useState([]);
  const [predictions, setPreds]   = useState([]);

  const load = async () => {
    try {
      const [a, u, d, p] = await Promise.all([
        api.get("/admin/analytics"),
        api.get("/admin/users"),
        api.get("/admin/datasets"),
        api.get("/admin/predictions"),
      ]);
      setAnalytics(a.data); setUsers(u.data); setDatasets(d.data); setPreds(p.data);
    } catch (err) { toast.error(unwrapError(err)); }
  };

  useEffect(() => { load(); }, []);

  const removeUser = async (id) => {
    if (!window.confirm("Delete this user?")) return;
    try {
      await api.delete(`/admin/users/${id}`);
      toast.success("User deleted.");
      load();
    } catch (err) { toast.error(unwrapError(err)); }
  };
  const removeDataset = async (id) => {
    if (!window.confirm("Delete this dataset?")) return;
    try {
      await api.delete(`/admin/datasets/${id}`);
      toast.success("Dataset deleted.");
      load();
    } catch (err) { toast.error(unwrapError(err)); }
  };

  return (
    <>
      <PageHeader title="Admin dashboard" subtitle="Users, datasets, model performance, and platform analytics." />
      <PageBody>
        {analytics && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatCard label="Users"       value={analytics.users}       icon={Users}    testid="admin-stat-users" />
            <StatCard label="Datasets"    value={analytics.datasets}    icon={Database} testid="admin-stat-datasets" />
            <StatCard label="Predictions" value={analytics.predictions} icon={Compass}  testid="admin-stat-predictions" />
            <StatCard label="Trained Models" value={analytics.trained_models} icon={Brain} testid="admin-stat-trained" />
            <StatCard label="Last 7 days" value={analytics.recent_predictions_7d} testid="admin-stat-7d" />
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="aq-card overflow-hidden">
            <div className="p-4 border-b border-border"><h3 className="font-display text-lg font-semibold">Users</h3></div>
            <div className="overflow-auto max-h-[480px]">
              <table className="min-w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    {["Name","Email","Role","Joined",""].map((h) => (
                      <th key={h} className="text-left px-4 py-2 font-semibold text-xs uppercase tracking-wider text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-t border-border" data-testid={`admin-user-${u.id}`}>
                      <td className="px-4 py-2 font-medium">{u.name}</td>
                      <td className="px-4 py-2 font-mono text-xs">{u.email}</td>
                      <td className="px-4 py-2"><span className={`text-xs px-2 py-0.5 rounded-full ${u.role === "admin" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}>{u.role}</span></td>
                      <td className="px-4 py-2 text-xs text-muted-foreground">{(u.created_at || "").slice(0, 10)}</td>
                      <td className="px-4 py-2">
                        {u.role !== "admin" && (
                          <button onClick={() => removeUser(u.id)} className="text-muted-foreground hover:text-destructive" data-testid={`admin-delete-user-${u.id}`}>
                            <Trash size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="aq-card overflow-hidden">
            <div className="p-4 border-b border-border"><h3 className="font-display text-lg font-semibold">Datasets</h3></div>
            <div className="overflow-auto max-h-[480px]">
              <table className="min-w-full text-sm">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    {["Name","Rows","Trained","Uploaded",""].map((h) => (
                      <th key={h} className="text-left px-4 py-2 font-semibold text-xs uppercase tracking-wider text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((d) => (
                    <tr key={d.id} className="border-t border-border" data-testid={`admin-dataset-${d.id}`}>
                      <td className="px-4 py-2 truncate max-w-[220px]">{d.name}</td>
                      <td className="px-4 py-2 font-mono text-xs">{d.rows}</td>
                      <td className="px-4 py-2">
                        {d.trained ? <span className="text-success text-xs">● {d.best_model}</span> : <span className="text-muted-foreground text-xs">○</span>}
                      </td>
                      <td className="px-4 py-2 text-xs text-muted-foreground">{(d.created_at || "").slice(0, 10)}</td>
                      <td className="px-4 py-2">
                        <button onClick={() => removeDataset(d.id)} className="text-muted-foreground hover:text-destructive" data-testid={`admin-delete-dataset-${d.id}`}>
                          <Trash size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="mt-6 aq-card overflow-hidden">
          <div className="p-4 border-b border-border"><h3 className="font-display text-lg font-semibold">Recent predictions (all users)</h3></div>
          <div className="overflow-auto max-h-[420px]">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/50 sticky top-0">
                <tr>
                  {["Time","Location","AQI","Category","Model"].map((h) => (
                    <th key={h} className="text-left px-4 py-2 font-semibold text-xs uppercase tracking-wider text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => (
                  <tr key={p.id} className="border-t border-border">
                    <td className="px-4 py-2 font-mono text-xs">{(p.created_at || "").slice(0, 16).replace("T", " ")}</td>
                    <td className="px-4 py-2">{p.location || "—"}</td>
                    <td className="px-4 py-2 font-mono font-semibold" style={{ color: p.color }}>{Math.round(p.aqi)}</td>
                    <td className="px-4 py-2"><AQIBadge aqi={p.aqi} /></td>
                    <td className="px-4 py-2 text-xs">{p.model}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </PageBody>
    </>
  );
}
