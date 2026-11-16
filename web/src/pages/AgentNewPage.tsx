import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Coins,
  FileSpreadsheet,
  Loader2,
  Rocket,
  Sparkles,
  Wand2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { halo } from "@/lib/halo-api";
import {
  AgentPulse,
  CardSkeleton,
  ErrorState,
  HaloRadar,
  SectionTitle,
  errorText,
  Explain,
} from "@/components/halo";
import { RunStatusBadge } from "@/components/halo/RunStatus";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import {
  isJobActive,
  useEstimate,
  useParseRequest,
  useProperty,
  useReference,
  useRuns,
  useStartRun,
} from "@/hooks/use-halo";
import { ago, dist, duration, fromUnit, OFFERING_LABEL, toUnit, usd } from "@/lib/halo-format";
import type {
  DiscoveryConfig,
  JobStatus,
  Offering,
  ParseResult,
  ProviderKey,
} from "@/lib/halo-types";
import { cn } from "@/lib/utils";

const OFFERINGS: Offering[] = ["corporate_rate", "mice", "long_stay", "fnb"];
const WINDOWS = [90, 180, 365, 730];
const EXAMPLES = [
  "IT and consulting firms within 5 miles that are hiring",
  "Manufacturers with 200+ staff who could need long stays",
  "Companies that host events or training programmes",
];

function useDebounced<T>(v: T, ms = 450) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const t = setTimeout(() => setD(v), ms);
    return () => clearTimeout(t);
  }, [v, ms]);
  return d;
}

function Chip({
  on,
  children,
  onClick,
  disabled,
  title,
}: {
  on: boolean;
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  title?: string | undefined;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        "rounded-full border px-3 py-1 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        on
          ? "border-gold/50 bg-gold/15 text-gold"
          : "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function RangeStat({
  icon,
  label,
  r,
  fmt,
}: {
  icon: React.ReactNode;
  label: string;
  r: { low: number; expected: number; high: number } | undefined;
  fmt: (n: number) => string;
}) {
  return (
    <div className="rounded-xl bg-surface-2 p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="mt-1 font-mono text-xl font-semibold tabular">
        {r ? fmt(r.expected) : "—"}
      </div>
      <div className="font-mono text-[11px] text-muted-foreground">
        {r ? `${fmt(r.low)} – ${fmt(r.high)}` : " "}
      </div>
    </div>
  );
}

