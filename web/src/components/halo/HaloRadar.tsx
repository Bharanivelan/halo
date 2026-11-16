import { useId } from "react";
import type { DistanceUnit, GeoPoint, MapPoint, Tier } from "@/lib/halo-types";
import { dist } from "@/lib/halo-format";
import { cn } from "@/lib/utils";

export const TIER_COLOR: Record<Tier | "none", string> = {
  A: "var(--gold)",
  B: "var(--teal)",
  C: "var(--slate)",
  none: "var(--muted-foreground)",
};

/** Local equirectangular projection: km east/north of the centre. Accurate enough inside a 50 km halo. */
export function offsetKm(center: GeoPoint, p: { lat: number; lng: number }) {
  const kx = 111.32 * Math.cos((center.lat * Math.PI) / 180);
  return { x: (p.lng - center.lng) * kx, y: (p.lat - center.lat) * 110.57 };
}

/**
 * The signature "halo" view: a location at the centre, its catchment rings, and every prospect
 * plotted at its true bearing and distance. Pure SVG, deterministic (SSR-safe).
 */
export function HaloRadar({
  center,
  radiusKm,
  points = [],
  size,
  sweep = true,
  labels = true,
  selectedId,
  onSelect,
  className,
  unit = "mi",
}: {
  center: GeoPoint;
  radiusKm: number;
  points?: MapPoint[] | undefined;
  size?: number;
  sweep?: boolean;
  labels?: boolean;
  selectedId?: string | null | undefined;
  onSelect?: ((p: MapPoint) => void) | undefined;
  className?: string;
  unit?: DistanceUnit;
}) {
  const id = useId().replace(/:/g, "");
  const R = 92;
  const scale = R / Math.max(radiusKm, 0.5);
  const plotted = points
    .filter((p) => p.status !== "dismissed")
    .map((p) => {
      const o = offsetKm(center, p);
      const d = Math.hypot(o.x, o.y);
      const k = d * scale > R ? R / (d * scale) : 1; // clamp strays to the edge
      return { ...p, cx: o.x * scale * k, cy: -o.y * scale * k };
    })
    // Hot prospects drawn last so they sit on top.
    .sort((a, b) => (a.tier ?? "Z").localeCompare(b.tier ?? "Z"))
    .reverse();

  return (
    <svg
      viewBox="-100 -100 200 200"
      width={size}
      height={size}
      className={cn("block aspect-square w-full select-none", className)}
      role="img"
      aria-label={`${plotted.length} prospects within ${dist(radiusKm, unit)}`}
    >
      <defs>
        <radialGradient id={`${id}bg`}>
          <stop offset="0%" stopColor="var(--gold)" stopOpacity="0.14" />
          <stop offset="60%" stopColor="var(--violet)" stopOpacity="0.04" />
          <stop offset="100%" stopColor="var(--violet)" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}sw`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--gold)" stopOpacity="0" />
          <stop offset="100%" stopColor="var(--gold)" stopOpacity="0.28" />
        </linearGradient>
      </defs>

      <circle r={R + 6} fill={`url(#${id}bg)`} />
      {[1 / 3, 2 / 3, 1].map((f) => (
        <g key={f}>
          <circle
            r={R * f}
            fill="none"
            stroke="var(--foreground)"
            strokeOpacity={f === 1 ? 0.18 : 0.08}
            strokeWidth="0.4"
            strokeDasharray={f === 1 ? undefined : "1.2 1.6"}
          />
          {labels && (
            <text
              x={2}
              y={-R * f - 1.5}
              fontSize="4"
              fill="var(--muted-foreground)"
              fontFamily="var(--font-mono)"
            >
              {dist(radiusKm * f, unit, radiusKm * f < 10 ? 1 : 0)}
            </text>
          )}
        </g>
      ))}
      <line
        x1={-R}
        x2={R}
        y1={0}
        y2={0}
        stroke="var(--foreground)"
        strokeOpacity="0.05"
        strokeWidth="0.3"
      />
      <line
        y1={-R}
        y2={R}
        x1={0}
        x2={0}
        stroke="var(--foreground)"
        strokeOpacity="0.05"
        strokeWidth="0.3"
      />
      {labels && (
        <text
          x={0}
          y={-R - 2.5}
          fontSize="4"
          textAnchor="middle"
          fill="var(--muted-foreground)"
          fontFamily="var(--font-mono)"
        >
          N
        </text>
      )}

      {sweep && (
        <g className="anim-radar-sweep">
          <path
            d={`M0 0 L${R} 0 A${R} ${R} 0 0 0 ${R * Math.cos(-0.7)} ${R * Math.sin(-0.7)} Z`}
            fill={`url(#${id}sw)`}
          />
          <line
            x1="0"
            y1="0"
            x2={R}
            y2="0"
            stroke="var(--gold)"
            strokeOpacity="0.55"
            strokeWidth="0.5"
          />
        </g>
      )}

      {plotted.map((p, i) => {
        const color = TIER_COLOR[p.tier ?? "none"];
        const big = p.tier === "A";
        const sel = p.id === selectedId;
        return (
          <g
            key={p.id}
            onClick={onSelect ? () => onSelect(p) : undefined}
            className={onSelect ? "cursor-pointer" : undefined}
          >
            <title>{`${p.name}${p.tier ? ` · Tier ${p.tier}` : ""}`}</title>
            {big && (
              <circle
                cx={p.cx}
                cy={p.cy}
                fill="none"
                stroke={color}
                strokeWidth="0.5"
                className="anim-blip"
                style={{ animationDelay: `${(i % 9) * 0.27}s` }}
              />
            )}
            {onSelect && <circle cx={p.cx} cy={p.cy} r={5} fill="transparent" />}
            <circle
              cx={p.cx}
              cy={p.cy}
              r={sel ? 3.4 : big ? 2.2 : 1.5}
              fill={color}
              stroke={sel ? "var(--foreground)" : "none"}
              strokeWidth="0.6"
              style={{ filter: `drop-shadow(0 0 ${big ? 2 : 1}px ${color})` }}
            />
          </g>
        );
      })}

      <circle
        r="5"
        fill="var(--gold)"
        opacity="0.18"
        className="anim-halo-pulse"
        style={{ transformBox: "fill-box", transformOrigin: "center" }}
      />
      <circle
        r="3"
        fill="var(--gold)"
        stroke="var(--background)"
        strokeWidth="1"
        style={{ filter: "drop-shadow(0 0 3px var(--gold))" }}
      />
    </svg>
  );
}

export function RadarLegend({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground",
        className,
      )}
    >
      {(["A", "B", "C"] as const).map((t) => (
        <span key={t} className="inline-flex items-center gap-1.5">
          <span
            className="size-2 rounded-full"
            style={{ background: TIER_COLOR[t], boxShadow: `0 0 6px ${TIER_COLOR[t]}` }}
          />
          {t === "A" ? "Hot" : t === "B" ? "Warm" : "Cool"}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-muted-foreground" />
        Not scored
      </span>
    </div>
  );
}
