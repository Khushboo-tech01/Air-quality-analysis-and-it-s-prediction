import { classifyAqi } from "@/lib/aqi";
import { motion } from "framer-motion";

// Semi-circular gauge for AQI
export function AQIGauge({ aqi }) {
  const cat = classifyAqi(aqi);
  // clamp to 0..500 across a 180° arc
  const pct = Math.min(1, Math.max(0, cat.value / 500));
  const angle = -90 + pct * 180; // -90 (left) → +90 (right)

  return (
    <div className="flex flex-col items-center" data-testid="aqi-gauge">
      <svg viewBox="0 0 200 120" className="w-full max-w-sm">
        <defs>
          <linearGradient id="aq-arc" x1="0" x2="1">
            <stop offset="0%"   stopColor="#10B981" />
            <stop offset="20%"  stopColor="#F59E0B" />
            <stop offset="40%"  stopColor="#F97316" />
            <stop offset="60%"  stopColor="#EF4444" />
            <stop offset="80%"  stopColor="#8B5CF6" />
            <stop offset="100%" stopColor="#7F1D1D" />
          </linearGradient>
        </defs>
        {/* Track */}
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="hsl(var(--muted))" strokeWidth="14" strokeLinecap="round" />
        {/* Colour arc */}
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#aq-arc)" strokeWidth="14" strokeLinecap="round" strokeDasharray={`${pct * 251.3} 251.3`} />
        {/* Needle */}
        <motion.line
          x1="100" y1="100" x2="100" y2="30"
          stroke={cat.color} strokeWidth="3" strokeLinecap="round"
          style={{ transformOrigin: "100px 100px" }}
          initial={{ rotate: -90 }}
          animate={{ rotate: angle }}
          transition={{ type: "spring", stiffness: 60, damping: 12 }}
        />
        <circle cx="100" cy="100" r="6" fill={cat.color} />
      </svg>
      <div className="mt-2 flex flex-col items-center">
        <span className="font-mono text-5xl font-bold" style={{ color: cat.color }} data-testid="aqi-value">
          {Math.round(cat.value)}
        </span>
        <span className="text-sm font-semibold text-foreground mt-1">{cat.label}</span>
      </div>
    </div>
  );
}
