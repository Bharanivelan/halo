import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

const COLORS = { fit: "var(--gold)", intent: "var(--coral)", confidence: "var(--teal)", priority: "var(--violet)" } as const;

export function ScoreRing({ value, kind = "fit", size = 64, label, className }: {
  value: number | null | undefined; kind?: keyof typeof COLORS; size?: number; label?: string; className?: string;
}) {
  const reduce = useReducedMotion();
  const stroke = Math.max(4, size / 12);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const v = value == null ? null : Math.max(0, Math.min(100, value));
  return (
    <div className={cn("inline-flex flex-col items-center gap-1.5", className)}>
      <div className="relative" style={{ width: size, height: size }} role="img" aria-label={`${label ?? kind} ${v ?? "unknown"}`}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
          {v != null && (
            <motion.circle
              cx={size / 2} cy={size / 2} r={r} fill="none" stroke={COLORS[kind]} strokeWidth={stroke} strokeLinecap="round"
              strokeDasharray={c}
              initial={{ strokeDashoffset: reduce ? c * (1 - v / 100) : c }}
              animate={{ strokeDashoffset: c * (1 - v / 100) }}
              transition={{ duration: 1, ease: "easeOut" }}
              style={{ filter: `drop-shadow(0 0 4px ${COLORS[kind]})` }}
            />
          )}
        </svg>
        <span className={cn("absolute inset-0 grid place-items-center font-mono font-semibold tabular", v == null && "text-muted-foreground")} style={{ fontSize: size / 3.6 }}>
          {v ?? "—"}
        </span>
      </div>
      {label && <span className="text-xs text-muted-foreground">{label}</span>}
    </div>
  );
}
