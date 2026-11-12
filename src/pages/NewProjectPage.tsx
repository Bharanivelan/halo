import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  Loader2,
  MapPin,
  Search,
  Sparkles,
  Target,
} from "lucide-react";
import { toast } from "sonner";
import { Explain, HaloRadar, errorText } from "@/components/halo";
import { CountryPicker } from "@/components/halo/CountryPicker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useCreateProperty, useGeocode, useMe, useReference } from "@/hooks/use-halo";
import { OFFERING_LABEL, dist, fromUnit, toUnit } from "@/lib/halo-format";
import { setLastProject } from "@/lib/halo-projects";
import type { CountryCode, GeocodeResult, Lifecycle, Offering, Region } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

const FALLBACK_REGIONS: Region[] = [
  {
    code: "US",
    label: "United States",
    currency: "USD",
    distance_unit: "mi",
    locale: "en-US",
    default_radius_km: 8.047,
  },
  {
    code: "IN",
    label: "India",
    currency: "INR",
    distance_unit: "km",
    locale: "en-IN",
    default_radius_km: 8,
  },
];
const OFFERINGS: Offering[] = ["corporate_rate", "mice", "long_stay", "fnb"];
const OFFERING_HINT: Record<Offering, string> = {
  corporate_rate: "Business travellers on a company rate",
  mice: "Meetings, conferences, offsites and events",
  long_stay: "Guests staying weeks or months, like relocations",
  fnb: "Team lunches, client dinners, catering",
};
const SIZES = [
  { key: "any", label: "Any size", min: null, max: null },
  { key: "small", label: "Small (10–200 staff)", min: 10, max: 200 },
  { key: "mid", label: "Medium (200–1,000)", min: 200, max: 1000 },
  { key: "large", label: "Large (1,000+)", min: 1000, max: null },
] as const;
const STEP_TITLES = ["Find your hotel", "About your hotel", "Who should we look for?"];

function useDebounced<T>(v: T, ms = 350) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const t = setTimeout(() => setD(v), ms);
    return () => clearTimeout(t);
  }, [v, ms]);
  return d;
}

