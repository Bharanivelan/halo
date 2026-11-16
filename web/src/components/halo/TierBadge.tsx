import { cn } from "@/lib/utils";

const TIERS = {
  A: { label: "Hot", cls: "bg-gold/15 text-gold border-gold/40 shadow-[0_0_14px_-4px_var(--gold)]" },
  B: { label: "Warm", cls: "bg-teal/15 text-teal border-teal/40" },
  C: { label: "Cool", cls: "bg-slate/15 text-muted-foreground border-slate/40" },
} as const;

export function TierBadge({ tier, className }: { tier: "A" | "B" | "C" | null | undefined; className?: string }) {
  if (!tier) return <span className={cn("text-xs text-muted-foreground", className)}>Unknown</span>;
  const t = TIERS[tier];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold", t.cls, className)}>
      <span className="font-mono">{tier}</span>·<span>{t.label}</span>
    </span>
  );
}
