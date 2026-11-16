import { cn } from "@/lib/utils";

export function SignalChip({ label, age, className }: { label: string; age?: string | null; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border border-coral/30 bg-coral/10 px-2.5 py-0.5 text-xs", className)}>
      <span className="size-1.5 rounded-full bg-coral shadow-[0_0_6px_var(--coral)]" />
      <span className="font-medium">{label}</span>
      {age && <span className="font-mono text-muted-foreground">· {age}</span>}
    </span>
  );
}
