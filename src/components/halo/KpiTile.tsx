import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

function CountUp({ value, format }: { value: number; format?: (n: number) => string }) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? value : 0);
  useEffect(() => {
    if (reduce) { setN(value); return; }
    const c = animate(0, value, { duration: 1.1, ease: "easeOut", onUpdate: setN });
    return () => c.stop();
  }, [value, reduce]);
  return <>{format ? format(n) : Math.round(n).toLocaleString("en-IN")}</>;
}

export function KpiTile({ label, value, format, sub, accent = false, icon, className }: {
  label: string; value: number | null | undefined; format?: (n: number) => string; sub?: ReactNode; accent?: boolean; icon?: ReactNode; className?: string;
}) {
  return (
    <div className={cn("card-halo p-5", className)}>
      <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
        <span>{label}</span>{icon}
      </div>
      <div className={cn("mt-3 font-mono text-3xl font-semibold tabular", accent && "text-signature", value == null && "text-muted-foreground")}>
        {value == null ? "—" : <CountUp value={value} format={format} />}
      </div>
      {sub && <div className="mt-1.5 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}
