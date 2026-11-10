import { cn } from "@/lib/utils";

/** Decorative animated concentric rings. */
export function HaloRings({ size = 200, rings = 3, color = "var(--gold)", className }: { size?: number; rings?: number; color?: string; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className={cn("pointer-events-none", className)} aria-hidden>
      <circle cx="50" cy="50" r="48" fill={color} opacity="0.05" />
      {[0.33, 0.66, 1].map((s) => (
        <circle key={s} cx="50" cy="50" r={48 * s} fill="none" stroke={color} strokeOpacity="0.15" strokeWidth="0.4" />
      ))}
      {Array.from({ length: rings }).map((_, i) => (
        <circle
          key={i}
          cx="50" cy="50" r="48" fill="none" stroke={color} strokeWidth="0.8"
          className="anim-halo-ring"
          style={{ animationDelay: `${(i * 4.5) / rings}s` }}
        />
      ))}
      <circle cx="50" cy="50" r="3" fill={color} />
    </svg>
  );
}
