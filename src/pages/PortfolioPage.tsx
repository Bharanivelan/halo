import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, Building2, CalendarClock, MapPin, Plus, Sparkles } from "lucide-react";
import {
  AgentPulse,
  EmptyState,
  ErrorState,
  HaloRadar,
  KpiSkeleton,
  KpiTile,
  RadarLegend,
} from "@/components/halo";
import { AddLocationDialog } from "@/components/halo/AddLocationDialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { isJobActive, useAccountsMap, useMe, useProperties, useRuns } from "@/hooks/use-halo";
import { date, firstName, greeting } from "@/lib/halo-format";
import type { JobSummary, PropertySummary } from "@/lib/halo-types";
import { PageHeader } from "./PlaceholderPage";

function LocationCard({
  p,
  run,
  i,
}: {
  p: PropertySummary;
  run: JobSummary | undefined;
  i: number;
}) {
  const reduce = useReducedMotion();
  const { data: points } = useAccountsMap(p.id);
  const hot = points?.filter((x) => x.tier === "A").length;
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * i, duration: 0.4 }}
    >
      <Link
        to="/p/$propertyId"
        params={{ propertyId: p.id }}
        className="card-halo group block overflow-hidden"
      >
        <div className="relative border-b border-border bg-background/40 p-4">
          <HaloRadar
            center={p.location}
            radiusKm={p.radius_km}
            points={points}
            labels={false}
            sweep={!!run}
            className="mx-auto max-w-[220px]"
          />
          {run && (
            <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full border border-violet/40 bg-violet/15 px-2.5 py-1 text-[11px] font-medium text-violet backdrop-blur">
              <AgentPulse />
              Agent {Math.round(run.progress * 100)}%
            </span>
          )}
          <ArrowUpRight className="absolute right-3 top-3 size-4 text-muted-foreground transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-gold" />
        </div>
        <div className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate text-lg font-bold">{p.name}</h3>
              <p className="mt-0.5 flex items-center gap-1 truncate text-sm text-muted-foreground">
                <MapPin className="size-3.5 shrink-0" />
                {[p.locality, p.city].filter(Boolean).join(", ") || "Location pinned"}
              </p>
            </div>
            {p.lifecycle === "pre_opening" && (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-teal/40 bg-teal/10 px-2 py-0.5 text-[11px] text-teal">
                <CalendarClock className="size-3" />
                {p.opening_date ? `Opens ${date(p.opening_date)}` : "Pre-opening"}
              </span>
            )}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            {[
              { k: "Prospects", v: p.account_count },
              { k: "Hot", v: hot, gold: true },
              { k: "Radius", v: `${p.radius_km} km` },
            ].map((s) => (
              <div key={s.k} className="rounded-xl bg-surface-2 py-2">
                <div
                  className={`font-mono text-lg font-semibold tabular ${s.gold ? "text-gold" : ""}`}
                >
                  {s.v ?? "—"}
                </div>
                <div className="text-[11px] text-muted-foreground">{s.k}</div>
              </div>
            ))}
          </div>
        </div>
      </Link>
    </motion.div>
  );
}

export function PortfolioPage() {
  const [adding, setAdding] = useState(false);
  const { data: me } = useMe();
  const props = useProperties();
  const { data: runs = [] } = useRuns();
  const list = props.data ?? [];
  const activeRuns = runs.filter((r) => isJobActive(r.status));
  const total = list.reduce((s, p) => s + p.account_count, 0);
  const cities = new Set(list.map((p) => p.city).filter(Boolean)).size;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title={me ? `${greeting()}, ${firstName(me.user.full_name)}` : "Portfolio"}
        sub={
          me
            ? `${me.workspace.name} · every location and the companies inside its halo`
            : "Every location and the prospects inside its halo."
        }
        right={
          <Button variant="signature" className="rounded-xl" onClick={() => setAdding(true)}>
            <Plus />
            Pin a location
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {props.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <KpiSkeleton key={i} />)
        ) : (
          <>
            <KpiTile
              label="Locations"
              value={list.length}
              icon={<Building2 className="size-4" />}
              sub={cities ? `${cities} ${cities === 1 ? "city" : "cities"}` : undefined}
            />
            <KpiTile label="Prospects found" value={total} accent sub="Across all halos" />
            <KpiTile
              label="Agent runs"
              value={runs.length}
              sub={
                activeRuns.length ? (
                  <span className="inline-flex items-center gap-1.5 text-violet">
                    <AgentPulse />
                    {activeRuns.length} running now
                  </span>
                ) : (
                  "None running"
                )
              }
              icon={<Sparkles className="size-4" />}
            />
            <KpiTile
              label="Largest halo"
              value={list.length ? Math.max(...list.map((p) => p.account_count)) : null}
              sub={
                list.length
                  ? [...list].sort((a, b) => b.account_count - a.account_count)[0]?.name
                  : undefined
              }
            />
          </>
        )}
      </div>

      <div className="mt-10 flex items-end justify-between gap-3">
        <h2 className="text-xl font-bold">Your locations</h2>
        <RadarLegend />
      </div>

      {props.error ? (
        <ErrorState className="mt-4" error={props.error} onRetry={() => void props.refetch()} />
      ) : (
        <div className="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {props.isLoading &&
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="card-halo p-5">
                <Skeleton className="mx-auto aspect-square w-48 rounded-full" />
                <Skeleton className="mt-5 h-5 w-2/3" />
                <Skeleton className="mt-2 h-3 w-1/2" />
              </div>
            ))}
          {list.map((p, i) => (
            <LocationCard
              key={p.id}
              p={p}
              i={i}
              run={activeRuns.find((r) => r.property_id === p.id)}
            />
          ))}
          {props.isSuccess && (
            <button
              onClick={() => setAdding(true)}
              className="group flex min-h-[320px] flex-col items-center justify-center rounded-[var(--radius)] border border-dashed border-border text-muted-foreground transition-colors hover:border-gold/50 hover:text-foreground"
            >
              {list.length === 0 ? (
                <EmptyState
                  title="Pin your first location"
                  text="Add a hotel or restaurant. Halo will map every company inside its catchment."
                />
              ) : (
                <>
                  <span className="grid size-12 place-items-center rounded-full border border-border transition-colors group-hover:border-gold/50 group-hover:text-gold">
                    <Plus />
                  </span>
                  <span className="mt-3 text-sm font-medium">Pin another location</span>
                </>
              )}
            </button>
          )}
        </div>
      )}
      <AddLocationDialog open={adding} onOpenChange={setAdding} />
    </div>
  );
}
