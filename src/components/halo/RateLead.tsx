import { Loader2, ThumbsDown, ThumbsUp } from "lucide-react";
import { toast } from "sonner";
import { errorText } from "@/components/halo/States";
import { useRateProspect } from "@/hooks/use-halo";
import type { LeadRating, LeadVerdict } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

/** Why a prospect is not a fit (same codes as the API). */
export const NOT_FIT_REASONS: Record<string, string> = {
  not_a_business: "Not a real business office",
  wrong_industry: "Wrong industry for us",
  too_small: "Too small",
  too_far: "Too far away",
  no_travel_need: "No reason to need a hotel",
  other: "Other",
};

function useRate(accountId: string) {
  const rate = useRateProspect();
  const set = (verdict: LeadVerdict | null, reason?: string | null) =>
    rate.mutate(
      { id: accountId, verdict, reason },
      {
        onError: (e) => {
          const t = errorText(e);
          toast.error(t.title, { description: t.detail });
        },
      },
    );
  return { set, pending: rate.isPending };
}

/** Two small thumbs for a table row. Clicking the selected one clears the rating. */
export function RateLeadCompact({
  accountId,
  rating,
  name,
}: {
  accountId: string;
  rating: LeadRating | null | undefined;
  name: string;
}) {
  const { set, pending } = useRate(accountId);
  const v = rating?.verdict;
  const btn = "grid size-7 place-items-center rounded-md transition-colors disabled:opacity-50";
  return (
    <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        aria-label={`${name}: good fit`}
        aria-pressed={v === "good_fit"}
        title="Good fit for this hotel"
        disabled={pending}
        onClick={() => set(v === "good_fit" ? null : "good_fit")}
        className={cn(
          btn,
          v === "good_fit"
            ? "bg-teal/15 text-teal"
            : "text-muted-foreground/60 hover:bg-surface-2 hover:text-teal",
        )}
      >
        <ThumbsUp className="size-3.5" fill={v === "good_fit" ? "currentColor" : "none"} />
      </button>
      <button
        type="button"
        aria-label={`${name}: not a fit`}
        aria-pressed={v === "not_fit"}
        title="Not a fit for this hotel"
        disabled={pending}
        onClick={() => set(v === "not_fit" ? null : "not_fit")}
        className={cn(
          btn,
          v === "not_fit"
            ? "bg-coral/15 text-coral"
            : "text-muted-foreground/60 hover:bg-surface-2 hover:text-coral",
        )}
      >
        <ThumbsDown className="size-3.5" fill={v === "not_fit" ? "currentColor" : "none"} />
      </button>
    </div>
  );
}

/** Full rating card for the company page, with reason chips for "not a fit". */
export function RateLeadCard({
  accountId,
  rating,
  hotelName,
}: {
  accountId: string;
  rating: LeadRating | null | undefined;
  hotelName: string;
}) {
  const { set, pending } = useRate(accountId);
  const v = rating?.verdict;
  const pill = "inline-flex items-center gap-1.5 rounded-xl border px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-60";
  return (
    <div className="card-halo p-5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-semibold">Is this a good lead for {hotelName}?</p>
          <p className="text-xs text-muted-foreground">
            Your ratings teach Halo Lab what a good lead looks like for your hotel.
          </p>
        </div>
        {pending && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
        <button
          type="button"
          aria-pressed={v === "good_fit"}
          disabled={pending}
          onClick={() => set(v === "good_fit" ? null : "good_fit")}
          className={cn(
            pill,
            v === "good_fit"
              ? "border-teal/60 bg-teal/15 text-teal"
              : "border-border bg-surface-2 hover:border-teal/50 hover:text-teal",
          )}
        >
          <ThumbsUp className="size-4" fill={v === "good_fit" ? "currentColor" : "none"} />
          Good fit
        </button>
        <button
          type="button"
          aria-pressed={v === "not_fit"}
          disabled={pending}
          onClick={() => set(v === "not_fit" ? null : "not_fit", rating?.reason)}
          className={cn(
            pill,
            v === "not_fit"
              ? "border-coral/60 bg-coral/15 text-coral"
              : "border-border bg-surface-2 hover:border-coral/50 hover:text-coral",
          )}
        >
          <ThumbsDown className="size-4" fill={v === "not_fit" ? "currentColor" : "none"} />
          Not a fit
        </button>
      </div>
      {v === "not_fit" && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <span className="text-xs text-muted-foreground">Why? (optional)</span>
          {Object.entries(NOT_FIT_REASONS).map(([code, label]) => (
            <button
              key={code}
              type="button"
              aria-pressed={rating?.reason === code}
              disabled={pending}
              onClick={() => set("not_fit", rating?.reason === code ? null : code)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                rating?.reason === code
                  ? "border-coral/60 bg-coral/15 text-coral"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
