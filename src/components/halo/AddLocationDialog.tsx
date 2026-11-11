import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Loader2, MapPin, Search } from "lucide-react";
import { toast } from "sonner";
import { useCreateProperty, useGeocode, useReference } from "@/hooks/use-halo";
import type { GeocodeResult, Lifecycle, Offering } from "@/lib/halo-types";
import { OFFERING_LABEL } from "@/lib/halo-format";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";
import { errorText } from "./States";

function useDebounced<T>(v: T, ms = 350) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const t = setTimeout(() => setD(v), ms);
    return () => clearTimeout(t);
  }, [v, ms]);
  return d;
}

const OFFERINGS: Offering[] = ["corporate_rate", "mice", "long_stay", "fnb"];

export function AddLocationDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const navigate = useNavigate();
  const create = useCreateProperty();
  const { data: ref } = useReference();
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [q, setQ] = useState("");
  const [place, setPlace] = useState<GeocodeResult | null>(null);
  const [lifecycle, setLifecycle] = useState<Lifecycle>("operating");
  const [rooms, setRooms] = useState("");
  const [radius, setRadius] = useState(10);
  const [offerings, setOfferings] = useState<Offering[]>(["corporate_rate", "mice"]);
  const dq = useDebounced(q);
  const geo = useGeocode(place ? "" : dq);

  useEffect(() => {
    if (!open) {
      setName("");
      setBrand("");
      setQ("");
      setPlace(null);
      setRooms("");
      setRadius(10);
      create.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const submit = () => {
    if (!place) return;
    create.mutate(
      {
        name: name.trim(),
        brand: brand.trim() || null,
        address_line: place.label,
        locality: place.locality,
        city: place.city,
        state: place.state,
        postal_code: place.postal_code,
        country: place.country ?? "IN",
        location: { lat: place.lat, lng: place.lng },
        lifecycle,
        opening_date: null,
        is_hypothetical: false,
        rooms_count: rooms ? Number(rooms) : null,
        meeting_rooms_count: null,
        largest_meeting_capacity: null,
        banquet_capacity: null,
        restaurants_count: null,
        facilities: [],
        description: null,
        offerings: offerings.length ? offerings : ["corporate_rate"],
        target: {
          radius_km: radius,
          industries: [],
          employee_min: null,
          employee_max: null,
          notes: null,
        },
      },
      {
        onSuccess: (p) => {
          toast.success(`${p.name} pinned`, {
            description: "Run the agent to discover who's inside its halo.",
          });
          onOpenChange(false);
          void navigate({ to: "/p/$propertyId", params: { propertyId: p.id } });
        },
      },
    );
  };
  const err = create.error ? errorText(create.error) : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto rounded-2xl border-border bg-surface sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display">Pin a location</DialogTitle>
          <DialogDescription>
            Halo will look for companies inside this location's catchment.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="loc-name">Property name</Label>
              <Input
                id="loc-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Halo Suites Guindy"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="loc-brand">
                Brand <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input id="loc-brand" value={brand} onChange={(e) => setBrand(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="loc-addr">Address</Label>
            {place ? (
              <div className="flex items-start gap-2 rounded-xl border border-gold/40 bg-gold/5 p-3 text-sm">
                <MapPin className="mt-0.5 size-4 shrink-0 text-gold" />
                <div className="min-w-0 flex-1">
                  <div className="truncate">{place.label}</div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {place.lat.toFixed(5)}, {place.lng.toFixed(5)}
                  </div>
                </div>
                <button
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
                    id="loc-addr"
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    placeholder="Search an address or area, e.g. Guindy, Chennai"
                    className="pl-9"
                  />
                  {geo.isFetching && (
                    <Loader2 className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
                  )}
                </div>
                {!!geo.data?.length && (
                  <ul className="max-h-48 overflow-y-auto rounded-xl border border-border">
                    {geo.data.map((g, i) => (
                      <li key={i}>
                        <button
                          className="flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-surface-2"
                          onClick={() => setPlace(g)}
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
                    No matches. Try a nearby landmark or area name.
                  </p>
                )}
              </>
            )}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Status</Label>
              <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
                {(["operating", "pre_opening"] as const).map((l) => (
                  <button
                    key={l}
                    onClick={() => setLifecycle(l)}
                    className={cn(
                      "rounded-lg py-1.5 text-xs",
                      lifecycle === l ? "bg-surface font-medium shadow" : "text-muted-foreground",
                    )}
                  >
                    {l === "operating" ? "Operating" : "Pre-opening"}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="loc-rooms">
                Rooms <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="loc-rooms"
                type="number"
                min={0}
                value={rooms}
                onChange={(e) => setRooms(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <Label>Catchment radius</Label>
              <span className="font-mono text-gold">{radius} km</span>
            </div>
            <Slider
              min={1}
              max={50}
              step={1}
              value={[radius]}
              onValueChange={(v) => setRadius(v[0] ?? 10)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>What you sell</Label>
            <div className="flex flex-wrap gap-2">
              {OFFERINGS.map((o) => {
                const on = offerings.includes(o);
                return (
                  <button
                    key={o}
                    onClick={() =>
                      setOfferings(on ? offerings.filter((x) => x !== o) : [...offerings, o])
                    }
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs transition-colors",
                      on
                        ? "border-gold/50 bg-gold/15 text-gold"
                        : "border-border text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {ref?.offerings.find((x) => x.code === o)?.label ?? OFFERING_LABEL[o]}
                  </button>
                );
              })}
            </div>
          </div>
          {err && (
            <p
              role="alert"
              className="rounded-xl border border-coral/30 bg-coral/10 p-3 text-sm text-coral"
            >
              {err.detail}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="signature"
            disabled={!place || name.trim().length < 2 || create.isPending}
            onClick={submit}
          >
            {create.isPending && <Loader2 className="animate-spin" />}Pin location
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
