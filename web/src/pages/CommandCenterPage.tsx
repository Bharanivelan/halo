import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  Bot,
  CalendarClock,
  Flame,
  MapPin,
  Radar,
  Sparkles,
  Wallet,
  Zap,
} from "lucide-react";
import {
  AgentPulse,
  CardSkeleton,
  EmptyState,
  ErrorState,
  Explain,
  HaloRadar,
  KpiSkeleton,
  KpiTile,
  RadarLegend,
  ScoreRing,
  SectionTitle,
  SignalChip,
  TierBadge,
  TIER_COLOR,
} from "@/components/halo";
import { Button } from "@/components/ui/button";
import { useAccountsMap, useOverview, useReference } from "@/hooks/use-halo";
import { ago, ageDays, date, dist, money, usd } from "@/lib/halo-format";
import type { AccountStatus, Tier } from "@/lib/halo-types";

const FUNNEL: AccountStatus[] = [
  "discovered",
  "qualified",
  "contact_identified",
  "outreach_prepared",
  "outreach_sent",
  "engaged",
];

export function CommandCenterPage() {
  const { propertyId } = useParams({ strict: false }) as { propertyId: string };
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const ov = useOverview(propertyId);
  const { data: points } = useAccountsMap(propertyId);
  const { data: ref } = useReference();

  if (ov.error)
    return (
      <div className="mx-auto max-w-7xl">
        <ErrorState error={ov.error} onRetry={() => void ov.refetch()} />
      </div>
    );
  const o = ov.data;
  const p = o?.property;
  const run = o?.running_jobs[0];
  const paused = run?.status === "paused_budget";
  const tiers = o?.tier_counts ?? { A: 0, B: 0, C: 0 };
  const scored = tiers.A + tiers.B + tiers.C;
  const funnelMax = Math.max(1, ...FUNNEL.map((s) => o?.funnel[s] ?? 0));
  const statusLabel = (s: string) =>
    ref?.account_statuses.find((x) => x.code === s)?.label ?? s.replace(/_/g, " ");
  const openPipeline = o
    ? o.opportunities.interested + o.opportunities.meeting_scheduled + o.opportunities.negotiation
    : null;
  const fade = (d: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 10 },
          animate: { opacity: 1, y: 0 },
          transition: { delay: d, duration: 0.45 },
        };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="size-4 text-gold" />
            {p ? [p.locality, p.city].filter(Boolean).join(", ") : "Loading hotel"}
            {p?.lifecycle === "pre_opening" && (
              <span className="inline-flex items-center gap-1 rounded-full border border-teal/40 bg-teal/10 px-2 py-0.5 text-[11px] text-teal">
                <CalendarClock className="size-3" />
                {p.opening_date ? `Opens ${date(p.opening_date)}` : "Opening soon"}
              </span>
            )}
          </div>
          <h1 className="mt-1 text-[32px] font-bold leading-tight">
            {p?.name ?? "Overview"}
          </h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="rounded-xl" asChild>
            <Link to="/p/$propertyId/accounts" params={{ propertyId }} search={{}}>
              View prospects
            </Link>
          </Button>
          <Button variant="signature" className="rounded-xl" asChild>
            <Link to="/p/$propertyId/agent/new" params={{ propertyId }}>
              <Sparkles />
              Run agent
            </Link>
          </Button>
        </div>
      </div>

      {/* Live run banner */}
      {run && (
        <Link
          to="/p/$propertyId/agent/$jobId"
          params={{ propertyId, jobId: run.id }}
          className="relative block overflow-hidden rounded-[var(--radius)] border border-violet/40 bg-violet/10 p-4 transition-colors hover:border-violet/70"
        >
          <div className="shimmer absolute inset-0 opacity-40" />
          <div className="relative flex flex-wrap items-center gap-4">
            <span className="grid size-10 place-items-center rounded-full bg-violet/20 text-violet">
              <Bot className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 font-semibold">
                {paused ? (
                  "The agent paused at its spending cap. Open the run to continue"
                ) : (
                  <>
                    <AgentPulse />
                    The agent is working on this hotel
                  </>
                )}
              </div>
              <div className="mt-0.5 font-mono text-xs text-muted-foreground">
                {run.counts.found} found · {run.counts.researched} researched · {run.counts.scored}{" "}
                scored · {usd(run.spent_usd)} of {usd(run.budget_usd)}
              </div>
            </div>
            <div className="w-40">
              <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-full rounded-full bg-violet transition-[width] duration-700"
                  style={{ width: `${Math.round(run.progress * 100)}%` }}
                />
              </div>
            </div>
            <span className="flex items-center gap-1 text-sm font-medium text-violet">
              Watch live
              <ArrowRight className="size-4" />
            </span>
          </div>
        </Link>
      )}

      {/* Hero: radar + KPIs */}
      <div className="grid gap-5 lg:grid-cols-5">
        <motion.div {...fade(0)} className="card-halo relative overflow-hidden p-5 lg:col-span-3">
          <SectionTitle right={<RadarLegend />}>
            <span className="inline-flex items-center gap-2">
              <Radar className="size-4 text-gold" />
              Businesses around your hotel
              <Explain k="radius" />
            </span>
          </SectionTitle>
          {p ? (
            <div className="mx-auto max-w-[520px]">
              <HaloRadar
                center={p.location}
                radiusKm={p.radius_km}
                unit={p.distance_unit}
                points={points}
                sweep
                onSelect={(pt) =>
                  void navigate({
                    to: "/p/$propertyId/accounts/$accountId",
                    params: { propertyId, accountId: pt.id },
                  })
                }
              />
            </div>
          ) : (
            <div className="mx-auto aspect-square max-w-[520px] animate-pulse rounded-full bg-surface-2" />
          )}
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Your hotel is in the centre. Each dot is a business at its real direction and distance; gold dots are the best matches. Click one to see what Halo learned.
          </p>
        </motion.div>

        <div className="grid content-start gap-4 sm:grid-cols-2 lg:col-span-2 lg:grid-cols-2">
          {!o ? (
            Array.from({ length: 4 }).map((_, i) => <KpiSkeleton key={i} />)
          ) : (
            <>
              <KpiTile
                label="Prospects"
                value={o.account_count}
                icon={<Explain k="prospect" />}
                sub={`within ${dist(o.property.radius_km, o.property.distance_unit)}`}
              />
              <KpiTile
                label="Hot prospects"
                value={tiers.A}
                accent
                icon={
                  <span className="flex items-center gap-1">
                    <Flame className="size-4 text-gold" />
                    <Explain k="tier" />
                  </span>
                }
                sub="Strong match with recent news: call this week"
              />
              <KpiTile
                label="Open pipeline"
                value={o.opportunities.open_value}
                format={(n) => money(n, o.opportunities.currency)}
                icon={
                  <span className="flex items-center gap-1">
                    <Wallet className="size-4" />
                    <Explain k="pipeline" />
                  </span>
                }
                sub={`${openPipeline} open · ${o.opportunities.won} won`}
              />
              <KpiTile
                label="AI spend · 30 days, all hotels"
                value={o.usage_30d.cost_usd}
                format={(n) => usd(n)}
                icon={
                  <span className="flex items-center gap-1">
                    <Zap className="size-4" />
                    <Explain k="budget" />
                  </span>
                }
                sub={`${o.usage_30d.llm_calls} AI calls`}
              />
            </>
          )}
          {o && (
            <motion.div {...fade(0.15)} className="card-halo p-5 sm:col-span-2">
              <SectionTitle>
                <span className="inline-flex items-center gap-2">
                  Hot, warm and cool
                  <Explain k="tier" />
                </span>
              </SectionTitle>
              <div className="flex h-3 overflow-hidden rounded-full bg-surface-2">
                {(["A", "B", "C"] as Tier[]).map(
                  (t) =>
                    tiers[t] > 0 && (
                      <div
                        key={t}
                        style={{
                          width: `${(tiers[t] / Math.max(1, scored)) * 100}%`,
                          background: TIER_COLOR[t],
                        }}
                        className="h-full first:rounded-l-full last:rounded-r-full"
                      />
                    ),
                )}
              </div>
              <div className="mt-3 flex justify-between text-sm">
                {(["A", "B", "C"] as Tier[]).map((t) => (
                  <Link
                    key={t}
                    to="/p/$propertyId/accounts"
                    params={{ propertyId }}
                    search={{ tier: t }}
                    className="flex items-center gap-2 hover:text-gold"
                  >
                    <TierBadge tier={t} />
                    <span className="font-mono tabular">{tiers[t]}</span>
                  </Link>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {o && o.account_count === 0 && !run && (
        <div className="card-halo">
          <EmptyState
            title="No businesses yet"
            text="Run the AI agent: it finds businesses near your hotel, reads up on each one and tells you who to call first. It takes a few minutes."
            action={
              <Button variant="signature" className="rounded-xl" asChild>
                <Link to="/p/$propertyId/agent/new" params={{ propertyId }}>
                  <Sparkles />
                  Run the agent
                </Link>
              </Button>
            }
          />
        </div>
      )}

      {o && o.account_count > 0 && (
        <div className="grid gap-5 lg:grid-cols-3">
          {/* Attention */}
          <motion.div {...fade(0.1)} className="card-halo p-5 lg:col-span-2">
            <SectionTitle
              right={
                <Link
                  to="/p/$propertyId/accounts"
                  params={{ propertyId }}
                  search={{}}
                  className="text-xs text-gold hover:underline"
                >
                  All prospects
                </Link>
              }
            >
              <span className="inline-flex items-center gap-2">
                Call these first
                <Explain k="score" />
              </span>
            </SectionTitle>
            {o.attention.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Nothing needs action right now.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {o.attention.map((a) => (
                  <li key={a.id}>
                    <Link
                      to="/p/$propertyId/accounts/$accountId"
                      params={{ propertyId, accountId: a.id }}
                      className="-mx-2 flex items-center gap-4 rounded-xl px-2 py-3 transition-colors hover:bg-surface-2"
                    >
                      <ScoreRing value={a.priority} kind="priority" size={44} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-semibold">{a.company.name}</span>
                          <TierBadge tier={a.tier} />
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {[
                            a.company.industry_label,
                            a.distance_km != null ? dist(a.distance_km, p?.distance_unit) : null,
                            statusLabel(a.status),
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </div>
                      </div>
                      {a.top_signal && (
                        <SignalChip
                          label={a.top_signal.type_label}
                          age={ageDays(a.top_signal.age_days)}
                          className="hidden sm:inline-flex"
                        />
                      )}
                      <ArrowRight className="size-4 text-muted-foreground" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </motion.div>

          {/* Signals */}
          <motion.div {...fade(0.2)} className="card-halo p-5">
            <SectionTitle>
              <span className="inline-flex items-center gap-2">
                Recent buying signals
                <Explain k="signal" />
              </span>
            </SectionTitle>
            {o.recent_signals.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No buying signals found yet.
              </p>
            ) : (
              <ol className="relative space-y-4 border-l border-border pl-5">
                {o.recent_signals.slice(0, 6).map((s) => (
                  <li key={s.id} className="relative">
                    <span className="absolute -left-[25px] top-1.5 size-2.5 rounded-full bg-coral shadow-[0_0_8px_var(--coral)]" />
                    <Link
                      to="/p/$propertyId/accounts/$accountId"
                      params={{ propertyId, accountId: s.account_id }}
                      className="group block"
                    >
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium text-coral">{s.type_label}</span> ·{" "}
                        {s.company_name} ·{" "}
                        {s.published_at ? ago(s.published_at) : ageDays(s.age_days)}
                      </div>
                      <div className="mt-0.5 line-clamp-2 text-sm group-hover:text-gold">
                        {s.title}
                      </div>
                    </Link>
                  </li>
                ))}
              </ol>
            )}
          </motion.div>

          {/* Funnel */}
          <motion.div {...fade(0.25)} className="card-halo p-5 lg:col-span-3">
            <SectionTitle>Outreach funnel</SectionTitle>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {FUNNEL.map((s, i) => {
                const v = o.funnel[s] ?? 0;
                return (
                  <div key={s} className="rounded-xl bg-surface-2 p-3">
                    <div className="font-mono text-2xl font-semibold tabular">{v}</div>
                    <div className="mt-0.5 truncate text-xs text-muted-foreground">
                      {statusLabel(s)}
                    </div>
                    <div className="mt-2 h-1 overflow-hidden rounded-full bg-background">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${(v / funnelMax) * 100}%`,
                          background: `color-mix(in oklab, var(--gold) ${100 - i * 12}%, var(--violet))`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </div>
      )}
      {!o && (
        <div className="grid gap-5 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CardSkeleton lines={5} />
          </div>
          <CardSkeleton lines={5} />
        </div>
      )}
    </div>
  );
}
