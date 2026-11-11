import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { ArrowRight, Download, List, Loader2, Radar, Search, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import {
  EmptyState,
  ErrorState,
  HaloRadar,
  Meter,
  MockBadge,
  RadarLegend,
  ScoreRing,
  SignalChip,
  TableSkeleton,
  TierBadge,
  errorText,
} from "@/components/halo";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  isJobActive,
  useAccounts,
  useAccountsMap,
  useBulk,
  useProperty,
  useReference,
  useRuns,
} from "@/hooks/use-halo";
import { halo, type AccountFilters } from "@/lib/halo-api";
import { ageDays, km } from "@/lib/halo-format";
import type { AccountListItem, MapPoint } from "@/lib/halo-types";
import { cn } from "@/lib/utils";
import type { AccountsSearch } from "@/routes/_shell.p.$propertyId.accounts.index";

const SORTS = [
  { v: "-priority", l: "Priority" },
  { v: "-fit", l: "Best fit" },
  { v: "-intent", l: "Strongest intent" },
  { v: "distance_km", l: "Nearest" },
  { v: "name", l: "Name" },
  { v: "-updated_at", l: "Recently updated" },
];
const ALL = "__all";

function useDebounced<T>(v: T, ms = 300) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const t = setTimeout(() => setD(v), ms);
    return () => clearTimeout(t);
  }, [v, ms]);
  return d;
}

function ProspectRow({
  a,
  propertyId,
  selected,
  onSelect,
  statusLabel,
}: {
  a: AccountListItem;
  propertyId: string;
  selected: boolean;
  onSelect: (v: boolean) => void;
  statusLabel: (s: string) => string;
}) {
  return (
    <tr
      className={cn(
        "group border-b border-border transition-colors last:border-0 hover:bg-surface-2/60",
        selected && "bg-gold/5",
      )}
    >
      <td className="w-10 py-3 pl-4">
        <Checkbox
          checked={selected}
          onCheckedChange={(v) => onSelect(!!v)}
          aria-label={`Select ${a.company.name}`}
        />
      </td>
      <td className="py-3 pr-3">
        <ScoreRing value={a.priority} kind="priority" size={42} />
      </td>
      <td className="min-w-[220px] py-3 pr-3">
        <Link
          to="/p/$propertyId/accounts/$accountId"
          params={{ propertyId, accountId: a.id }}
          className="block"
        >
          <div className="flex items-center gap-2">
            <span className="truncate font-semibold group-hover:text-gold">{a.company.name}</span>
            <MockBadge origin={a.company.data_origin} />
            {a.research_status === "researching" && (
              <Loader2 className="size-3.5 animate-spin text-violet" />
            )}
          </div>
          <div className="truncate text-xs text-muted-foreground">
            {[
              a.company.industry_label,
              a.company.employee_range && `${a.company.employee_range} staff`,
              a.company.locality,
            ]
              .filter(Boolean)
              .join(" · ") ||
              a.company.domain ||
              "—"}
          </div>
        </Link>
      </td>
      <td className="py-3 pr-3">
        <TierBadge tier={a.tier} />
      </td>
      <td className="hidden w-36 py-3 pr-3 lg:table-cell">
        <div className="space-y-1.5">
          {(
            [
              ["Fit", a.fit, "var(--gold)"],
              ["Intent", a.intent, "var(--coral)"],
              ["Conf.", a.confidence, "var(--teal)"],
            ] as const
          ).map(([l, v, c]) => (
            <div key={l} className="flex items-center gap-2 text-[10px] text-muted-foreground">
              <span className="w-8">{l}</span>
              <Meter value={v} color={c} />
              <span className="w-5 text-right font-mono">{v ?? "—"}</span>
            </div>
          ))}
        </div>
      </td>
      <td className="hidden py-3 pr-3 md:table-cell">
        {a.top_signal ? (
          <SignalChip label={a.top_signal.type_label} age={ageDays(a.top_signal.age_days)} />
        ) : (
          <span className="text-xs text-muted-foreground">No signal</span>
        )}
      </td>
      <td className="hidden py-3 pr-3 font-mono text-sm tabular sm:table-cell">
        {km(a.distance_km)}
      </td>
      <td className="hidden py-3 pr-3 xl:table-cell">
        <span className="rounded-full bg-surface-2 px-2.5 py-1 text-xs">
          {statusLabel(a.status)}
        </span>
      </td>
      <td className="hidden py-3 pr-4 text-sm text-muted-foreground xl:table-cell">
        {a.owner?.name ?? "Unassigned"}
      </td>
      <td className="py-3 pr-4">
        <Link
          to="/p/$propertyId/accounts/$accountId"
          params={{ propertyId, accountId: a.id }}
          aria-label="Open dossier"
        >
          <ArrowRight className="size-4 text-muted-foreground group-hover:text-gold" />
        </Link>
      </td>
    </tr>
  );
}

