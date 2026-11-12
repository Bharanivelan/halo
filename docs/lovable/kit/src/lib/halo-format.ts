/** Display helpers for Halo. Never invent values: null/undefined → "—". */
import type { DistanceUnit, Offering, Tier } from "./halo-types";

const DASH = "—";

export const usd = (n?: number | null) =>
  n == null ? DASH : `$${n < 1 && n > 0 ? n.toFixed(3) : n.toFixed(2)}`;

/** Indian grouping for INR (₹4,50,000); other currencies use their locale default. */
export function money(n?: number | null, currency = "USD") {
  if (n == null) return DASH;
  const locale = currency === "INR" ? "en-IN" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(n);
}

export const num = (n?: number | null) =>
  n == null ? DASH : new Intl.NumberFormat("en-US").format(n);

/** Distances are stored in km; show them in the project's unit (D-39). */
export const KM_PER_MILE = 1.609344;
export const toUnit = (km: number, unit: DistanceUnit) => (unit === "mi" ? km / KM_PER_MILE : km);
export const fromUnit = (v: number, unit: DistanceUnit) => (unit === "mi" ? v * KM_PER_MILE : v);
export function dist(kmVal?: number | null, unit: DistanceUnit = "mi", digits = 1) {
  if (kmVal == null) return DASH;
  const v = toUnit(kmVal, unit);
  return `${Number(v.toFixed(digits))} ${unit}`;
}
/** @deprecated use dist(n, unit) */
export const km = (n?: number | null) => dist(n, "km");
export const score = (n?: number | null) => (n == null ? DASH : Math.round(n).toString());
export const pct = (n?: number | null) => (n == null ? DASH : `${Math.round(n * 100)}%`);

export function ago(iso?: string | null) {
  if (!iso) return DASH;
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  const d = Math.floor(s / 86400);
  return d < 30
    ? `${d}d ago`
    : new Date(iso).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
}
export const ageDays = (d?: number | null) => (d == null ? "" : d === 0 ? "today" : `${d}d`);
export const dateTime = (iso?: string | null) =>
  iso
    ? new Date(iso).toLocaleString(undefined, {
        day: "numeric",
        month: "short",
        hour: "numeric",
        minute: "2-digit",
      })
    : DASH;
export const date = (iso?: string | null) =>
  iso
    ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
    : DASH;

export function duration(start?: string | null, end?: string | null) {
  if (!start) return DASH;
  const s = Math.max(
    0,
    ((end ? new Date(end) : new Date()).getTime() - new Date(start).getTime()) / 1000,
  );
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

export const TIER_LABEL: Record<Tier, string> = { A: "Hot", B: "Warm", C: "Cool" };
export const OFFERING_LABEL: Record<Offering, string> = {
  corporate_rate: "Corporate stays",
  mice: "Meetings & events",
  long_stay: "Long stays",
  fnb: "Food & beverage",
};
/** Plain-language names for the agent's steps (D-41). */
export const STAGE_LABEL: Record<string, string> = {
  plan: "Getting ready",
  discover: "Finding nearby businesses",
  resolve: "Removing duplicates",
  classify: "Keeping the relevant ones",
  research: "Reading their websites",
  signals: "Looking for buying signals",
  score: "Scoring and fact-checking",
};
export const firstName = (full?: string | null) => (full ?? "").trim().split(/\s+/)[0] || "there";
export function greeting(d = new Date()) {
  const h = d.getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}
