import { useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Beaker,
  FileSpreadsheet,
  Lightbulb,
  Loader2,
  Lock,
  Shuffle,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Upload,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { CardSkeleton, ErrorState, Meter, SectionTitle, errorText } from "@/components/halo";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useImportRatings, useLabSummary, useProperties } from "@/hooks/use-halo";
import { ago, pct } from "@/lib/halo-format";
import type { LabSummary, RatingsImport } from "@/lib/halo-types";
import { PageHeader } from "./PlaceholderPage";

const LOOP = [
  {
    icon: Wand2,
    title: "Propose",
    text: "Looks at the leads Halo misjudged and suggests a few changes to how it scores and sorts companies.",
  },
  {
    icon: Beaker,
    title: "Test",
    text: "Tries every suggestion on the leads your team rated and measures how often it agrees with you.",
  },
  {
    icon: Shuffle,
    title: "Combine",
    text: "Merges the changes that helped into one new version, and drops the ones that hurt.",
  },
  {
    icon: Lightbulb,
    title: "Learn",
    text: "Writes down what it learned, so the next round starts smarter.",
  },
];

function AnswerKey({ s }: { s: LabSummary }) {
  const r = s.ratings;
  const goal = s.recommended_ratings;
  return (
    <div className="card-halo p-5">
      <SectionTitle
        right={<span className="font-mono text-xs text-muted-foreground">{r.total} rated</span>}
      >
        Your answer key
      </SectionTitle>
      <p className="text-sm text-muted-foreground">
        Rate prospects with <ThumbsUp className="inline size-3.5 text-teal" /> /{" "}
        <ThumbsDown className="inline size-3.5 text-coral" /> on the Prospects list or a company page.
        Halo Lab uses these ratings to check whether a new version is really better.
      </p>
      <div className="mt-4">
        <div className="mb-1.5 flex justify-between text-xs text-muted-foreground">
          <span>
            {r.total} of {goal} recommended
          </span>
          <span>{s.ready ? "Enough to start" : `At least ${s.min_ratings} needed`}</span>
        </div>
        <Meter value={(r.total / goal) * 100} color={s.ready ? "var(--teal)" : "var(--gold)"} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-teal/10 p-3">
          <p className="font-mono text-2xl text-teal">{r.good_fit}</p>
          <p className="text-xs text-muted-foreground">Good fits</p>
        </div>
        <div className="rounded-xl bg-coral/10 p-3">
          <p className="font-mono text-2xl text-coral">{r.not_fit}</p>
          <p className="text-xs text-muted-foreground">
            Not a fit{r.from_dismissals ? ` (incl. ${r.from_dismissals} dismissed)` : ""}
          </p>
        </div>
      </div>
      {!s.ready && s.not_ready_reason && (
        <p className="mt-3 text-xs text-muted-foreground">{s.not_ready_reason}</p>
      )}
      {(r.signals_correct > 0 || r.signals_wrong > 0) && (
        <p className="mt-3 text-xs text-muted-foreground">
          Signals checked by your team: {r.signals_correct} right, {r.signals_wrong} wrong.
        </p>
      )}
      {r.per_project.length > 0 && (
        <ul className="mt-4 space-y-1.5 border-t border-border pt-4">
          {r.per_project.map((p) => (
            <li key={p.property_id}>
              <Link
                to="/p/$propertyId/accounts"
                params={{ propertyId: p.property_id }}
                search={{}}
                className="flex items-center gap-3 rounded-lg px-2 py-1.5 text-sm hover:bg-surface-2"
              >
                <span className="flex-1 truncate">{p.property_name}</span>
                <span className="font-mono text-xs text-teal">{p.good_fit}</span>
                <span className="font-mono text-xs text-coral">{p.not_fit}</span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function UploadRatings() {
  const { data: props } = useProperties();
  const [pid, setPid] = useState<string>("");
  const [res, setRes] = useState<RatingsImport | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const target = pid || props?.[0]?.id || "";
  const upload = useImportRatings(target);
  const onFile = (f: File | undefined) => {
    if (!f || !target) return;
    upload.mutate(f, {
      onSuccess: (r) => {
        setRes(r);
        toast.success(`${r.created + r.updated} ratings added`);
      },
      onError: (e) => {
        const t = errorText(e);
        toast.error(t.title, { description: t.detail });
      },
    });
    if (fileRef.current) fileRef.current.value = "";
  };
  return (
    <div className="card-halo p-5">
      <SectionTitle>Upload ratings (CSV)</SectionTitle>
      <p className="text-sm text-muted-foreground">
        Already know which nearby companies are good leads? Upload a spreadsheet with a{" "}
        <span className="font-mono text-foreground">Company</span> column, a{" "}
        <span className="font-mono text-foreground">Verdict</span> column (good / not a fit) and,
        if you have it, a <span className="font-mono text-foreground">Website</span> column.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Select value={target} onValueChange={setPid}>
          <SelectTrigger className="h-9 w-60 rounded-xl bg-surface-2">
            <SelectValue placeholder="Choose a hotel" />
          </SelectTrigger>
          <SelectContent>
            {props?.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])}
        />
        <Button
          variant="outline"
          className="rounded-xl"
          disabled={!target || upload.isPending}
          onClick={() => fileRef.current?.click()}
        >
          {upload.isPending ? <Loader2 className="animate-spin" /> : <Upload />}
          Choose CSV file
        </Button>
      </div>
      {res && (
        <div className="mt-4 rounded-xl bg-surface-2/60 p-3 text-sm">
          <p className="flex items-center gap-2">
            <FileSpreadsheet className="size-4 text-teal" />
            {res.created} new and {res.updated} updated ratings.
          </p>
          {res.unmatched_count > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {res.unmatched_count} companies aren't in this hotel's prospects yet:{" "}
              {res.unmatched.slice(0, 6).join(", ")}
              {res.unmatched_count > 6 ? "…" : ""}
            </p>
          )}
          {res.invalid.length > 0 && (
            <p className="mt-1 text-xs text-coral">
              {res.invalid.length} rows skipped: {res.invalid[0]?.message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function LabPage() {
  const q = useLabSummary();
  const s = q.data;
  if (q.error) return <ErrorState error={q.error} onRetry={() => void q.refetch()} />;
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Halo Lab"
        sub="Teach Halo what a good lead looks like for your hotels. It only suggests a new version when it measurably agrees with your team more."
      />
      {!s ? (
        <div className="grid gap-5 lg:grid-cols-2">
          <CardSkeleton lines={5} />
          <CardSkeleton lines={5} />
        </div>
      ) : (
        <div className="grid items-start gap-5 lg:grid-cols-[1fr_380px]">
          <div className="space-y-5">
            <div className="card-halo relative overflow-hidden p-6">
              <div
                className="pointer-events-none absolute -right-24 -top-24 size-64 rounded-full opacity-50 blur-3xl"
                style={{ background: "color-mix(in oklab, var(--violet) 25%, transparent)" }}
              />
              <div className="relative flex flex-wrap items-center gap-5">
                <span className="grid size-12 place-items-center rounded-2xl bg-signature text-primary-foreground">
                  <Sparkles className="size-6" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Live agent
                  </p>
                  <p className="text-2xl font-bold">Version {s.active_version.version}</p>
                  <p className="text-sm text-muted-foreground">
                    {s.active_version.summary}
                    {s.active_version.decided_at
                      ? ` · Approved ${ago(s.active_version.decided_at)}`
                      : ""}
                  </p>
                </div>
                {s.active_version.metrics.accuracy != null && (
                  <div className="text-right">
                    <p className="font-mono text-3xl text-teal">
                      {pct(s.active_version.metrics.accuracy)}
                    </p>
                    <p className="text-xs text-muted-foreground">agrees with your team</p>
                  </div>
                )}
              </div>
            </div>

            <div className="card-halo p-5">
              <SectionTitle>How Halo Lab improves the agent</SectionTitle>
              <ol className="grid gap-3 sm:grid-cols-2">
                {LOOP.map((l, i) => (
                  <li key={l.title} className="rounded-xl bg-surface-2/50 p-4">
                    <div className="flex items-center gap-2">
                      <span className="grid size-7 place-items-center rounded-lg bg-violet/15 text-violet">
                        <l.icon className="size-4" />
                      </span>
                      <span className="font-semibold">
                        {i + 1}. {l.title}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{l.text}</p>
                  </li>
                ))}
              </ol>
              <p className="mt-4 flex gap-2 rounded-xl border border-dashed border-border p-3 text-xs text-muted-foreground">
                <Lock className="mt-0.5 size-3.5 shrink-0" />
                The fact-checking rules are locked: Halo Lab can change how leads are scored and
                sorted, but it can never let the agent state facts without a source. A person approves
                every new version, and you can switch back to an older one at any time.
              </p>
            </div>
          </div>

          <div className="space-y-5">
            <AnswerKey s={s} />
            {s.can_manage && <UploadRatings />}
          </div>
        </div>
      )}
    </div>
  );
}
