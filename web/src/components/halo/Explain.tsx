import type { ReactNode } from "react";
import { CircleHelp } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { GLOSSARY, type GlossaryKey } from "@/lib/halo-glossary";
import { cn } from "@/lib/utils";

/** A small "?" next to a term that opens a plain-language explanation. */
export function Explain({ k, className }: { k: GlossaryKey; className?: string }) {
  const g = GLOSSARY[k];
  return (
    <Popover>
      <PopoverTrigger
        type="button"
        aria-label={`What is ${g.title}?`}
        onClick={(e) => e.stopPropagation()}
        className={cn(
          "inline-grid size-4 shrink-0 place-items-center rounded-full align-middle text-muted-foreground transition-colors hover:text-gold focus-visible:text-gold",
          className,
        )}
      >
        <CircleHelp className="size-3.5" />
      </PopoverTrigger>
      <PopoverContent
        className="w-72 rounded-xl border-border bg-surface text-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="font-medium">{g.title}</div>
        <p className="mt-1 leading-relaxed text-muted-foreground">{g.text}</p>
      </PopoverContent>
    </Popover>
  );
}

/** A label with an inline explanation. */
export function Term({ k, children }: { k: GlossaryKey; children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1">
      {children ?? GLOSSARY[k].title}
      <Explain k={k} />
    </span>
  );
}
