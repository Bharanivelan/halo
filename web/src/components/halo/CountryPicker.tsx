import { useState } from "react";
import { Check, ChevronsUpDown, Globe2 } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import type { Region } from "@/lib/halo-types";
import { cn } from "@/lib/utils";

/** Flag emoji from an ISO country code (shows letters on systems without flag glyphs). */
export const flag = (code: string) =>
  String.fromCodePoint(...[...code.toUpperCase()].map((c) => 127397 + c.charCodeAt(0)));

const unitText = (r: Region) =>
  `Prices in ${r.currency} · distances in ${r.distance_unit === "mi" ? "miles" : "kilometres"}`;

/**
 * Any country (D-43). The first `pinned` markets get quick buttons; every other country is in a
 * searchable list. The server returns pinned markets first.
 */
export function CountryPicker({
  regions,
  value,
  onChange,
  pinned = 2,
}: {
  regions: Region[];
  value: string;
  onChange: (code: string) => void;
  pinned?: number;
}) {
  const [open, setOpen] = useState(false);
  const quick = regions.slice(0, pinned);
  const current = regions.find((r) => r.code === value);
  const isOther = !!current && !quick.some((r) => r.code === value);

  return (
    <div className="space-y-2">
      <div className="grid gap-2 sm:grid-cols-3">
        {quick.map((r) => (
          <button
            key={r.code}
            type="button"
            onClick={() => onChange(r.code)}
            aria-pressed={value === r.code}
            className={cn(
              "flex items-center gap-3 rounded-xl border p-3 text-left transition-colors",
              value === r.code ? "border-gold/50 bg-gold/10" : "border-border hover:border-gold/30",
            )}
          >
            <span className="text-2xl" aria-hidden>
              {flag(r.code)}
            </span>
            <span className="min-w-0">
              <span className="block truncate font-medium">{r.label}</span>
              <span className="block truncate text-xs text-muted-foreground">{r.currency}</span>
            </span>
          </button>
        ))}
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger
            type="button"
            role="combobox"
            aria-expanded={open}
            className={cn(
              "flex items-center gap-3 rounded-xl border p-3 text-left transition-colors",
              isOther ? "border-gold/50 bg-gold/10" : "border-border hover:border-gold/30",
            )}
          >
            <span className="text-2xl" aria-hidden>
              {isOther && current ? flag(current.code) : <Globe2 className="size-6 text-gold" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">
                {isOther && current ? current.label : "Another country"}
              </span>
              <span className="block truncate text-xs text-muted-foreground">
                {isOther && current ? current.currency : "Search all countries"}
              </span>
            </span>
            <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" />
          </PopoverTrigger>
          <PopoverContent className="w-72 rounded-xl border-border bg-surface p-0" align="end">
            <Command>
              <CommandInput placeholder="Type a country…" />
              <CommandList className="max-h-72">
                <CommandEmpty>No country found.</CommandEmpty>
                <CommandGroup>
                  {regions.map((r) => (
                    <CommandItem
                      key={r.code}
                      value={`${r.label} ${r.code}`}
                      onSelect={() => {
                        onChange(r.code);
                        setOpen(false);
                      }}
                    >
                      <span aria-hidden>{flag(r.code)}</span>
                      <span className="flex-1 truncate">{r.label}</span>
                      {value === r.code ? (
                        <Check className="size-4" />
                      ) : (
                        <span className="text-xs text-muted-foreground">{r.currency}</span>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
      {current && <p className="text-xs text-muted-foreground">{unitText(current)}</p>}
    </div>
  );
}
