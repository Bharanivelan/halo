import { useMemo, useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Globe,
  Loader2,
  MapPin,
  RefreshCw,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Undo2,
  Users,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import {
  CardSkeleton,
  ErrorState,
  Meter,
  MockBadge,
  ScoreRing,
  SectionTitle,
  SignalChip,
  TierBadge,
  errorText,
} from "@/components/halo";
import { RateLeadCard } from "@/components/halo/RateLead";
import { ActivityPanel } from "@/components/dossier/ActivityPanel";
import { ClaimCard, SourceLink } from "@/components/dossier/Evidence";
import { PeoplePanel } from "@/components/dossier/PeoplePanel";
import { PitchPanel } from "@/components/dossier/PitchPanel";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useAccount,
  useMembers,
  useReference,
  useRateSignal,
  useReResearch,
  useUpdateAccount,
  useProjectUnits,
} from "@/hooks/use-halo";
import { ago, ageDays, date, dist, OFFERING_LABEL, pct } from "@/lib/halo-format";
import type { AccountDetail, Offering } from "@/lib/halo-types";

const UNASSIGNED = "__none";
type Tab = "overview" | "signals" | "people" | "pitch" | "activity";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 truncate text-sm">{children ?? "—"}</dd>
    </div>
  );
}

function WhyScore({ a }: { a: AccountDetail }) {
  const s = a.score;
  if (!s) return <p className="text-sm text-muted-foreground">Not scored yet.</p>;
  return (
    <div className="space-y-6">
      <div>
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-medium">Fit</span>
          <span className="font-mono text-gold">{s.fit}</span>
        </div>
        <ul className="space-y-3">
          {s.breakdown.fit.factors.map((f) => (
            <li key={f.key}>
              <div className="flex justify-between text-xs">
                <span>{f.label}</span>
                <span className="font-mono text-muted-foreground">
                  {f.points.toFixed(0)} / {f.weight}
                </span>
              </div>
              <Meter value={(f.points / Math.max(1, f.weight)) * 100} className="mt-1" />
              <p className="mt-1 text-xs text-muted-foreground">{f.explanation}</p>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-medium">Intent</span>
          <span className="font-mono text-coral">{s.intent}</span>
        </div>
        {s.breakdown.intent.signals.length === 0 ? (
          <p className="text-xs text-muted-foreground">No recent buying signals.</p>
        ) : (
          <ul className="space-y-1.5">
            {s.breakdown.intent.signals.map((x) => (
              <li key={x.id} className="flex items-center gap-2 text-xs">
                <span className="flex-1 truncate">{x.title}</span>
                <span className="text-muted-foreground">{ageDays(x.age_days)}</span>
                <span className="w-10 text-right font-mono text-coral">
                  +{x.contribution.toFixed(0)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-medium">Confidence</span>
          <span className="font-mono text-teal">{s.confidence}</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          {(["coverage", "diversity", "freshness"] as const).map((k) => (
            <div key={k} className="rounded-lg bg-surface-2 p-2">
              <div className="font-mono">{pct(s.breakdown.confidence.components[k])}</div>
              <div className="capitalize text-muted-foreground">{k}</div>
            </div>
          ))}
        </div>
      </div>
      {s.breakdown.missing.length > 0 && (
        <div className="rounded-xl border border-dashed border-border p-3">
          <p className="text-xs font-medium">What would sharpen this score</p>
          <ul className="mt-1 list-inside list-disc text-xs text-muted-foreground">
            {s.breakdown.missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function AccountDetailPage() {
  const { propertyId, accountId } = useParams({ strict: false }) as {
    propertyId: string;
    accountId: string;
  };
  const { unit } = useProjectUnits(propertyId);
  const reduce = useReducedMotion();
  const acc = useAccount(accountId);
  const { data: ref } = useReference();
  const { data: members } = useMembers();
  const update = useUpdateAccount(accountId);
  const research = useReResearch(accountId);
  const rateSignal = useRateSignal(accountId);
  const [tab, setTab] = useState<Tab>("overview");
  const [preset, setPreset] = useState<{
    role_code?: string;
    offering?: Offering;
    contact_id?: string;
  } | null>(null);
  const [dismissOpen, setDismissOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const a = acc.data;
  const facts = useMemo(() => a?.claims.filter((c) => c.kind !== "unknown") ?? [], [a]);

  if (acc.error) return <ErrorState error={acc.error} onRetry={() => void acc.refetch()} />;
  if (!a)
    return (
      <div className="mx-auto max-w-7xl space-y-5">
        <CardSkeleton lines={3} />
        <CardSkeleton lines={8} />
      </div>
    );

  const onErr = (e: unknown) => {
    const t = errorText(e);
    toast.error(t.title, { description: t.detail });
  };
  const statusLabel = (s: string) =>
    ref?.account_statuses.find((x) => x.code === s)?.label ?? s.replace(/_/g, " ");
  const c = a.company;
  const draft = (p: typeof preset) => {
    setPreset(p);
    setTab("pitch");
  };
  const nextAction = () => {
    switch (a.next_action.kind) {
      case "research":
        research.mutate(undefined, {
          onError: onErr,
          onSuccess: () => toast.success("Research queued"),
        });
        break;
      case "add_contact":
        setTab("people");
        break;
      case "prepare_outreach":
        setTab("pitch");
        break;
      case "follow_up":
      case "create_opportunity":
        setTab("activity");
        break;
      default:
        break;
    }
  };
  const fade = (d: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 10 },
          animate: { opacity: 1, y: 0 },
          transition: { delay: d, duration: 0.4 },
        };

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <Link
        to="/p/$propertyId/accounts"
        params={{ propertyId }}
        search={{}}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        All prospects
      </Link>

      {a.status === "dismissed" && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-2 p-3 text-sm">
          <XCircle className="size-4 text-muted-foreground" />
          Dismissed
          {a.dismissed_reason
            ? `: ${ref?.dismiss_reasons.find((x) => x.code === a.dismissed_reason)?.label ?? a.dismissed_reason}`
            : ""}
          {a.dismissed_note ? ` · ${a.dismissed_note}` : ""}
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto"
            onClick={() => update.mutate({ status: "discovered" }, { onError: onErr })}
          >
            <Undo2 />
            Restore
          </Button>
        </div>
      )}

      {/* Header */}
      <motion.div {...fade(0)} className="card-halo relative overflow-hidden p-6">
        <div
          className="pointer-events-none absolute -right-32 -top-32 size-80 rounded-full opacity-60 blur-3xl"
          style={{
            background:
              a.tier === "A"
                ? "color-mix(in oklab, var(--gold) 25%, transparent)"
                : "color-mix(in oklab, var(--violet) 15%, transparent)",
          }}
        />
        <div className="relative flex flex-wrap items-start gap-6">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <TierBadge tier={a.tier} />
              <MockBadge origin={c.data_origin} />
              {c.research_status === "researching" && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-violet/40 bg-violet/10 px-2.5 py-0.5 text-xs text-violet">
                  <Loader2 className="size-3 animate-spin" />
                  Researching
                </span>
              )}
            </div>
            <h1 className="mt-3 text-4xl font-bold leading-tight">{c.name}</h1>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted-foreground">
              {c.industry_label && (
                <span className="inline-flex items-center gap-1.5">
                  <Building2 className="size-4" />
                  {c.industry_label}
                </span>
              )}
              {c.employee_range && (
                <span className="inline-flex items-center gap-1.5">
                  <Users className="size-4" />
                  {c.employee_range} staff
                </span>
              )}
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="size-4" />
                {dist(a.distance_km, unit)} from {a.property_name}
              </span>
              {(c.website || c.domain) && (
                <a
                  href={c.website ?? `https://${c.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 hover:text-gold"
                >
                  <Globe className="size-4" />
                  {c.domain ?? c.website}
                </a>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ScoreRing value={a.priority} kind="priority" size={96} label="Priority" />
            <div className="flex gap-3">
              <ScoreRing value={a.fit} kind="fit" size={56} label="Fit" />
              <ScoreRing value={a.intent} kind="intent" size={56} label="Intent" />
              <ScoreRing value={a.confidence} kind="confidence" size={56} label="Confidence" />
            </div>
          </div>
        </div>
        <div className="relative mt-6 flex flex-wrap items-center gap-3 border-t border-border pt-5">
          <Select
            value={a.status}
            onValueChange={(v) =>
              v === "dismissed"
                ? setDismissOpen(true)
                : update.mutate({ status: v }, { onError: onErr })
            }
          >
            <SelectTrigger className="h-9 w-52 rounded-xl bg-surface-2">
              <span className="text-muted-foreground">Stage:</span>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ref?.account_statuses.map((s) => (
                <SelectItem key={s.code} value={s.code}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={a.owner?.id ?? UNASSIGNED}
            onValueChange={(v) =>
              update.mutate(
                { owner_membership_id: v === UNASSIGNED ? null : v },
                { onError: onErr },
              )
            }
          >
            <SelectTrigger className="h-9 w-52 rounded-xl bg-surface-2">
              <span className="text-muted-foreground">Owner:</span>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNASSIGNED}>Unassigned</SelectItem>
              {members?.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {update.isPending && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
          <div className="ml-auto flex gap-2">
            <Button
              variant="outline"
              className="rounded-xl"
              disabled={research.isPending || c.research_status === "researching"}
              onClick={() =>
                research.mutate(undefined, {
                  onError: onErr,
                  onSuccess: () =>
                    toast.success("Re-research queued", {
                      description: "The agent will refresh evidence and scores.",
                    }),
                })
              }
            >
              <RefreshCw className={research.isPending ? "animate-spin" : ""} />
              Re-research
            </Button>
            {a.status !== "dismissed" && (
              <Button
                variant="ghost"
                className="rounded-xl text-muted-foreground"
                onClick={() => setDismissOpen(true)}
              >
                <XCircle />
                Dismiss
              </Button>
            )}
          </div>
        </div>
      </motion.div>

      <motion.div {...fade(0.05)}>
        <RateLeadCard accountId={a.id} rating={a.feedback} hotelName={a.property_name} />
      </motion.div>

      {/* Next action */}
      {a.next_action.kind !== "none" && (
        <motion.button
          {...fade(0.08)}
          onClick={nextAction}
          className="group flex w-full items-center gap-4 rounded-[var(--radius)] border border-gold/40 bg-gradient-to-r from-gold/15 via-coral/5 to-transparent p-4 text-left transition-colors hover:border-gold/70"
        >
          <span className="grid size-10 shrink-0 place-items-center rounded-full bg-signature text-primary-foreground">
            <Sparkles className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-gold">
              Next best action
            </p>
            <p className="font-semibold">{a.next_action.title}</p>
            <p className="text-sm text-muted-foreground">{a.next_action.detail}</p>
          </div>
          <ArrowRight className="size-5 text-gold transition-transform group-hover:translate-x-1" />
        </motion.button>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
        <TabsList className="h-auto flex-wrap rounded-xl bg-surface p-1">
          <TabsTrigger value="overview" className="rounded-lg">
            Research
          </TabsTrigger>
          <TabsTrigger value="signals" className="rounded-lg">
            Signals{" "}
            <span className="ml-1.5 font-mono text-xs text-muted-foreground">
              {a.signals.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="people" className="rounded-lg">
            People{" "}
            <span className="ml-1.5 font-mono text-xs text-muted-foreground">
              {a.contacts.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="pitch" className="rounded-lg">
            <Sparkles className="mr-1 size-3.5 text-gold" />
            Pitch
          </TabsTrigger>
          <TabsTrigger value="activity" className="rounded-lg">
            Activity & pipeline
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-5">
          <div className="grid items-start gap-5 lg:grid-cols-[1fr_380px]">
            <div className="space-y-5">
              <div className="card-halo p-5">
                <SectionTitle
                  right={
                    <span className="text-xs text-muted-foreground">
                      {c.last_researched_at
                        ? `Researched ${ago(c.last_researched_at)}`
                        : "Not researched yet"}
                    </span>
                  }
                >
                  About
                </SectionTitle>
                {c.description ? (
                  <p className="leading-relaxed">{c.description}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">No description found yet.</p>
                )}
                <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <Fact label="Industry">{c.industry_label}</Fact>
                  <Fact label="Employees">{c.employee_range}</Fact>
                  <Fact label="Headquarters">{c.hq_city}</Fact>
                  <Fact label="Locality">{c.locality}</Fact>
                </dl>
                {c.address && (
                  <p className="mt-4 flex gap-2 text-sm text-muted-foreground">
                    <MapPin className="mt-0.5 size-4 shrink-0" />
                    {c.address}
                  </p>
                )}
              </div>
              <div className="card-halo p-5">
                <SectionTitle
                  right={
                    <span className="text-xs text-muted-foreground">
                      {facts.length} findings · {a.sources.length} sources
                    </span>
                  }
                >
                  What the agent found
                </SectionTitle>
                {facts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No findings yet. Try re-research.</p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    {facts.map((cl) => (
                      <ClaimCard key={cl.id} c={cl} />
                    ))}
                  </div>
                )}
              </div>
              {a.sources.length > 0 && (
                <div className="card-halo p-5">
                  <SectionTitle>Sources</SectionTitle>
                  <ul className="grid gap-2 sm:grid-cols-2">
                    {a.sources.map((s) => (
                      <li key={s.id} className="min-w-0 rounded-lg bg-surface-2/50 px-3 py-2">
                        <p className="truncate text-sm">{s.title ?? s.domain ?? s.url}</p>
                        <SourceLink s={s} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="space-y-5">
              <div className="card-halo p-5">
                <SectionTitle>Why this score</SectionTitle>
                <WhyScore a={a} />
              </div>
              {a.related_accounts.length > 0 && (
                <div className="card-halo p-5">
                  <SectionTitle>Also near your other hotels</SectionTitle>
                  <ul className="space-y-2">
                    {a.related_accounts.map((r) => (
                      <li key={r.id}>
                        <Link
                          to="/p/$propertyId/accounts/$accountId"
                          params={{ propertyId: r.property_id, accountId: r.id }}
                          className="flex items-center justify-between rounded-lg bg-surface-2/50 px-3 py-2 text-sm hover:bg-surface-2"
                        >
                          <span className="truncate">{r.property_name}</span>
                          <TierBadge tier={r.tier} />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="signals" className="mt-5">
          {a.signals.length === 0 ? (
            <div className="card-halo p-10 text-center text-sm text-muted-foreground">
              No buying signals found in the selected window.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {a.signals.map((s) => (
                <div key={s.id} className="card-halo p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <SignalChip
                      label={s.type_label}
                      age={s.published_at ? date(s.published_at) : ageDays(s.age_days)}
                    />
                    {s.is_historical && (
                      <span className="text-[11px] text-muted-foreground">older than window</span>
                    )}
                    <span className="ml-auto font-mono text-[11px] text-muted-foreground">
                      {pct(s.confidence)} sure
                    </span>
                  </div>
                  <h3 className="mt-3 font-semibold leading-snug">{s.title}</h3>
                  {s.description && (
                    <p className="mt-1.5 text-sm text-muted-foreground">{s.description}</p>
                  )}
                  {s.evidence_quote && (
                    <blockquote className="mt-3 border-l-2 border-coral/50 pl-3 text-sm italic text-muted-foreground">
                      "{s.evidence_quote}"
                    </blockquote>
                  )}
                  {s.recommended_approach && (
                    <p className="mt-3 rounded-lg bg-gold/5 p-3 text-sm">
                      <span className="font-medium text-gold">How to use it: </span>
                      {s.recommended_approach}
                    </p>
                  )}
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {s.implied_offerings.map((o) => (
                      <span key={o} className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px]">
                        {OFFERING_LABEL[o]}
                      </span>
                    ))}
                    <SourceLink s={s.source} className="ml-auto" />
                  </div>
                  <div className="mt-3 flex items-center gap-1 border-t border-border pt-3 text-xs text-muted-foreground">
                    <span className="mr-auto">Is this signal right?</span>
                    {(
                      [
                        ["correct", "Right", ThumbsUp, "text-teal bg-teal/15"],
                        ["wrong", "Wrong", ThumbsDown, "text-coral bg-coral/15"],
                      ] as const
                    ).map(([v, label, Icon, on]) => (
                      <button
                        key={v}
                        type="button"
                        aria-pressed={s.feedback === v}
                        disabled={rateSignal.isPending}
                        onClick={() =>
                          rateSignal.mutate(
                            { id: s.id, verdict: s.feedback === v ? null : v },
                            { onError: onErr },
                          )
                        }
                        className={`inline-flex items-center gap-1 rounded-md px-2 py-1 transition-colors ${
                          s.feedback === v ? on : "hover:bg-surface-2 hover:text-foreground"
                        }`}
                      >
                        <Icon className="size-3.5" fill={s.feedback === v ? "currentColor" : "none"} />
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="people" className="mt-5">
          <PeoplePanel account={a} onDraft={draft} />
        </TabsContent>
        <TabsContent value="pitch" className="mt-5">
          <PitchPanel account={a} preset={preset} />
        </TabsContent>
        <TabsContent value="activity" className="mt-5">
          <ActivityPanel account={a} />
        </TabsContent>
      </Tabs>

      <Dialog open={dismissOpen} onOpenChange={setDismissOpen}>
        <DialogContent className="rounded-2xl border-border bg-surface">
          <DialogHeader>
            <DialogTitle className="font-display">Dismiss {c.name}?</DialogTitle>
            <DialogDescription>
              It leaves the active list. Your reason helps tune future scoring.
            </DialogDescription>
          </DialogHeader>
          <Select value={reason} onValueChange={setReason}>
            <SelectTrigger>
              <SelectValue placeholder="Why?" />
            </SelectTrigger>
            <SelectContent>
              {ref?.dismiss_reasons.map((r) => (
                <SelectItem key={r.code} value={r.code}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Note (optional)"
            rows={2}
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDismissOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!reason || update.isPending}
              onClick={() =>
                update.mutate(
                  {
                    status: "dismissed",
                    dismissed_reason: reason,
                    ...(note.trim() ? { dismissed_note: note.trim() } : {}),
                  },
                  {
                    onError: onErr,
                    onSuccess: () => {
                      setDismissOpen(false);
                      toast.success("Dismissed");
                    },
                  },
                )
              }
            >
              Dismiss
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