export function AccountsPage() {
  const { propertyId } = useParams({ strict: false }) as { propertyId: string };
  const search = useSearch({ strict: false }) as AccountsSearch;
  const navigate = useNavigate();
  const { data: ref } = useReference();
  const prop = useProperty(propertyId);
  const { data: runs } = useRuns(propertyId);
  const live = !!runs?.some((r) => isJobActive(r.status));

  const [q, setQ] = useState(search.q ?? "");
  const [tier, setTier] = useState<string>(search.tier ?? ALL);
  const [status, setStatus] = useState<string>(ALL);
  const [sort, setSort] = useState("-priority");
  const [hasSignal, setHasSignal] = useState(false);
  const [limit, setLimit] = useState(50);
  const [view, setView] = useState<"list" | "radar">("list");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [focus, setFocus] = useState<MapPoint | null>(null);
  const [exporting, setExporting] = useState(false);
  const dq = useDebounced(q);

  useEffect(() => {
    setQ(search.q ?? "");
  }, [search.q]);
  useEffect(() => {
    setTier(search.tier ?? ALL);
  }, [search.tier]);

  const filters: AccountFilters = useMemo(() => {
    const f: AccountFilters = { sort, limit };
    if (dq.trim()) f.q = dq.trim();
    if (tier !== ALL) f.tier = tier;
    if (status !== ALL) f.status = status;
    if (hasSignal) f.has_signal = true;
    if (search.job) f.job_id = search.job;
    return f;
  }, [dq, tier, status, sort, hasSignal, limit, search.job]);

  const acc = useAccounts(propertyId, filters, { live });
  const map = useAccountsMap(view === "radar" ? propertyId : undefined);
  const bulk = useBulk(propertyId);
  const items = acc.data?.items ?? [];
  const statusLabel = (s: string) =>
    ref?.account_statuses.find((x) => x.code === s)?.label ?? s.replace(/_/g, " ");
  const allSel = items.length > 0 && items.every((a) => sel.has(a.id));
  const unfiltered = !dq && tier === ALL && status === ALL && !hasSignal && !search.job;

  const doBulk = (b: Omit<Parameters<typeof halo.bulk>[1], "account_ids">) =>
    bulk.mutate(
      { ...b, account_ids: [...sel] },
      {
        onSuccess: (r) => {
          toast.success(`Updated ${r.updated} prospect${r.updated === 1 ? "" : "s"}`);
          setSel(new Set());
        },
        onError: (e) => {
          const t = errorText(e);
          toast.error(t.title, { description: t.detail });
        },
      },
    );

  const exportCsv = async () => {
    setExporting(true);
    const { limit: _l, ...f } = filters;
    try {
      await halo.downloadAccountsCsv(
        propertyId,
        f,
        `halo-${(prop.data?.name ?? "prospects").toLowerCase().replace(/\W+/g, "-")}.csv`,
      );
    } catch (e) {
      const t = errorText(e);
      toast.error(t.title, { description: t.detail });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">{prop.data?.name}</p>
          <h1 className="mt-1 flex items-center gap-3 text-[32px] font-bold leading-tight">
            Prospects{" "}
            {acc.data && (
              <span className="rounded-full bg-surface-2 px-3 py-0.5 font-mono text-lg text-muted-foreground">
                {acc.data.total}
              </span>
            )}
          </h1>
        </div>
        <div className="flex gap-2">
          <div className="grid grid-cols-2 gap-1 rounded-xl border border-border bg-surface p-1">
            <button
              onClick={() => setView("list")}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm",
                view === "list" ? "bg-surface-2 text-foreground" : "text-muted-foreground",
              )}
            >
              <List className="size-4" />
              List
            </button>
            <button
              onClick={() => setView("radar")}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm",
                view === "radar" ? "bg-surface-2 text-foreground" : "text-muted-foreground",
              )}
            >
              <Radar className="size-4" />
              Radar
            </button>
          </div>
          <Button variant="outline" className="rounded-xl" onClick={exportCsv} disabled={exporting}>
            {exporting ? <Loader2 className="animate-spin" /> : <Download />}Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="card-halo mb-4 flex flex-wrap items-center gap-3 p-3">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search companies"
            className="h-9 rounded-xl border-border bg-surface-2 pl-9"
          />
        </div>
        <div className="flex gap-1 rounded-xl bg-surface-2 p-1">
          {[ALL, "A", "B", "C"].map((t) => (
            <button
              key={t}
              onClick={() => setTier(t)}
              className={cn(
                "rounded-lg px-3 py-1 text-xs",
                tier === t
                  ? "bg-surface font-medium text-foreground shadow"
                  : "text-muted-foreground",
              )}
            >
              {t === ALL ? "All" : t === "A" ? "Hot" : t === "B" ? "Warm" : "Cool"}
            </button>
          ))}
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="h-9 w-44 rounded-xl bg-surface-2">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Any status</SelectItem>
            {ref?.account_statuses.map((s) => (
              <SelectItem key={s.code} value={s.code}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="h-9 w-48 rounded-xl bg-surface-2">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORTS.map((s) => (
              <SelectItem key={s.v} value={s.v}>
                Sort: {s.l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <Switch checked={hasSignal} onCheckedChange={setHasSignal} />
          Has signal
        </label>
        {search.job && (
          <button
            onClick={() =>
              void navigate({ to: "/p/$propertyId/accounts", params: { propertyId }, search: {} })
            }
            className="inline-flex items-center gap-1.5 rounded-full border border-violet/40 bg-violet/10 px-3 py-1 text-xs text-violet"
          >
            <Sparkles className="size-3" />
            From one agent run
            <X className="size-3" />
          </button>
        )}
        {live && (
          <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-violet">
            <Loader2 className="size-3 animate-spin" />
            Agent running · refreshing live
          </span>
        )}
      </div>

      {/* Bulk bar */}
      {sel.size > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-gold/40 bg-gold/10 p-3 text-sm">
          <span className="font-medium">{sel.size} selected</span>
          <Select value="" onValueChange={(v) => doBulk({ action: "set_status", status: v })}>
            <SelectTrigger className="h-8 w-44 rounded-lg bg-surface">
              <SelectValue placeholder="Move to…" />
            </SelectTrigger>
            <SelectContent>
              {ref?.account_statuses
                .filter((s) => s.code !== "dismissed")
                .map((s) => (
                  <SelectItem key={s.code} value={s.code}>
                    {s.label}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          <Select
            value=""
            onValueChange={(v) => doBulk({ action: "dismiss", dismissed_reason: v })}
          >
            <SelectTrigger className="h-8 w-44 rounded-lg bg-surface">
              <SelectValue placeholder="Dismiss because…" />
            </SelectTrigger>
            <SelectContent>
              {ref?.dismiss_reasons.map((s) => (
                <SelectItem key={s.code} value={s.code}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {bulk.isPending && <Loader2 className="size-4 animate-spin" />}
          <button
            className="ml-auto text-muted-foreground hover:text-foreground"
            onClick={() => setSel(new Set())}
          >
            Clear
          </button>
        </div>
      )}

      {acc.error ? (
        <ErrorState error={acc.error} onRetry={() => void acc.refetch()} />
      ) : view === "radar" ? (
        <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
          <div className="card-halo p-5">
            {prop.data && (
              <HaloRadar
                center={prop.data.location}
                radiusKm={prop.data.radius_km}
                points={map.data}
                selectedId={focus?.id}
                onSelect={setFocus}
                className="mx-auto max-w-[640px]"
              />
            )}
            <RadarLegend className="mt-3 justify-center" />
          </div>
          <div className="card-halo p-5">
            {focus ? (
              <div>
                <TierBadge tier={focus.tier} />
                <h3 className="mt-3 text-xl font-bold">{focus.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{statusLabel(focus.status)}</p>
                <Button variant="signature" className="mt-5 w-full rounded-xl" asChild>
                  <Link
                    to="/p/$propertyId/accounts/$accountId"
                    params={{ propertyId, accountId: focus.id }}
                  >
                    Open dossier
                    <ArrowRight />
                  </Link>
                </Button>
              </div>
            ) : (
              <EmptyState title="Pick a dot" text="Click any company on the radar to preview it." />
            )}
          </div>
        </div>
      ) : acc.isLoading ? (
        <TableSkeleton rows={8} />
      ) : items.length === 0 ? (
        <div className="card-halo">
          {unfiltered ? (
            <EmptyState
              title="No prospects yet"
              text="Run the agent to find and score companies around this location."
              action={
                <Button variant="signature" className="rounded-xl" asChild>
                  <Link to="/p/$propertyId/agent/new" params={{ propertyId }}>
                    <Sparkles />
                    Run agent
                  </Link>
                </Button>
              }
            />
          ) : (
            <EmptyState title="No matches" text="Try loosening the filters." />
          )}
        </div>
      ) : (
        <div className="card-halo overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-border text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="w-10 py-3 pl-4">
                  <Checkbox
                    checked={allSel}
                    onCheckedChange={(v) => setSel(v ? new Set(items.map((a) => a.id)) : new Set())}
                    aria-label="Select all"
                  />
                </th>
                <th className="py-3 pr-3 font-medium">Priority</th>
                <th className="py-3 pr-3 font-medium">Company</th>
                <th className="py-3 pr-3 font-medium">Tier</th>
                <th className="hidden py-3 pr-3 font-medium lg:table-cell">Scores</th>
                <th className="hidden py-3 pr-3 font-medium md:table-cell">Top signal</th>
                <th className="hidden py-3 pr-3 font-medium sm:table-cell">Distance</th>
                <th className="hidden py-3 pr-3 font-medium xl:table-cell">Status</th>
                <th className="hidden py-3 pr-4 font-medium xl:table-cell">Owner</th>
                <th className="py-3 pr-4" />
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <ProspectRow
                  key={a.id}
                  a={a}
                  propertyId={propertyId}
                  selected={sel.has(a.id)}
                  statusLabel={statusLabel}
                  onSelect={(v) =>
                    setSel((s) => {
                      const n = new Set(s);
                      if (v) n.add(a.id);
                      else n.delete(a.id);
                      return n;
                    })
                  }
                />
              ))}
            </tbody>
          </table>
          {acc.data && acc.data.total > items.length && limit < 200 && (
            <div className="border-t border-border p-3 text-center">
              <Button
                variant="ghost"
                onClick={() => setLimit((l) => Math.min(200, l + 50))}
                disabled={acc.isFetching}
              >
                {acc.isFetching && <Loader2 className="animate-spin" />}Show more (
                {acc.data.total - items.length} left)
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
