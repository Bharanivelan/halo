import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  Ban,
  Check,
  Circle,
  Loader2,
  Minus,
  PauseCircle,
  RotateCcw,
  Terminal,
  TriangleAlert,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  AgentPulse,
  CardSkeleton,
  ErrorState,
  HaloRadar,
  SectionTitle,
  errorText,
} from "@/components/halo";
import { RunStatusBadge } from "@/components/halo/RunStatus";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  isJobActive,
  useAccountsMap,
  useCancelRun,
  useProperty,
  useResumeRun,
  useRetryFailed,
  useRun,
} from "@/hooks/use-halo";
import { ago, dateTime, duration, usd } from "@/lib/halo-format";
import type { Stage, StageStatus } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

const STAGE_ICON: Record<StageStatus, { icon: React.ReactNode; cls: string }> = {
  pending: {
    icon: <Circle className="size-3.5" />,
    cls: "border-border bg-surface-2 text-muted-foreground",
  },
  running: {
    icon: <Loader2 className="size-3.5 animate-spin" />,
    cls: "border-violet/60 bg-violet/20 text-violet shadow-[0_0_16px_-2px_var(--violet)]",
  },
  succeeded: { icon: <Check className="size-3.5" />, cls: "border-teal/50 bg-teal/15 text-teal" },
  partial: {
    icon: <TriangleAlert className="size-3.5" />,
    cls: "border-amber-500/50 bg-amber-500/15 text-amber-400",
  },
  failed: { icon: <X className="size-3.5" />, cls: "border-coral/50 bg-coral/15 text-coral" },
  skipped: {
    icon: <Minus className="size-3.5" />,
    cls: "border-border bg-surface-2 text-muted-foreground",
  },
};

function StageRow({ s, last }: { s: Stage; last: boolean }) {
  const st = STAGE_ICON[s.status];
  const total =
    s.counts.pending + s.counts.running + s.counts.succeeded + s.counts.failed + s.counts.skipped;
  const done = s.counts.succeeded + s.counts.failed + s.counts.skipped;
  return (
    <li className="relative flex gap-4 pb-6 last:pb-0">
      {!last && (
        <span
          className={cn(
            "absolute left-[15px] top-8 h-[calc(100%-2rem)] w-px",
            s.status === "succeeded" ? "bg-teal/40" : "bg-border",
          )}
        />
      )}
      <span
        className={cn(
          "relative z-10 grid size-8 shrink-0 place-items-center rounded-full border",
          st.cls,
        )}
      >
        {st.icon}
      </span>
      <div className="min-w-0 flex-1 pt-1">
        <div className="flex items-center justify-between gap-2">
          <span className={cn("font-medium", s.status === "pending" && "text-muted-foreground")}>
            {s.label}
          </span>
          {total > 1 && (
            <span className="font-mono text-xs text-muted-foreground">
              {done}/{total}
            </span>
          )}
        </div>
        {s.detail && <p className="mt-0.5 text-sm text-muted-foreground">{s.detail}</p>}
        {s.status === "running" && total > 1 && (
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-violet transition-[width] duration-700"
              style={{ width: `${(done / total) * 100}%` }}
            />
          </div>
        )}
        {s.counts.failed > 0 && <p className="mt-1 text-xs text-coral">{s.counts.failed} failed</p>}
      </div>
    </li>
  );
}

