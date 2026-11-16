import { useState } from "react";
import { Link, useParams } from "@tanstack/react-router";
import { CalendarDays, GripVertical, Trophy, Wallet } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, ErrorState, KpiTile, TableSkeleton, errorText } from "@/components/halo";
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
import { Textarea } from "@/components/ui/textarea";
import {
  useOpportunities,
  useProjectUnits,
  useProperty,
  useReference,
  useUpdateOpportunity,
} from "@/hooks/use-halo";
import { date, money, OFFERING_LABEL } from "@/lib/halo-format";
import type { Opportunity, OpportunityStage } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

const STAGES: { key: OpportunityStage; color: string }[] = [
  { key: "interested", color: "var(--teal)" },
  { key: "meeting_scheduled", color: "var(--violet)" },
  { key: "negotiation", color: "var(--gold)" },
  { key: "won", color: "oklch(0.75 0.17 150)" },
  { key: "lost", color: "var(--slate)" },
];

export function PipelinePage() {
  const { propertyId } = useParams({ strict: false }) as { propertyId: string };
  const prop = useProperty(propertyId);
  const opps = useOpportunities(propertyId);
  const { data: ref } = useReference();
  const move = useUpdateOpportunity();
  const [drag, setDrag] = useState<string | null>(null);
  const [over, setOver] = useState<OpportunityStage | null>(null);
  const [losing, setLosing] = useState<Opportunity | null>(null);
  const [lossReason, setLossReason] = useState("");
  const [lossNote, setLossNote] = useState("");
  const list = opps.data ?? [];
  const { currency: projectCurrency } = useProjectUnits(propertyId);
  const currency = list[0]?.currency ?? projectCurrency;
  const label = (s: string) =>
    ref?.opportunity_stages.find((x) => x.code === s)?.label ?? s.replace(/_/g, " ");
  const open = list.filter((o) => !["won", "lost"].includes(o.stage));
  const sum = (xs: Opportunity[]) => xs.reduce((s, o) => s + (o.value_amount ?? 0), 0);
  const weighted = open.reduce(
    (s, o) => s + (o.value_amount ?? 0) * ((o.probability ?? 0) / 100),
    0,
  );
  const won = list.filter((o) => o.stage === "won");
  const closed = won.length + list.filter((o) => o.stage === "lost").length;

  const onErr = (e: unknown) => {
    const t = errorText(e);
    toast.error(t.title, { description: t.detail });
  };
  const moveTo = (o: Opportunity, stage: OpportunityStage) => {
    if (o.stage === stage) return;
    if (stage === "lost") {
      setLosing(o);
      setLossReason("");
      setLossNote("");
      return;
    }
    move.mutate(
      { id: o.id, stage },
      {
        onError: onErr,
        onSuccess: () =>
          stage === "won" &&
          toast.success(`${o.company_name} won!`, {
            icon: <Trophy className="size-4 text-gold" />,
          }),
      },
    );
  };

  if (opps.error) return <ErrorState error={opps.error} onRetry={() => void opps.refetch()} />;

  return (
    <div className="mx-auto max-w-[1400px]">
      <div className="mb-6">
        <p className="text-sm text-muted-foreground">{prop.data?.name}</p>
        <h1 className="mt-1 text-[32px] font-bold leading-tight">Pipeline</h1>
      </div>
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Open pipeline"
          value={opps.data ? sum(open) : null}
          format={(n) => money(n, currency)}
          icon={<Wallet className="size-4" />}
          sub={`${open.length} open deals`}
        />
        <KpiTile
          label="Weighted forecast"
          value={opps.data ? weighted : null}
          format={(n) => money(n, currency)}
          accent
          sub="Value × chance to close"
        />
        <KpiTile
          label="Won"
          value={opps.data ? sum(won) : null}
          format={(n) => money(n, currency)}
          icon={<Trophy className="size-4 text-gold" />}
          sub={`${won.length} deals`}
        />
        <KpiTile
          label="Win rate"
          value={closed ? Math.round((won.length / closed) * 100) : null}
          format={(n) => `${Math.round(n)}%`}
          sub={closed ? `${closed} closed` : "No closed deals yet"}
        />
      </div>

      {opps.isLoading ? (
        <TableSkeleton rows={4} />
      ) : list.length === 0 ? (
        <div className="card-halo">
          <EmptyState
            title="No opportunities yet"
            text="Open a hot prospect's dossier and add it to the pipeline from the Activity tab."
            action={
              <Button variant="signature" className="rounded-xl" asChild>
                <Link to="/p/$propertyId/accounts" params={{ propertyId }} search={{ tier: "A" }}>
                  See hot prospects
                </Link>
              </Button>
            }
          />
        </div>
      ) : (
        <div className="grid gap-4 overflow-x-auto pb-2 md:grid-cols-5">
          {STAGES.map((st) => {
            const col = list.filter((o) => o.stage === st.key);
            return (
              <div
                key={st.key}
                onDragOver={(e) => {
                  e.preventDefault();
                  setOver(st.key);
                }}
                onDragLeave={() => setOver((o) => (o === st.key ? null : o))}
                onDrop={(e) => {
                  e.preventDefault();
                  setOver(null);
                  const o = list.find((x) => x.id === drag);
                  if (o) moveTo(o, st.key);
                  setDrag(null);
                }}
                className={cn(
                  "flex min-h-[320px] min-w-[220px] flex-col rounded-[var(--radius)] border border-border bg-surface/50 p-3 transition-colors",
                  over === st.key && "border-gold/50 bg-gold/5",
                )}
              >
                <div className="mb-3 flex items-center gap-2 px-1">
                  <span
                    className="size-2 rounded-full"
                    style={{ background: st.color, boxShadow: `0 0 8px ${st.color}` }}
                  />
                  <span className="text-sm font-semibold">{label(st.key)}</span>
                  <span className="font-mono text-xs text-muted-foreground">{col.length}</span>
                  <span className="ml-auto font-mono text-[11px] text-muted-foreground">
                    {col.length ? money(sum(col), currency) : ""}
                  </span>
                </div>
                <div className="flex flex-1 flex-col gap-2">
                  {col.map((o) => (
                    <div
                      key={o.id}
                      draggable
                      onDragStart={() => setDrag(o.id)}
                      onDragEnd={() => setDrag(null)}
                      className={cn(
                        "group cursor-grab rounded-xl border border-border bg-surface p-3 shadow-card transition-all hover:border-gold/30 active:cursor-grabbing",
                        drag === o.id && "opacity-40",
                      )}
                      style={{ borderLeft: `3px solid ${st.color}` }}
                    >
                      <div className="flex items-start gap-1">
                        <Link
                          to="/p/$propertyId/accounts/$accountId"
                          params={{ propertyId, accountId: o.account_id }}
                          className="min-w-0 flex-1"
                        >
                          <p className="truncate text-sm font-semibold hover:text-gold">
                            {o.company_name}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">{o.name}</p>
                        </Link>
                        <GripVertical className="size-4 shrink-0 text-muted-foreground/40" />
                      </div>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="font-mono text-sm text-gold">
                          {money(o.value_amount, o.currency)}
                        </span>
                        {o.probability != null && (
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {o.probability}%
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2 text-[11px] text-muted-foreground">
                        <span>{OFFERING_LABEL[o.offering]}</span>
                        {o.expected_close_date && (
                          <span className="inline-flex items-center gap-1">
                            <CalendarDays className="size-3" />
                            {date(o.expected_close_date)}
                          </span>
                        )}
                        {o.owner && <span>· {o.owner.name}</span>}
                      </div>
                      {o.stage === "lost" && o.loss_reason && (
                        <p className="mt-1 text-[11px] text-coral">
                          {ref?.loss_reasons.find((x) => x.code === o.loss_reason)?.label ??
                            o.loss_reason}
                        </p>
                      )}
                      <Select
                        value={o.stage}
                        onValueChange={(v) => moveTo(o, v as OpportunityStage)}
                      >
                        <SelectTrigger className="mt-2 h-7 rounded-lg bg-surface-2 text-xs md:hidden">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {STAGES.map((s) => (
                            <SelectItem key={s.key} value={s.key}>
                              {label(s.key)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                  {col.length === 0 && (
                    <div className="grid flex-1 place-items-center rounded-xl border border-dashed border-border text-xs text-muted-foreground">
                      Drop here
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={!!losing} onOpenChange={(o) => !o && setLosing(null)}>
        <DialogContent className="rounded-2xl border-border bg-surface">
          <DialogHeader>
            <DialogTitle className="font-display">Why was {losing?.company_name} lost?</DialogTitle>
            <DialogDescription>This feeds the learning loop for future scoring.</DialogDescription>
          </DialogHeader>
          <Select value={lossReason} onValueChange={setLossReason}>
            <SelectTrigger>
              <SelectValue placeholder="Pick a reason" />
            </SelectTrigger>
            <SelectContent>
              {ref?.loss_reasons.map((r) => (
                <SelectItem key={r.code} value={r.code}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Textarea
            value={lossNote}
            onChange={(e) => setLossNote(e.target.value)}
            placeholder="Note (optional)"
            rows={2}
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setLosing(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!lossReason || move.isPending}
              onClick={() =>
                losing &&
                move.mutate(
                  {
                    id: losing.id,
                    stage: "lost",
                    loss_reason: lossReason,
                    ...(lossNote.trim() ? { loss_note: lossNote.trim() } : {}),
                  },
                  { onError: onErr, onSuccess: () => setLosing(null) },
                )
              }
            >
              Mark lost
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
