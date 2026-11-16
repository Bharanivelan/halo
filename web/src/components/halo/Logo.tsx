import { useId } from "react";
import { cn } from "@/lib/utils";

export function LogoMark({ size = 28, className }: { size?: number; className?: string }) {
  const id = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} aria-hidden>
      <defs>
        <linearGradient id={`${id}g`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--gold)" />
          <stop offset="100%" stopColor="var(--teal)" />
        </linearGradient>
        <filter id={`${id}f`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.6" />
        </filter>
      </defs>
      <circle cx="16" cy="16" r="10" fill="none" stroke={`url(#${id}g)`} strokeWidth="3.5" filter={`url(#${id}f)`} opacity="0.8" />
      <circle cx="16" cy="16" r="10" fill="none" stroke={`url(#${id}g)`} strokeWidth="3" />
      <circle cx="16" cy="16" r="2.2" fill="var(--gold)" />
    </svg>
  );
}

export function Logo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <LogoMark />
      {!compact && (
        <div className="flex flex-col leading-none">
          <span className="font-display text-xl font-bold tracking-tight">halo</span>
          <span className="mt-0.5 text-[11px] text-muted-foreground">AI sales agent for hotels</span>
        </div>
      )}
    </div>
  );
}
