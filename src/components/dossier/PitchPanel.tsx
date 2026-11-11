import { useEffect, useMemo, useState } from "react";
import {
  Check,
  Copy,
  Loader2,
  MailCheck,
  PenLine,
  Phone,
  Save,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { EmptyState, SectionTitle, errorText } from "@/components/halo";
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
import {
  useEditPitch,
  useGeneratePitch,
  usePitchCopied,
  usePitches,
  usePitchSent,
  useReference,
} from "@/hooks/use-halo";
import { ago, OFFERING_LABEL } from "@/lib/halo-format";
import type { AccountDetail, Claim, CopilotBlock, CopilotOutput, Offering } from "@/lib/halo-types";
import { cn } from "@/lib/utils";
import { EvidenceMarker } from "./Evidence";

const NONE = "__none";
const bodyOf = (p: CopilotOutput) =>
  p.edited?.body ?? p.content.email.body_blocks.map((b) => b.text).join("\n\n");
const subjectOf = (p: CopilotOutput) => p.edited?.subject ?? p.content.email.subject;

function Blocks({ blocks, claims }: { blocks: CopilotBlock[]; claims: Map<string, Claim> }) {
  return (
    <div className="space-y-2">
      {blocks.map((b, i) => (
        <p
          key={i}
          className={cn("text-sm leading-relaxed", b.is_inference && "text-muted-foreground")}
        >
          {b.is_inference && (
            <span className="mr-1.5 rounded border border-violet/40 bg-violet/10 px-1 text-[10px] uppercase text-violet">
              inference
            </span>
          )}
          {b.text}
          <EvidenceMarker ids={b.claims} claims={claims} />
        </p>
      ))}
    </div>
  );
}

export function PitchPanel({
  account,
  preset,
}: {
  account: AccountDetail;
  preset: { role_code?: string; offering?: Offering; contact_id?: string } | null;
}) {
  const { data: ref } = useReference();
  const pitches = usePitches(account.id);
  const gen = useGeneratePitch(account.id);
  const edit = useEditPitch(account.id);
  const copied = usePitchCopied(account.id);
  const sent = usePitchSent(account.id);
  const claims = useMemo(() => new Map(account.claims.map((c) => [c.id, c])), [account.claims]);

  const [offering, setOffering] = useState<Offering>(
    account.roles[0]?.offering ?? "corporate_rate",
  );
  const [role, setRole] = useState<string>(account.roles[0]?.role_code ?? NONE);
  const [contact, setContact] = useState<string>(NONE);
  const [tone, setTone] = useState<"warm" | "formal">("warm");
  const [pickedId, setPickedId] = useState<string | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [justCopied, setJustCopied] = useState(false);

  useEffect(() => {
    if (!preset) return;
    if (preset.offering) setOffering(preset.offering);
    if (preset.role_code) setRole(preset.role_code);
    if (preset.contact_id) setContact(preset.contact_id);
  }, [preset]);

  const list = pitches.data ?? [];
  const current = list.find((p) => p.id === pickedId) ?? list[0];
  useEffect(() => {
    if (current) {
      setSubject(subjectOf(current));
      setBody(bodyOf(current));
    }
  }, [current]);
  const dirty = !!current && (subject !== subjectOf(current) || body !== bodyOf(current));

  const onErr = (e: unknown) => {
    const t = errorText(e);
    toast.error(t.title, { description: t.detail });
  };
  const generate = () =>
    gen.mutate(
      {
        offering,
        tone,
        ...(role !== NONE ? { role_code: role } : {}),
        ...(contact !== NONE ? { contact_id: contact } : {}),
      },
      {
        onSuccess: (p) => {
          setPickedId(p.id);
          toast.success("Draft ready");
        },
        onError: onErr,
      },
    );
  const copy = async () => {
    if (!current) return;
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    } catch {
      /* clipboard blocked; still log */
    }
    setJustCopied(true);
    setTimeout(() => setJustCopied(false), 1800);
    copied.mutate(current.id, { onError: onErr });
  };

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[320px_1fr]">
      {/* Generator */}
      <div className="card-halo space-y-4 p-5 lg:sticky lg:top-24">
        <SectionTitle className="mb-0">
          <span className="inline-flex items-center gap-2">
            <Wand2 className="size-4 text-violet" />
            Pitch writer
          </span>
        </SectionTitle>
        <div className="space-y-1.5">
          <Label>Offer</Label>
          <Select value={offering} onValueChange={(v) => setOffering(v as Offering)}>
            <SelectTrigger className="rounded-xl bg-surface-2">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(ref?.offerings ?? []).map((o) => (
                <SelectItem key={o.code} value={o.code}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Who you're writing to</Label>
          <Select value={contact} onValueChange={setContact}>
            <SelectTrigger className="rounded-xl bg-surface-2">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>No named contact</SelectItem>
              {account.contacts
                .filter((c) => !c.do_not_contact)
                .map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.full_name}
                    {c.title ? ` · ${c.title}` : ""}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Their role</Label>
          <Select value={role} onValueChange={setRole}>
            <SelectTrigger className="rounded-xl bg-surface-2">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>Any decision-maker</SelectItem>
              {(ref?.role_codes ?? []).map((r) => (
                <SelectItem key={r.code} value={r.code}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
          {(["warm", "formal"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTone(t)}
              className={cn(
                "rounded-lg py-1.5 text-xs capitalize",
                tone === t ? "bg-surface font-medium shadow" : "text-muted-foreground",
              )}
            >
              {t}
            </button>
          ))}
        </div>
        <Button
          variant="signature"
          className="w-full rounded-xl"
          onClick={generate}
          disabled={gen.isPending}
        >
          {gen.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {list.length ? "Write a new draft" : "Write the pitch"}
        </Button>
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Every line cites the evidence behind it. Halo never sends anything: you copy and send it
          yourself.
        </p>
        {list.length > 1 && (
          <div className="space-y-1 border-t border-border pt-3">
            <p className="text-xs text-muted-foreground">Drafts</p>
            {list.map((p) => (
              <button
                key={p.id}
                onClick={() => setPickedId(p.id)}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs hover:bg-surface-2",
                  current?.id === p.id && "bg-surface-2",
                )}
              >
                <span>
                  v{p.version} · {OFFERING_LABEL[p.offering]}
                </span>
                <span className="text-muted-foreground">{ago(p.created_at)}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Output */}
      <div className="space-y-5">
        {gen.isPending && (
          <div className="card-halo relative overflow-hidden p-6">
            <div className="shimmer absolute inset-0" />
            <div className="relative flex items-center gap-3">
              <Loader2 className="size-5 animate-spin text-violet" />
              <div>
                <p className="font-medium">Reading the evidence and writing…</p>
                <p className="text-sm text-muted-foreground">Usually 10–40 seconds.</p>
              </div>
            </div>
          </div>
        )}
        {!current && !gen.isPending && (
          <div className="card-halo">
            <EmptyState
              title="No pitch yet"
              text="Pick the offer and who you're writing to, then let Halo draft a brief, an email and call questions."
            />
          </div>
        )}
        {current && (
          <>
            <div className="card-halo p-5">
              <SectionTitle
                right={
                  <span className="text-xs text-muted-foreground">
                    {current.generated_by === "template" ? "Template draft (AI off)" : "AI draft"} ·
                    v{current.version}
                  </span>
                }
              >
                Why them, why now
              </SectionTitle>
              <Blocks blocks={current.content.brief.summary} claims={claims} />
              {current.content.brief.opportunity.length > 0 && (
                <div className="mt-4 rounded-xl border border-gold/30 bg-gold/5 p-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gold">
                    The opportunity · {OFFERING_LABEL[current.content.brief.recommended_offering]}
                  </p>
                  <Blocks blocks={current.content.brief.opportunity} claims={claims} />
                </div>
              )}
              {current.content.brief.approach && (
                <p className="mt-4 text-sm">
                  <span className="font-medium">Approach: </span>
                  <span className="text-muted-foreground">{current.content.brief.approach}</span>
                </p>
              )}
            </div>

            <div className="card-halo p-5">
              <SectionTitle
                right={
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-0.5 text-xs",
                      current.status === "marked_sent"
                        ? "bg-teal/15 text-teal"
                        : current.status === "copied"
                          ? "bg-gold/15 text-gold"
                          : "bg-surface-2 text-muted-foreground",
                    )}
                  >
                    {current.status === "marked_sent"
                      ? "Sent"
                      : current.status === "copied"
                        ? "Copied"
                        : current.status === "edited"
                          ? "Edited"
                          : "Draft"}
                  </span>
                }
              >
                <span className="inline-flex items-center gap-2">
                  <PenLine className="size-4" />
                  Email
                </span>
              </SectionTitle>
              <div className="space-y-3">
                <Input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="rounded-xl bg-surface-2 font-medium"
                  aria-label="Subject"
                />
                <Textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={12}
                  className="rounded-xl bg-surface-2 text-sm leading-relaxed"
                  aria-label="Body"
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {dirty && (
                  <Button
                    variant="outline"
                    className="rounded-xl"
                    disabled={edit.isPending}
                    onClick={() =>
                      edit.mutate(
                        { id: current.id, subject, body },
                        { onError: onErr, onSuccess: () => toast.success("Saved") },
                      )
                    }
                  >
                    <Save />
                    Save edits
                  </Button>
                )}
                <Button variant="signature" className="rounded-xl" onClick={copy}>
                  {justCopied ? <Check /> : <Copy />}
                  {justCopied ? "Copied" : "Copy email"}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-xl"
                  disabled={sent.isPending || current.status === "marked_sent"}
                  onClick={() =>
                    sent.mutate(current.id, {
                      onError: onErr,
                      onSuccess: () =>
                        toast.success("Marked as sent", {
                          description: "Status moved to outreach sent.",
                        }),
                    })
                  }
                >
                  <MailCheck />
                  {current.status === "marked_sent" ? "Sent" : "I sent it"}
                </Button>
              </div>
            </div>

            {current.content.call_questions.length > 0 && (
              <div className="card-halo p-5">
                <SectionTitle>
                  <span className="inline-flex items-center gap-2">
                    <Phone className="size-4" />
                    If you call instead
                  </span>
                </SectionTitle>
                <ol className="space-y-2">
                  {current.content.call_questions.map((q, i) => (
                    <li key={i} className="flex gap-3 text-sm">
                      <span className="grid size-6 shrink-0 place-items-center rounded-full bg-surface-2 font-mono text-xs">
                        {i + 1}
                      </span>
                      <span className="pt-0.5">{q}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
