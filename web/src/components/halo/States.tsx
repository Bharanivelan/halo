import type { ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { ApiError } from "@/lib/halo-api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function errorText(e: unknown): { title: string; detail: string } {
  if (e instanceof ApiError) {
    const field = e.errors[0];
    return {
      title: e.title,
      detail: field ? `${field.field}: ${field.message}` : (e.detail ?? e.message),
    };
  }
  return { title: "Something went wrong", detail: e instanceof Error ? e.message : String(e) };
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const { title, detail } = errorText(error);
  return (
    <div
      className={cn("card-halo flex flex-col items-center gap-3 px-6 py-12 text-center", className)}
      role="alert"
    >
      <span className="grid size-11 place-items-center rounded-full bg-coral/15 text-coral">
        <AlertTriangle className="size-5" />
      </span>
      <div>
        <h3 className="font-semibold">{title}</h3>
        <p className="mt-1 max-w-md text-sm text-muted-foreground">{detail}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" className="rounded-xl" onClick={onRetry}>
          <RefreshCw />
          Try again
        </Button>
      )}
    </div>
  );
}

export function SectionTitle({
  children,
  right,
  className,
}: {
  children: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-center justify-between gap-3", className)}>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        {children}
      </h2>
      {right}
    </div>
  );
}

/** Small labelled meter (0–100) for fit / intent / confidence. */
export function Meter({
  value,
  color = "var(--gold)",
  className,
}: {
  value: number | null | undefined;
  color?: string;
  className?: string;
}) {
  const v = value == null ? 0 : Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-surface-2", className)}>
      <div
        className="h-full rounded-full transition-[width] duration-700"
        style={{ width: `${v}%`, background: color, boxShadow: `0 0 8px ${color}` }}
      />
    </div>
  );
}

export function MockBadge({ origin }: { origin: string | null | undefined }) {
  if (origin !== "mock") return null;
  return (
    <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-400">
      Sample data
    </span>
  );
}
