import { cn } from "@/lib/utils";

export function AgentPulse({ active = true, className }: { active?: boolean; className?: string }) {
  return (
    <span className={cn("relative inline-flex size-2.5", className)} aria-hidden>
      {active && <span className="anim-halo-pulse absolute inset-0 rounded-full bg-violet" />}
      <span className={cn("relative size-2.5 rounded-full", active ? "bg-violet shadow-[0_0_8px_var(--violet)]" : "bg-slate")} />
    </span>
  );
}
