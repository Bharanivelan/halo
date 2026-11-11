import { ExternalLink, FileText, Quote } from "lucide-react";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { Claim, SourceRef } from "@/lib/halo-types";
import { date, pct } from "@/lib/halo-format";
import { cn } from "@/lib/utils";

export const KIND_STYLE = {
  fact: { label: "Fact", cls: "border-teal/40 bg-teal/10 text-teal" },
  inference: { label: "Inference", cls: "border-violet/40 bg-violet/10 text-violet" },
  unknown: { label: "Unknown", cls: "border-border bg-surface-2 text-muted-foreground" },
} as const;

export function SourceLink({
  s,
  className,
}: {
  s: SourceRef | null | undefined;
  className?: string;
}) {
  if (!s) return <span className={cn("text-xs text-muted-foreground", className)}>No source</span>;
  const label = s.domain ?? s.title ?? s.source_type.replace(/_/g, " ");
  const when = s.published_at ? date(s.published_at) : `retrieved ${date(s.retrieved_at)}`;
  const inner = (
    <>
      <FileText className="size-3 shrink-0" />
      <span className="truncate">{label}</span>
      <span className="shrink-0 text-muted-foreground/70">· {when}</span>
    </>
  );
  return s.url ? (
    <a
      href={s.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground hover:text-gold",
        className,
      )}
    >
      {inner}
      <ExternalLink className="size-3 shrink-0" />
    </a>
  ) : (
    <span
      className={cn(
        "inline-flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground",
        className,
      )}
    >
      {inner}
    </span>
  );
}

export function ClaimCard({ c }: { c: Claim }) {
  const k = KIND_STYLE[c.kind];
  return (
    <div className="rounded-xl border border-border bg-surface-2/50 p-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">{c.field_label}</span>
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
            k.cls,
          )}
        >
          {k.label}
        </span>
        <span className="ml-auto font-mono text-[11px] text-muted-foreground">
          {pct(c.confidence)} sure
        </span>
      </div>
      <p className="mt-1.5 font-medium">{c.display_value}</p>
      {c.evidence_quote && (
        <blockquote className="mt-2 flex gap-2 border-l-2 border-gold/50 pl-3 text-sm italic text-muted-foreground">
          <Quote className="mt-0.5 size-3 shrink-0 text-gold/70" />"{c.evidence_quote}"
        </blockquote>
      )}
      {c.rationale && <p className="mt-2 text-xs text-muted-foreground">{c.rationale}</p>}
      <div className="mt-2 flex items-center gap-2">
        <SourceLink s={c.source} />
        {c.grounding_status === "failed" && (
          <span className="text-[11px] text-coral">quote not found in source</span>
        )}
      </div>
    </div>
  );
}

/** Inline evidence marker for copilot text blocks: hover to see the claims behind it. */
export function EvidenceMarker({ ids, claims }: { ids: string[]; claims: Map<string, Claim> }) {
  const found = ids.map((i) => claims.get(i)).filter((c): c is Claim => !!c);
  if (!found.length) return null;
  return (
    <HoverCard openDelay={100}>
      <HoverCardTrigger asChild>
        <button className="ml-1 inline-flex translate-y-[-2px] items-center rounded-full border border-gold/40 bg-gold/10 px-1.5 font-mono text-[10px] text-gold">
          {found.length}
        </button>
      </HoverCardTrigger>
      <HoverCardContent className="w-80 space-y-2 border-border bg-surface">
        <p className="text-xs font-medium text-muted-foreground">Backed by</p>
        {found.map((c) => (
          <div key={c.id} className="text-sm">
            <span className="text-muted-foreground">{c.field_label}: </span>
            {c.display_value}
            <div>
              <SourceLink s={c.source} />
            </div>
          </div>
        ))}
      </HoverCardContent>
    </HoverCard>
  );
}
