import { AgentPulse } from "./AgentPulse";
import { isJobActive } from "@/hooks/use-halo";
import type { JobStatus } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

export const RUN_STATUS: Record<JobStatus, { label: string; cls: string }> = {
  queued: { label: "Queued", cls: "border-violet/40 bg-violet/10 text-violet" },
  running: { label: "Running", cls: "border-violet/40 bg-violet/10 text-violet" },
  cancelling: { label: "Stopping", cls: "border-amber-500/40 bg-amber-500/10 text-amber-400" },
  paused_budget: {
    label: "Paused at spending cap",
    cls: "border-amber-500/40 bg-amber-500/10 text-amber-400",
  },
  completed: { label: "Completed", cls: "border-teal/40 bg-teal/10 text-teal" },
  completed_with_errors: {
    label: "Done · a few steps skipped",
    cls: "border-amber-500/40 bg-amber-500/10 text-amber-400",
  },
  failed: { label: "Failed", cls: "border-coral/40 bg-coral/10 text-coral" },
  cancelled: { label: "Cancelled", cls: "border-border bg-surface-2 text-muted-foreground" },
};
export function RunStatusBadge({ status }: { status: JobStatus }) {
  const s = RUN_STATUS[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        s.cls,
      )}
    >
      {isJobActive(status) && <AgentPulse />}
      {s.label}
    </span>
  );
}
