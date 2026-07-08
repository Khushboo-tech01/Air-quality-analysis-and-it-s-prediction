import { classifyAqi } from "@/lib/aqi";

export function AQIBadge({ aqi, className = "", size = "sm" }) {
  const cat = classifyAqi(aqi);
  const sizeCls = size === "lg" ? "px-3 py-1.5 text-sm" : "px-2 py-0.5 text-xs";
  return (
    <span
      data-testid="aqi-badge"
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold border ${sizeCls} ${className}`}
      style={{ color: cat.color, borderColor: `${cat.color}55`, background: `${cat.color}15` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: cat.color }} />
      {cat.label}
    </span>
  );
}