function BigProgress({ value, active }: { value: number; active: boolean }) {
  const reduce = useReducedMotion();
  const size = 168,
    stroke = 10,
    r = (size - stroke) / 2,
    c = 2 * Math.PI * r;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="runprog" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--violet)" />
            <stop offset="100%" stopColor="var(--gold)" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--surface-2)"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#runprog)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: reduce ? c * (1 - value) : c }}
          animate={{ strokeDashoffset: c * (1 - value) }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          style={{ filter: "drop-shadow(0 0 6px var(--violet))" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="font-mono text-4xl font-semibold tabular">
            {Math.round(value * 100)}
            <span className="text-lg text-muted-foreground">%</span>
          </div>
          <div className="mt-0.5 flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
            {active && <AgentPulse />}
            {active ? "working" : "progress"}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AgentRunPage() {
  const { propertyId, jobId } = useParams({ strict: false }) as {
    propertyId: string;
    jobId: string;
  };
  const run = useRun(jobId);
  const prop = useProperty(propertyId);
  const j = run.data;
  const active = isJobActive(j?.status);
  const { data: points, refetch: refetchMap } = useAccountsMap(propertyId);
  const cancel = useCancelRun();
  const retry = useRetryFailed();
  const resume = useResumeRun();
  const [resumeOpen, setResumeOpen] = useState(false);
  const [budget, setBudget] = useState(5);
  const logRef = useRef<HTMLDivElement>(null);
  const events = j?.events ?? [];

  // Refresh the radar as companies get scored.
  useEffect(() => {
    if (active) void refetchMap();
  }, [j?.counts.scored, active, refetchMap]);
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  if (run.error) return <ErrorState error={run.error} onRetry={() => void run.refetch()} />;
  if (!j)
    return (
      <div className="mx-auto max-w-7xl space-y-5">
        <CardSkeleton lines={4} />
        <CardSkeleton lines={8} />
      </div>
    );

  const onErr = (e: unknown) => {
    const t = errorText(e);
    toast.error(t.title, { description: t.detail });
  };
  const finished = !active;
  const stats = [
    { k: "Found", v: j.counts.found },
    { k: "Companies", v: j.counts.companies },
    { k: "Researched", v: j.counts.researched },
    { k: "Scored", v: j.counts.scored },
    { k: "Failed", v: j.counts.failed, bad: j.counts.failed > 0 },
  ];
  const spendPct = Math.min(100, (j.spent_usd / Math.max(0.01, j.budget_usd)) * 100);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">
            {j.property_name} · started {ago(j.created_at)} by {j.created_by}
          </p>
          <h1 className="mt-1 flex flex-wrap items-center gap-3 text-[32px] font-bold leading-tight">
            Agent run <RunStatusBadge status={j.status} />
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {active && (
            <Button
              variant="outline"
              className="rounded-xl"
              disabled={cancel.isPending || j.status === "cancelling"}
              onClick={() => cancel.mutate(j.id, { onError: onErr })}
            >
              <Ban />
              Stop
            </Button>
          )}
          {j.status === "paused_budget" && (
            <Button
              variant="outline"
              className="rounded-xl"
              onClick={() => {
                setBudget(Math.ceil(j.budget_usd * 2));
                setResumeOpen(true);
              }}
            >
              <PauseCircle />
              Raise cap & resume
            </Button>
          )}
          {finished && j.counts.failed > 0 && (
            <Button
              variant="outline"
              className="rounded-xl"
              disabled={retry.isPending}
              onClick={() =>
                retry.mutate(j.id, {
                  onError: onErr,
                  onSuccess: () => toast.success("Retrying failed companies"),
                })
              }
            >
              <RotateCcw />
              Retry {j.counts.failed} failed
            </Button>
          )}
          {j.counts.scored > 0 && (
            <Button variant="signature" className="rounded-xl" asChild>
              <Link to="/p/$propertyId/accounts" params={{ propertyId }} search={{ job: j.id }}>
                See {j.counts.scored} prospects
                <ArrowRight />
              </Link>
            </Button>
          )}
        </div>
      </div>

      {j.error && (
        <p className="rounded-xl border border-coral/30 bg-coral/10 p-3 text-sm text-coral">
          {j.error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Progress + radar */}
        <div className="card-halo relative overflow-hidden p-6 lg:col-span-2">
          {active && (
            <div className="pointer-events-none absolute -left-24 -top-24 size-72 rounded-full bg-violet/20 blur-3xl" />
          )}
          <div className="relative grid items-center gap-6 sm:grid-cols-[auto_1fr]">
            <BigProgress value={j.progress} active={active} />
            <div>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {stats.map((s) => (
                  <div key={s.k} className="rounded-xl bg-surface-2 p-3 text-center">
                    <div
                      className={cn(
                        "font-mono text-2xl font-semibold tabular",
                        s.bad && "text-coral",
                      )}
                    >
                      {s.v}
                    </div>
                    <div className="text-[11px] text-muted-foreground">{s.k}</div>
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>AI spend</span>
                  <span className="font-mono">
                    {usd(j.spent_usd)} of {usd(j.budget_usd)} cap
                  </span>
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className={cn(
                      "h-full rounded-full transition-[width] duration-700",
                      spendPct > 85 ? "bg-coral" : "bg-gold",
                    )}
                    style={{ width: `${spendPct}%` }}
                  />
                </div>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Running for {duration(j.started_at ?? j.created_at, j.finished_at)}
                {j.finished_at ? ` · finished ${dateTime(j.finished_at)}` : ""}
              </p>
            </div>
          </div>
          {prop.data && (
            <div className="relative mt-6 grid items-center gap-6 border-t border-border pt-6 sm:grid-cols-[220px_1fr]">
              <HaloRadar
                center={prop.data.location}
                radiusKm={j.config.radius_km}
                points={points}
                sweep={active}
                labels={false}
              />
              <div className="text-sm text-muted-foreground">
                <p className="font-medium text-foreground">The halo is filling in</p>
                <p className="mt-1">
                  Each company lights up as it's scored. Gold dots are hot prospects worth calling
                  this week.
                </p>
                <p className="mt-3 font-mono text-xs">
                  {j.config.radius_km} km · up to {j.config.max_companies} companies ·{" "}
                  {j.config.research_depth} research
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Stages */}
        <div className="card-halo p-5">
          <SectionTitle>What the agent is doing</SectionTitle>
          <ol>
            {j.stages.map((s, i) => (
              <StageRow key={s.key} s={s} last={i === j.stages.length - 1} />
            ))}
          </ol>
        </div>
      </div>

      {/* Live log */}
      <div className="card-halo overflow-hidden">
        <div className="flex items-center gap-2 border-b border-border px-5 py-3 text-sm">
          <Terminal className="size-4 text-gold" />
          <span className="font-medium">Live log</span>
          {active && (
            <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-violet">
              <AgentPulse />
              streaming
            </span>
          )}
        </div>
        <div
          ref={logRef}
          className="max-h-80 overflow-y-auto bg-background/60 p-4 font-mono text-xs leading-relaxed"
        >
          {events.length === 0 ? (
            <p className="text-muted-foreground">Waiting for the first event…</p>
          ) : (
            events.map((e) => (
              <div key={e.id} className="flex gap-3">
                <span className="shrink-0 text-muted-foreground/60">
                  {new Date(e.created_at).toLocaleTimeString("en-IN", { hour12: false })}
                </span>
                {e.stage && <span className="w-20 shrink-0 truncate text-violet">{e.stage}</span>}
                <span
                  className={cn(
                    e.level === "error"
                      ? "text-coral"
                      : e.level === "warning"
                        ? "text-amber-400"
                        : "text-foreground/85",
                  )}
                >
                  {e.message}
                </span>
              </div>
            ))
          )}
          {active && <div className="mt-1 h-3 w-2 animate-pulse bg-gold" />}
        </div>
      </div>

      <Dialog open={resumeOpen} onOpenChange={setResumeOpen}>
        <DialogContent className="rounded-2xl border-border bg-surface">
          <DialogHeader>
            <DialogTitle className="font-display">Raise the spending cap</DialogTitle>
            <DialogDescription>
              The run paused at {usd(j.spent_usd)}. Set a new total cap to continue where it
              stopped.
            </DialogDescription>
          </DialogHeader>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
              $
            </span>
            <Input
              type="number"
              min={j.spent_usd}
              max={500}
              step={0.5}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="pl-7 font-mono"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setResumeOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="signature"
              disabled={resume.isPending || budget <= j.spent_usd || budget > 500}
              onClick={() =>
                resume.mutate(
                  { id: j.id, budget },
                  { onError: onErr, onSuccess: () => setResumeOpen(false) },
                )
              }
            >
              Resume
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