export function AgentNewPage() {
  const { propertyId } = useParams({ strict: false }) as { propertyId: string };
  const navigate = useNavigate();
  const prop = useProperty(propertyId);
  const unit = prop.data?.distance_unit ?? "mi";
  const { data: ref } = useReference();
  const runs = useRuns(propertyId);
  const parse = useParseRequest();
  const start = useStartRun();
  const [cfg, setCfg] = useState<DiscoveryConfig | null>(null);
  const [brief, setBrief] = useState("");
  const [patch, setPatch] = useState<ParseResult["patch"] | null>(null);
  const [csv, setCsv] = useState<{ name: string; rows: number } | null>(null);
  const [csvBusy, setCsvBusy] = useState(false);

  /** Upload a list of known companies; the run then researches them alongside the map search. */
  const uploadCsv = async (file: File) => {
    if (!cfg) return;
    setCsvBusy(true);
    try {
      const imp = await halo.importCsv(propertyId, file);
      if (imp.status !== "parsed" || imp.row_count === 0) {
        toast.error("Couldn't read that file", {
          description: imp.errors[0]?.message ?? "Use a CSV with a 'Company' column.",
        });
        return;
      }
      setCsv({ name: imp.file_name, rows: imp.row_count });
      setCfg({
        ...cfg,
        csv_import_id: imp.id,
        sources: cfg.sources.includes("csv") ? cfg.sources : [...cfg.sources, "csv"],
      });
      toast.success(`${imp.row_count} companies added from ${imp.file_name}`);
    } catch (e) {
      const t = errorText(e);
      toast.error(t.title, { description: t.detail });
    } finally {
      setCsvBusy(false);
    }
  };
  const removeCsv = () => {
    if (!cfg) return;
    setCsv(null);
    setCfg({ ...cfg, csv_import_id: null, sources: cfg.sources.filter((s) => s !== "csv") });
  };

  // Seed the config from the location's saved target profile.
  useEffect(() => {
    if (!prop.data || !ref || cfg) return;
    const p = prop.data;
    const sources = ref.providers.filter((x) => x.enabled && x.key !== "csv").map((x) => x.key);
    setCfg({
      property_id: p.id,
      radius_km: p.target.radius_km,
      industries: p.target.industries,
      employee_min: p.target.employee_min,
      employee_max: p.target.employee_max,
      offerings_focus: p.offerings,
      sources,
      csv_import_id: null,
      max_companies: 50,
      research_depth: "standard",
      signal_window_days: ref.scoring.signal_window_days || 365,
      prioritisation_notes: p.target.notes,
      budget_usd: 5,
    });
  }, [prop.data, ref, cfg]);

  const set = <K extends keyof DiscoveryConfig>(k: K, v: DiscoveryConfig[K]) =>
    setCfg((c) => (c ? { ...c, [k]: v } : c));
  const toggle = <T extends string>(arr: T[], v: T) =>
    arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
  const debounced = useDebounced(cfg);
  const est = useEstimate(debounced);
  const active = runs.data?.find((r) => isJobActive(r.status));
  const industryLabel = useMemo(
    () => new Map(ref?.industries.map((i) => [i.code, i.label])),
    [ref],
  );

  if (prop.error) return <ErrorState error={prop.error} onRetry={() => void prop.refetch()} />;

  const runBrief = () => {
    if (!cfg || !brief.trim()) return;
    parse.mutate(
      { propertyId, text: brief, config: cfg },
      {
        onSuccess: (r) => {
          setCfg(r.config);
          setPatch(r.patch);
          toast.success(
            r.patch.length
              ? `Applied ${r.patch.length} change${r.patch.length > 1 ? "s" : ""}`
              : "Nothing to change",
          );
        },
      },
    );
  };
  const launch = () => {
    if (!cfg) return;
    start.mutate(cfg, {
      onSuccess: (r) =>
        void navigate({
          to: "/p/$propertyId/agent/$jobId",
          params: { propertyId, jobId: r.job_id },
        }),
      onError: (e) => {
        const t = errorText(e);
        toast.error(t.title, { description: t.detail });
      },
    });
  };
  const fmtVal = (v: unknown) =>
    Array.isArray(v)
      ? v.length
        ? v
            .map((x) => industryLabel.get(String(x)) ?? OFFERING_LABEL[x as Offering] ?? String(x))
            .join(", ")
        : "none"
      : v == null || v === ""
        ? "—"
        : String(v);

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-8">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Sparkles className="size-4 text-gold" />
          {prop.data?.name ?? "Hotel"}
        </p>
        <h1 className="mt-1 text-[32px] font-bold leading-tight">Brief the agent</h1>
        <p className="mt-1 text-muted-foreground">
          Tell Halo who you want to find. It searches, researches every company and scores who to
          call first.
        </p>
      </div>

      {active && (
        <Link
          to="/p/$propertyId/agent/$jobId"
          params={{ propertyId, jobId: active.id }}
          className="mb-6 flex items-center gap-3 rounded-xl border border-violet/40 bg-violet/10 p-3 text-sm hover:border-violet/70"
        >
          <AgentPulse />A run is already in progress for this hotel (
          {Math.round(active.progress * 100)}%).
          <span className="ml-auto flex items-center gap-1 text-violet">
            Watch
            <ArrowRight className="size-4" />
          </span>
        </Link>
      )}

      {!cfg ? (
        <div className="grid gap-5 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CardSkeleton lines={8} />
          </div>
          <CardSkeleton lines={6} />
        </div>
      ) : (
        <div className="grid items-start gap-5 lg:grid-cols-3">
          <div className="space-y-5 lg:col-span-2">
            {/* Natural-language brief */}
            <div className="card-halo relative overflow-hidden p-5">
              <div className="pointer-events-none absolute -right-20 -top-20 size-60 rounded-full bg-violet/20 blur-3xl" />
              <SectionTitle>
                <span className="inline-flex items-center gap-2">
                  <Wand2 className="size-4 text-violet" />
                  Say it in plain words
                </span>
              </SectionTitle>
              <div className="relative">
                <Textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  maxLength={500}
                  rows={3}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runBrief();
                  }}
                  placeholder="e.g. Find tech and healthcare companies within 5 miles that are hiring or expanding"
                  className="resize-none rounded-xl border-border bg-surface-2 pr-28"
                />
                <Button
                  onClick={runBrief}
                  disabled={!brief.trim() || parse.isPending}
                  className="absolute bottom-2 right-2 rounded-lg bg-violet text-white hover:bg-violet/90"
                  size="sm"
                >
                  {parse.isPending ? <Loader2 className="animate-spin" /> : <Wand2 />}Apply
                </Button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {EXAMPLES.map((x) => (
                  <button
                    key={x}
                    onClick={() => setBrief(x)}
                    className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground hover:border-violet/50 hover:text-foreground"
                  >
                    {x}
                  </button>
                ))}
              </div>
              {parse.error && (
                <p className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-300">
                  {errorText(parse.error).detail}
                </p>
              )}
              {patch && patch.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {patch.map((c, i) => (
                    <li
                      key={i}
                      className="rounded-xl border border-violet/30 bg-violet/5 p-3 text-sm"
                    >
                      <div className="font-medium">
                        {c.field.replace(/_/g, " ")}:{" "}
                        <span className="text-muted-foreground line-through">{fmtVal(c.from)}</span>{" "}
                        <ArrowRight className="inline size-3" />{" "}
                        <span className="text-violet">{fmtVal(c.to)}</span>
                      </div>
                      <div className="mt-0.5 text-xs text-muted-foreground">{c.reason}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Structured config */}
            <div className="card-halo space-y-6 p-5">
              <SectionTitle>Search settings</SectionTitle>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <Label className="flex items-center gap-1">
                    How far to look <Explain k="radius" />
                  </Label>
                  <span className="font-mono text-gold">{dist(cfg.radius_km, unit)}</span>
                </div>
                <Slider
                  min={1}
                  max={unit === "mi" ? 30 : 50}
                  step={unit === "mi" ? 0.5 : 1}
                  value={[Number(toUnit(cfg.radius_km, unit).toFixed(1))]}
                  onValueChange={(v) =>
                    set(
                      "radius_km",
                      v[0] == null
                        ? cfg.radius_km
                        : Math.min(50, Math.round(fromUnit(v[0], unit) * 1000) / 1000),
                    )
                  }
                  aria-label="Search distance"
                />
              </div>
              <div className="space-y-2">
                <Label>
                  Industries <span className="text-muted-foreground">(none selected = all)</span>
                </Label>
                <div className="flex flex-wrap gap-2">
                  {ref?.industries.map((i) => (
                    <Chip
                      key={i.code}
                      on={cfg.industries.includes(i.code)}
                      onClick={() => set("industries", toggle(cfg.industries, i.code))}
                    >
                      {i.label}
                    </Chip>
                  ))}
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Company size (employees)</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      placeholder="Min"
                      value={cfg.employee_min ?? ""}
                      onChange={(e) =>
                        set("employee_min", e.target.value ? Number(e.target.value) : null)
                      }
                    />
                    <span className="text-muted-foreground">to</span>
                    <Input
                      type="number"
                      min={0}
                      placeholder="Max"
                      value={cfg.employee_max ?? ""}
                      onChange={(e) =>
                        set("employee_max", e.target.value ? Number(e.target.value) : null)
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Signals from the last</Label>
                  <div className="grid grid-cols-4 gap-1 rounded-xl bg-surface-2 p-1">
                    {WINDOWS.map((w) => (
                      <button
                        key={w}
                        onClick={() => set("signal_window_days", w)}
                        className={cn(
                          "rounded-lg py-1.5 text-xs",
                          cfg.signal_window_days === w
                            ? "bg-surface font-medium shadow"
                            : "text-muted-foreground",
                        )}
                      >
                        {w < 365 ? `${w / 30}mo` : `${w / 365}y`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <Label>What you want to sell them</Label>
                <div className="flex flex-wrap gap-2">
                  {OFFERINGS.map((o) => (
                    <Chip
                      key={o}
                      on={cfg.offerings_focus.includes(o)}
                      onClick={() => set("offerings_focus", toggle(cfg.offerings_focus, o))}
                    >
                      {ref?.offerings.find((x) => x.code === o)?.label ?? OFFERING_LABEL[o]}
                    </Chip>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>Where to look</Label>
                <div className="flex flex-wrap gap-2">
                  {ref?.providers
                    .filter((x) => x.key !== "csv")
                    .map((x) => (
                      <Chip
                        key={x.key}
                        on={cfg.sources.includes(x.key)}
                        disabled={!x.enabled}
                        title={x.reason}
                        onClick={() => set("sources", toggle<ProviderKey>(cfg.sources, x.key))}
                      >
                        {x.label}
                        {!x.enabled && " (off)"}
                      </Chip>
                    ))}
                </div>
                <div className="flex flex-wrap items-center gap-2 pt-1 text-sm">
                  {csv ? (
                    <span className="inline-flex items-center gap-2 rounded-full border border-teal/40 bg-teal/10 px-3 py-1 text-teal">
                      <FileSpreadsheet className="size-4" />
                      {csv.name} · {csv.rows} companies
                      <button
                        type="button"
                        className="text-xs underline-offset-2 hover:underline"
                        onClick={removeCsv}
                      >
                        Remove
                      </button>
                    </span>
                  ) : (
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-dashed border-border px-3 py-1 text-muted-foreground hover:border-gold/50 hover:text-foreground">
                      {csvBusy ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <FileSpreadsheet className="size-4" />
                      )}
                      Add your own list (CSV)
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        className="sr-only"
                        disabled={csvBusy}
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          e.target.value = "";
                          if (f) void uploadCsv(f);
                        }}
                      />
                    </label>
                  )}
                  <span className="text-xs text-muted-foreground">
                    A spreadsheet with a Company column (website optional).
                  </span>
                </div>
              </div>
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <Label>Max companies</Label>
                    <span className="font-mono text-gold">{cfg.max_companies}</span>
                  </div>
                  <Slider
                    min={5}
                    max={200}
                    step={5}
                    value={[cfg.max_companies]}
                    onValueChange={(v) => set("max_companies", v[0] ?? cfg.max_companies)}
                  />
                </div>
                <div className="space-y-2">
                  <Label className="flex items-center gap-1">
                    Research depth <Explain k="depth" />
                  </Label>
                  <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
                    {(["light", "standard"] as const).map((d) => (
                      <button
                        key={d}
                        onClick={() => set("research_depth", d)}
                        className={cn(
                          "rounded-lg py-1.5 text-xs",
                          cfg.research_depth === d
                            ? "bg-surface font-medium shadow"
                            : "text-muted-foreground",
                        )}
                      >
                        {d === "light" ? "Light · faster" : "Standard · deeper"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">
                  Anything to prioritise? <span className="text-muted-foreground">(optional)</span>
                </Label>
                <Textarea
                  id="notes"
                  rows={2}
                  maxLength={500}
                  value={cfg.prioritisation_notes ?? ""}
                  onChange={(e) => set("prioritisation_notes", e.target.value || null)}
                  placeholder="e.g. Prefer companies with visiting clients or frequent training batches"
                  className="resize-none rounded-xl bg-surface-2"
                />
              </div>
            </div>
          </div>

          {/* Estimate + launch */}
          <div className="space-y-5 lg:sticky lg:top-24">
            <div className="card-halo overflow-hidden">
              <div className="border-b border-border bg-background/40 p-4">
                {prop.data && (
                  <HaloRadar
                    center={prop.data.location}
                    radiusKm={cfg.radius_km}
                    unit={unit}
                    labels
                    sweep
                    className="mx-auto max-w-[240px]"
                  />
                )}
              </div>
              <div className="space-y-4 p-5">
                <SectionTitle
                  className="mb-0"
                  right={
                    est.isFetching ? (
                      <Loader2 className="size-4 animate-spin text-muted-foreground" />
                    ) : null
                  }
                >
                  Estimate
                </SectionTitle>
                <div className="grid grid-cols-2 gap-2">
                  <RangeStat
                    icon={<Sparkles className="size-3" />}
                    label="Companies"
                    r={est.data?.candidates}
                    fmt={(n) => String(Math.round(n))}
                  />
                  <RangeStat
                    icon={<CheckCircle2 className="size-3" />}
                    label="Researched"
                    r={est.data?.researched}
                    fmt={(n) => String(Math.round(n))}
                  />
                  <RangeStat
                    icon={<Coins className="size-3" />}
                    label="AI cost"
                    r={est.data?.cost_usd}
                    fmt={usd}
                  />
                  <RangeStat
                    icon={<Clock className="size-3" />}
                    label="Time"
                    r={est.data?.duration_min}
                    fmt={(n) => `${Math.max(1, Math.round(n))}m`}
                  />
                </div>
                {est.error && (
                  <p className="rounded-xl border border-coral/30 bg-coral/10 p-2.5 text-xs text-coral">
                    Couldn't estimate this run: {errorText(est.error).detail}
                  </p>
                )}
                {est.data?.warnings.map((w) => (
                  <p
                    key={w}
                    className="flex gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-300"
                  >
                    <AlertTriangle className="size-4 shrink-0" />
                    {w}
                  </p>
                ))}
                {est.data && !est.data.is_calibrated && (
                  <p className="text-[11px] text-muted-foreground">
                    Rough estimate: it gets sharper after a few runs.
                  </p>
                )}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <Label htmlFor="budget" className="flex items-center gap-1">
                      Spending cap <Explain k="budget" />
                    </Label>
                    <span className="text-xs text-muted-foreground">
                      The agent pauses if it hits this
                    </span>
                  </div>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                      $
                    </span>
                    <Input
                      id="budget"
                      type="number"
                      min={0.5}
                      max={500}
                      step={0.5}
                      value={cfg.budget_usd}
                      onChange={(e) =>
                        set(
                          "budget_usd",
                          Math.min(500, Math.max(0.5, Number(e.target.value) || 0.5)),
                        )
                      }
                      className="pl-7 font-mono"
                    />
                  </div>
                </div>
                <Button
                  variant="signature"
                  className="h-12 w-full rounded-xl text-base"
                  onClick={launch}
                  disabled={start.isPending || !cfg.sources.length}
                >
                  {start.isPending ? <Loader2 className="animate-spin" /> : <Rocket />}Launch the
                  agent
                </Button>
                {!cfg.sources.length && (
                  <p className="text-center text-xs text-coral">Pick at least one place to look.</p>
                )}
              </div>
            </div>

            <div className="card-halo p-5">
              <SectionTitle>Recent runs</SectionTitle>
              {!runs.data?.length ? (
                <p className="text-sm text-muted-foreground">No runs yet for this hotel.</p>
              ) : (
                <ul className="space-y-1">
                  {runs.data.slice(0, 6).map((r) => (
                    <li key={r.id}>
                      <Link
                        to="/p/$propertyId/agent/$jobId"
                        params={{ propertyId, jobId: r.id }}
                        className="-mx-2 flex items-center gap-3 rounded-xl px-2 py-2 text-sm hover:bg-surface-2"
                      >
                        {r.status === "failed" ? (
                          <XCircle className="size-4 text-coral" />
                        ) : (
                          <RunDot status={r.status} />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="font-mono text-xs">
                            {r.counts.companies} companies · {r.counts.scored} scored
                          </div>
                          <div className="text-[11px] text-muted-foreground">
                            {ago(r.created_at)} · {duration(r.started_at, r.finished_at)} ·{" "}
                            {usd(r.spent_usd)}
                          </div>
                        </div>
                        <RunStatusBadge status={r.status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RunDot({ status }: { status: JobStatus }) {
  return isJobActive(status) ? (
    <AgentPulse />
  ) : (
    <CheckCircle2
      className={cn("size-4", status === "completed" ? "text-teal" : "text-muted-foreground")}
    />
  );
}