function Chip({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={cn(
        "rounded-full border px-3 py-1.5 text-sm transition-colors",
        on
          ? "border-gold/50 bg-gold/15 text-gold"
          : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function NumberField({
  id,
  label,
  hint,
  value,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>
        {label} <span className="text-muted-foreground">(optional)</span>
      </Label>
      <Input
        id={id}
        type="number"
        inputMode="numeric"
        min={0}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

export function NewProjectPage() {
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const { data: me } = useMe();
  const { data: ref } = useReference();
  const create = useCreateProperty();
  const regions = ref?.regions?.length ? ref.regions : FALLBACK_REGIONS;

  const [step, setStep] = useState(0);
  const [country, setCountry] = useState<CountryCode>("US");
  const region = regions.find((r) => r.code === country) ?? FALLBACK_REGIONS[0]!;
  const unit = region.distance_unit;

  // Step 1
  const [name, setName] = useState("");
  const [q, setQ] = useState("");
  const [place, setPlace] = useState<GeocodeResult | null>(null);
  const [lifecycle, setLifecycle] = useState<Lifecycle>("operating");
  // Step 2
  const [rooms, setRooms] = useState("");
  const [meetingRooms, setMeetingRooms] = useState("");
  const [capacity, setCapacity] = useState("");
  const [offerings, setOfferings] = useState<Offering[]>(["corporate_rate", "mice"]);
  // Step 3
  const [radiusKm, setRadiusKm] = useState(region.default_radius_km);
  const [industries, setIndustries] = useState<string[]>([]);
  const [size, setSize] = useState<(typeof SIZES)[number]["key"]>("any");
  const [startAgent, setStartAgent] = useState(true);

  const dq = useDebounced(q);
  const geo = useGeocode(place ? "" : dq, country);

  // Default country from the server; reset location-dependent fields when the country changes.
  useEffect(() => {
    if (ref?.default_country) setCountry(ref.default_country);
  }, [ref?.default_country]);
  useEffect(() => {
    setPlace(null);
    setRadiusKm(region.default_radius_km);
  }, [country, region.default_radius_km]);

  const sizeRow = SIZES.find((s) => s.key === size) ?? SIZES[0];
  const canNext = step === 0 ? !!place && name.trim().length >= 2 : true;
  const canManage = me ? me.role !== "rep" : true;
  const n = (v: string) => (v.trim() ? Math.max(0, Math.round(Number(v))) : null);

  const summary = useMemo(
    () =>
      [
        `look within ${dist(radiusKm, unit)} of ${name.trim() || "your hotel"}`,
        industries.length
          ? `focus on ${industries.length} ${industries.length === 1 ? "industry" : "industries"}`
          : "consider every industry",
        sizeRow.key === "any" ? "any company size" : sizeRow.label.toLowerCase(),
      ].join(", "),
    [radiusKm, unit, name, industries.length, sizeRow],
  );

  const submit = () => {
    if (!place) return;
    create.mutate(
      {
        name: name.trim(),
        brand: null,
        address_line: place.label,
        locality: place.locality,
        city: place.city,
        state: place.state,
        postal_code: place.postal_code,
        country,
        location: { lat: place.lat, lng: place.lng },
        lifecycle,
        opening_date: null,
        is_hypothetical: false,
        rooms_count: n(rooms),
        meeting_rooms_count: n(meetingRooms),
        largest_meeting_capacity: n(capacity),
        banquet_capacity: null,
        restaurants_count: null,
        facilities: [],
        description: null,
        offerings: offerings.length ? offerings : ["corporate_rate"],
        target: {
          radius_km: Math.round(radiusKm * 1000) / 1000,
          industries,
          employee_min: sizeRow.min,
          employee_max: sizeRow.max,
          notes: null,
        },
        start_agent: startAgent,
      },
      {
        onSuccess: (p) => {
          setLastProject(p.id);
          if (p.started_job_id) {
            toast.success(`${p.name} is set up`, {
              description: "The agent has started. Watch it work, or come back in a few minutes.",
            });
            void navigate({
              to: "/p/$propertyId/agent/$jobId",
              params: { propertyId: p.id, jobId: p.started_job_id },
            });
          } else {
            toast.success(`${p.name} is set up`);
            void navigate({ to: "/p/$propertyId", params: { propertyId: p.id } });
          }
        },
      },
    );
  };
  const err = create.error ? errorText(create.error) : null;

  if (!canManage) {
    return (
      <div className="mx-auto max-w-xl card-halo p-8 text-center">
        <h1 className="text-xl font-bold">Only managers can list a hotel</h1>
        <p className="mt-2 text-muted-foreground">
          Ask your manager or administrator to add the hotel and share it with you.
        </p>
        <Button className="mt-6 rounded-xl" variant="outline" asChild>
          <Link to="/">Back to projects</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Projects
        </Link>
        <h1 className="mt-2 text-[32px] font-bold leading-tight">List a new hotel</h1>
        <p className="mt-1 text-muted-foreground">
          Three quick steps. Then Halo's AI agent starts finding businesses near your hotel that
          could fill rooms and event space.
        </p>
      </div>

      <ol className="mb-6 grid grid-cols-3 gap-2" aria-label="Setup steps">
        {STEP_TITLES.map((t, i) => (
          <li
            key={t}
            className={cn(
              "flex items-center gap-2 rounded-xl border px-3 py-2 text-sm",
              i === step
                ? "border-gold/50 bg-gold/10 text-foreground"
                : i < step
                  ? "border-teal/40 text-teal"
                  : "border-border text-muted-foreground",
            )}
            aria-current={i === step ? "step" : undefined}
          >
            <span
              className={cn(
                "grid size-6 shrink-0 place-items-center rounded-full text-xs",
                i < step ? "bg-teal/20" : i === step ? "bg-gold/20 text-gold" : "bg-surface-2",
              )}
            >
              {i < step ? <Check className="size-3.5" /> : i + 1}
            </span>
            <span className="hidden truncate sm:inline">{t}</span>
          </li>
        ))}
      </ol>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="card-halo p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={reduce ? false : { opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: reduce ? 1 : 0, x: reduce ? 0 : -12 }}
              transition={{ duration: 0.2 }}
              className="space-y-5"
            >
              {step === 0 && (
                <>
                  <div className="space-y-1.5">
                    <Label>Which country is the hotel in?</Label>
                    <CountryPicker regions={regions} value={country} onChange={setCountry} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="hotel-name">Hotel name</Label>
                    <Input
                      id="hotel-name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={
                        country === "US"
                          ? "e.g. Marriott Downtown Austin"
                          : country === "IN"
                            ? "e.g. Hyatt Regency Chennai"
                            : "Your hotel's name"
                      }
                      autoFocus
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="hotel-addr">Where is it?</Label>
                    {place ? (
                      <div className="flex items-start gap-2 rounded-xl border border-gold/40 bg-gold/5 p-3 text-sm">
                        <MapPin className="mt-0.5 size-4 shrink-0 text-gold" />
                        <div className="min-w-0 flex-1">{place.label}</div>
                        <button
                          type="button"
                          className="text-xs text-gold hover:underline"
                          onClick={() => setPlace(null)}
                        >
                          Change
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="relative">
                          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            id="hotel-addr"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                            placeholder={
                              country === "US"
                                ? "Street address or area, e.g. 701 E 11th St, Austin"
                                : country === "IN"
                                  ? "Street address or area, e.g. Guindy, Chennai"
                                  : "Street address, area or landmark"
                            }
                            className="pl-9"
                          />
                          {geo.isFetching && (
                            <Loader2 className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
                          )}
                        </div>
                        {!!geo.data?.length && (
                          <ul className="max-h-56 overflow-y-auto rounded-xl border border-border">
                            {geo.data.map((g, i) => (
                              <li key={i}>
                                <button
                                  type="button"
                                  className="flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-surface-2"
                                  onClick={() => {
                                    setPlace(g);
                                    if (!name.trim()) {
                                      const first = g.label.split(",")[0]?.trim() ?? "";
                                      if (first && !/^\d/.test(first)) setName(first);
                                    }
                                  }}
                                >
                                  <MapPin className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                                  <span className="line-clamp-2">{g.label}</span>
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                        {geo.data && !geo.data.length && dq.length >= 3 && (
                          <p className="text-xs text-muted-foreground">
                            No matches in {region.label}. Try the street address, a landmark or the
                            neighbourhood name.
                          </p>
                        )}
                        {geo.error && (
                          <p className="text-xs text-coral">{errorText(geo.error).detail}</p>
                        )}
                      </>
                    )}
                    <p className="text-xs text-muted-foreground">
                      We use this pin as the centre of the search.
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Is the hotel open yet?</Label>
                    <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
                      {(["operating", "pre_opening"] as const).map((l) => (
                        <button
                          key={l}
                          type="button"
                          onClick={() => setLifecycle(l)}
                          className={cn(
                            "rounded-lg py-2 text-sm",
                            lifecycle === l
                              ? "bg-surface font-medium shadow"
                              : "text-muted-foreground",
                          )}
                        >
                          {l === "operating" ? "Yes, it's open" : "Opening soon"}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {step === 1 && (
                <>
                  <p className="text-sm text-muted-foreground">
                    This helps the agent judge which businesses are a good match. Skip anything you
                    don't know.
                  </p>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <NumberField
                      id="rooms"
                      label="Guest rooms"
                      hint="Bigger hotels can take bigger group bookings."
                      value={rooms}
                      onChange={setRooms}
                    />
                    <NumberField
                      id="meeting"
                      label="Meeting rooms"
                      hint="Lets us suggest meetings and events."
                      value={meetingRooms}
                      onChange={setMeetingRooms}
                    />
                    <NumberField
                      id="capacity"
                      label="Largest room holds"
                      hint="Number of people in your biggest space."
                      value={capacity}
                      onChange={setCapacity}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="flex items-center gap-1">
                      What do you want to sell? <Explain k="offerings" />
                    </Label>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {OFFERINGS.map((o) => {
                        const on = offerings.includes(o);
                        return (
                          <button
                            key={o}
                            type="button"
                            aria-pressed={on}
                            onClick={() =>
                              setOfferings(
                                on ? offerings.filter((x) => x !== o) : [...offerings, o],
                              )
                            }
                            className={cn(
                              "flex items-start gap-3 rounded-xl border p-3 text-left transition-colors",
                              on
                                ? "border-gold/50 bg-gold/10"
                                : "border-border hover:border-gold/30",
                            )}
                          >
                            <span
                              className={cn(
                                "mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border",
                                on
                                  ? "border-gold bg-gold text-primary-foreground"
                                  : "border-border",
                              )}
                            >
                              {on && <Check className="size-3.5" />}
                            </span>
                            <span>
                              <span className="block font-medium">
                                {ref?.offerings.find((x) => x.code === o)?.label ??
                                  OFFERING_LABEL[o]}
                              </span>
                              <span className="block text-xs text-muted-foreground">
                                {OFFERING_HINT[o]}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}

              {step === 2 && (
                <>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <Label className="flex items-center gap-1">
                        How far should we look? <Explain k="radius" />
                      </Label>
                      <span className="font-mono text-gold">{dist(radiusKm, unit)}</span>
                    </div>
                    <Slider
                      min={1}
                      max={unit === "mi" ? 30 : 50}
                      step={unit === "mi" ? 0.5 : 1}
                      value={[Number(toUnit(radiusKm, unit).toFixed(1))]}
                      onValueChange={(v) => setRadiusKm(fromUnit(v[0] ?? 5, unit))}
                      aria-label="Search distance"
                    />
                    <p className="text-xs text-muted-foreground">
                      Start small: nearby companies book the most. You can widen it later.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>
                      Which industries?{" "}
                      <span className="text-muted-foreground">(leave empty for all)</span>
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      {(ref?.industries ?? []).map((ind) => (
                        <Chip
                          key={ind.code}
                          on={industries.includes(ind.code)}
                          onClick={() =>
                            setIndustries(
                              industries.includes(ind.code)
                                ? industries.filter((x) => x !== ind.code)
                                : [...industries, ind.code],
                            )
                          }
                        >
                          {ind.label}
                        </Chip>
                      ))}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Company size</Label>
                    <div className="flex flex-wrap gap-2">
                      {SIZES.map((s) => (
                        <Chip key={s.key} on={size === s.key} onClick={() => setSize(s.key)}>
                          {s.label}
                        </Chip>
                      ))}
                    </div>
                  </div>
                  <label className="flex items-start gap-3 rounded-xl border border-violet/30 bg-violet/5 p-4">
                    <Switch
                      checked={startAgent}
                      onCheckedChange={setStartAgent}
                      aria-label="Start the agent now"
                    />
                    <span className="text-sm">
                      <span className="flex items-center gap-1 font-medium">
                        Start the AI agent right away <Explain k="agent" />
                      </span>
                      <span className="mt-0.5 block text-muted-foreground">
                        It will look at up to 50 nearby businesses and spend at most $2 of AI
                        credit. It usually takes a few minutes, and you can stop it at any time.
                      </span>
                    </span>
                  </label>
                </>
              )}

              {err && (
                <p
                  role="alert"
                  className="rounded-xl border border-coral/30 bg-coral/10 p-3 text-sm text-coral"
                >
                  {err.detail}
                </p>
              )}
            </motion.div>
          </AnimatePresence>

          <div className="mt-8 flex items-center justify-between gap-3 border-t border-border pt-5">
            <Button
              variant="ghost"
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0 || create.isPending}
            >
              <ArrowLeft />
              Back
            </Button>
            {step < 2 ? (
              <Button
                variant="signature"
                className="rounded-xl"
                disabled={!canNext}
                onClick={() => setStep((s) => s + 1)}
              >
                Next
                <ArrowRight />
              </Button>
            ) : (
              <Button
                variant="signature"
                className="rounded-xl"
                disabled={!place || create.isPending}
                onClick={submit}
              >
                {create.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                {startAgent ? "Create project and start agent" : "Create project"}
              </Button>
            )}
          </div>
        </div>

        <aside className="card-halo h-fit p-5 lg:sticky lg:top-24">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Building2 className="size-4 text-gold" />
            {name.trim() || "Your hotel"}
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {place ? [place.locality, place.city].filter(Boolean).join(", ") : region.label}
          </p>
          <div className="mt-4">
            {place ? (
              <HaloRadar
                center={{ lat: place.lat, lng: place.lng }}
                radiusKm={radiusKm}
                unit={unit}
                points={[]}
                className="mx-auto max-w-[240px]"
              />
            ) : (
              <div className="mx-auto grid aspect-square max-w-[240px] place-items-center rounded-full border border-dashed border-border text-center text-xs text-muted-foreground">
                Pick an address to
                <br />
                see the search area
              </div>
            )}
          </div>
          <div className="mt-4 rounded-xl bg-surface-2 p-3 text-xs leading-relaxed text-muted-foreground">
            <div className="mb-1 flex items-center gap-1.5 font-medium text-foreground">
              <Target className="size-3.5 text-violet" />
              The agent will
            </div>
            {summary}.
          </div>
        </aside>
      </div>
    </div>
  );
}
