import { useState } from "react";
import {
  ArrowRightLeft,
  Bot,
  Briefcase,
  CalendarDays,
  Copy,
  Loader2,
  Mail,
  MessageSquare,
  Phone,
  Plus,
  StickyNote,
} from "lucide-react";
import { toast } from "sonner";
import { SectionTitle, errorText } from "@/components/halo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAddActivity, useCreateOpportunity, useReference } from "@/hooks/use-halo";
import { ago, date, dateTime, money, OFFERING_LABEL } from "@/lib/halo-format";
import type { AccountDetail, ActivityType, Offering } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

const ACT_ICON: Record<ActivityType, React.ReactNode> = {
  note: <StickyNote className="size-3.5" />,
  call: <Phone className="size-3.5" />,
  meeting: <CalendarDays className="size-3.5" />,
  email_sent: <Mail className="size-3.5" />,
  status_change: <ArrowRightLeft className="size-3.5" />,
  stage_change: <Briefcase className="size-3.5" />,
  draft_copied: <Copy className="size-3.5" />,
  system: <Bot className="size-3.5" />,
};
const LOG_TYPES = [
  { v: "note", l: "Note" },
  { v: "call", l: "Call" },
  { v: "meeting", l: "Meeting" },
  { v: "email_sent", l: "Email sent" },
] as const;

export function ActivityPanel({ account }: { account: AccountDetail }) {
  const { data: ref } = useReference();
  const log = useAddActivity(account.id);
  const createOpp = useCreateOpportunity(account.id);
  const [type, setType] = useState<(typeof LOG_TYPES)[number]["v"]>("note");
  const [body, setBody] = useState("");
  const [oppOpen, setOppOpen] = useState(false);
  const defaultOffering: Offering = account.roles[0]?.offering ?? "corporate_rate";
  const [opp, setOpp] = useState({
    name: `${account.company.name} · ${OFFERING_LABEL[defaultOffering]}`,
    offering: defaultOffering,
    value: "",
    close: "",
    prob: "",
  });
  const onErr = (e: unknown) => {
    const t = errorText(e);
    toast.error(t.title, { description: t.detail });
  };
  const stageLabel = (s: string) => ref?.opportunity_stages.find((x) => x.code === s)?.label ?? s;

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[1fr_380px]">
      <div className="card-halo p-5">
        <SectionTitle>Timeline</SectionTitle>
        <form
          className="mb-6 space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            log.mutate(
              { type, body: body.trim() },
              {
                onSuccess: () => {
                  setBody("");
                  toast.success("Logged");
                },
                onError: onErr,
              },
            );
          }}
        >
          <div className="flex gap-1 rounded-xl bg-surface-2 p-1">
            {LOG_TYPES.map((t) => (
              <button
                type="button"
                key={t.v}
                onClick={() => setType(t.v)}
                className={cn(
                  "flex-1 rounded-lg py-1.5 text-xs",
                  type === t.v ? "bg-surface font-medium shadow" : "text-muted-foreground",
                )}
              >
                {t.l}
              </button>
            ))}
          </div>
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={2}
            placeholder="What happened?"
            className="resize-none rounded-xl bg-surface-2"
          />
          <div className="flex justify-end">
            <Button size="sm" disabled={!body.trim() || log.isPending}>
              {log.isPending ? <Loader2 className="animate-spin" /> : <MessageSquare />}Log it
            </Button>
          </div>
        </form>
        {account.activities.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing logged yet.</p>
        ) : (
          <ol className="relative space-y-5 border-l border-border pl-6">
            {account.activities.map((a) => (
              <li key={a.id} className="relative">
                <span className="absolute -left-[37px] grid size-6 place-items-center rounded-full border border-border bg-surface text-muted-foreground">
                  {ACT_ICON[a.type]}
                </span>
                <div className="text-xs text-muted-foreground">
                  {a.actor?.name ?? "Halo"} ·{" "}
                  <span title={dateTime(a.occurred_at)}>{ago(a.occurred_at)}</span>
                </div>
                {a.body && <p className="mt-0.5 whitespace-pre-line text-sm">{a.body}</p>}
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="card-halo p-5">
        <SectionTitle
          right={
            !oppOpen && (
              <Button
                size="sm"
                variant="outline"
                className="rounded-lg"
                onClick={() => setOppOpen(true)}
              >
                <Plus />
                New
              </Button>
            )
          }
        >
          Opportunities
        </SectionTitle>
        {oppOpen && (
          <form
            className="mb-4 space-y-3 rounded-xl border border-gold/30 bg-gold/5 p-4"
            onSubmit={(e) => {
              e.preventDefault();
              createOpp.mutate(
                {
                  name: opp.name.trim(),
                  offering: opp.offering,
                  value_amount: opp.value ? Number(opp.value) : null,
                  expected_close_date: opp.close || null,
                  probability: opp.prob ? Math.round(Number(opp.prob)) : null,
                },
                {
                  onSuccess: () => {
                    setOppOpen(false);
                    toast.success("Added to pipeline");
                  },
                  onError: onErr,
                },
              );
            }}
          >
            <div className="space-y-1">
              <Label htmlFor="o-name">Name</Label>
              <Input
                id="o-name"
                required
                value={opp.name}
                onChange={(e) => setOpp({ ...opp, name: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <Label>Offer</Label>
              <Select
                value={opp.offering}
                onValueChange={(v) => setOpp({ ...opp, offering: v as Offering })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ref?.offerings.map((o) => (
                    <SelectItem key={o.code} value={o.code}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <Label htmlFor="o-val">Value ₹</Label>
                <Input
                  id="o-val"
                  type="number"
                  min={0}
                  value={opp.value}
                  onChange={(e) => setOpp({ ...opp, value: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="o-prob">Chance %</Label>
                <Input
                  id="o-prob"
                  type="number"
                  min={0}
                  max={100}
                  value={opp.prob}
                  onChange={(e) => setOpp({ ...opp, prob: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="o-close">Close by</Label>
                <Input
                  id="o-close"
                  type="date"
                  value={opp.close}
                  onChange={(e) => setOpp({ ...opp, close: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => setOppOpen(false)}>
                Cancel
              </Button>
              <Button disabled={createOpp.isPending}>
                {createOpp.isPending && <Loader2 className="animate-spin" />}Add
              </Button>
            </div>
          </form>
        )}
        {account.opportunities.length === 0 && !oppOpen ? (
          <p className="text-sm text-muted-foreground">Not in the pipeline yet.</p>
        ) : (
          <ul className="space-y-2">
            {account.opportunities.map((o) => (
              <li key={o.id} className="rounded-xl border border-border p-3.5">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium">{o.name}</span>
                  <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-[11px]">
                    {stageLabel(o.stage)}
                  </span>
                </div>
                <div className="mt-1 font-mono text-sm text-gold">
                  {money(o.value_amount, o.currency)}
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {OFFERING_LABEL[o.offering]}
                  {o.expected_close_date ? ` · close ${date(o.expected_close_date)}` : ""}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
