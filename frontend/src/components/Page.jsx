export function PageHeader({ title, subtitle, actions, testid }) {
  return (
    <div className="border-b border-border bg-card/40" data-testid={testid || "page-header"}>
      <div className="mx-auto max-w-7xl px-6 py-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-bold tracking-tight">{title}</h1>
          {subtitle && <p className="text-muted-foreground mt-2 max-w-2xl">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export function PageBody({ children, className = "" }) {
  return <div className={`mx-auto max-w-7xl px-6 py-8 ${className}`}>{children}</div>;
}

export function StatCard({ label, value, mono = true, hint, icon: Icon, testid }) {
  return (
    <div className="aq-card p-5 aq-hover-lift" data-testid={testid}>
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
        {Icon && <Icon size={16} className="text-muted-foreground" />}
      </div>
      <div className={`mt-2 ${mono ? "font-mono" : "font-display"} text-3xl font-semibold`}>{value}</div>
      {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
    </div>
  );
}
