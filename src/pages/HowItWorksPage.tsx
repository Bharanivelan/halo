import { Link } from "@tanstack/react-router";
import {
  BadgeCheck,
  BookOpen,
  Brain,
  Copy,
  FlaskConical,
  Gauge,
  Mail,
  MapPinned,
  Radar,
  ShieldCheck,
  Sparkles,
  Users,
  Wallet,
} from "lucide-react";
import { useReference } from "@/hooks/use-halo";
import { GLOSSARY, type GlossaryKey } from "@/lib/halo-glossary";
import { cn } from "@/lib/utils";
import { PageHeader } from "./PlaceholderPage";

const STEPS = [
  {
    icon: MapPinned,
    title: "Finds businesses near your hotel",
    text: "Looks up every office, company and organisation inside your search area on public maps (OpenStreetMap), plus any list you upload.",
    ai: false,
  },
  {
    icon: Copy,
    title: "Removes duplicates",
    text: "The same company often appears more than once. Halo merges them so you see each business once.",
    ai: false,
  },
  {
    icon: Radar,
    title: "Keeps the relevant ones",
    text: "Drops places that won't book hotel rooms, like shops and houses, and keeps offices, factories, hospitals and colleges.",
    ai: true,
  },
  {
    icon: BookOpen,
    title: "Reads their websites",
    text: "The AI visits each company's website to learn what they do, how big they are and where they are based.",
    ai: true,
  },
  {
    icon: Sparkles,
    title: "Looks for buying signals",
    text: "Searches the news for recent hiring, new offices, expansions and events: signs they will need rooms or event space soon.",
    ai: true,
  },
  {
    icon: Gauge,
    title: "Scores and fact-checks",
    text: "Gives each business a score from 0 to 100 and ranks them Hot, Warm or Cool. Every fact must match the source page word for word, or it is marked “Not verified”.",
    ai: false,
  },
  {
    icon: Users,
    title: "Recommends who to contact",
    text: "Suggests which roles to approach, such as HR, travel or admin, based on the company's size.",
    ai: false,
  },
  {
    icon: Mail,
    title: "Drafts your pitch",
    text: "On request, writes a first introduction email using only verified facts. You review and edit before sending.",
    ai: true,
  },
];

const TERMS: GlossaryKey[] = [
  "score",
  "tier",
  "fit",
  "intent",
  "confidence",
  "signal",
  "evidence",
  "budget",
];

const PROMISES = [
  {
    icon: ShieldCheck,
    title: "No made-up facts",
    text: "If Halo can't point to a source, it says so. Guesses are labelled as estimates.",
  },
  {
    icon: Wallet,
    title: "You control the spend",
    text: "Every run has a spending cap. The first automatic run is capped at $2.",
  },
  {
    icon: BadgeCheck,
    title: "You stay in charge",
    text: "The agent suggests; you decide who to contact and what to send.",
  },
];

export function HowItWorksPage() {
  const { data: ref } = useReference();
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="How Halo's AI works"
        sub="A plain-English tour of what the agent does for each hotel, and how to read its results."
      />

      <section className="card-halo p-6">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-medium">Right now on this server:</span>
          <span
            className={cn(
              "rounded-full border px-2.5 py-0.5",
              ref?.llm_configured
                ? "border-teal/40 bg-teal/10 text-teal"
                : "border-coral/40 bg-coral/10 text-coral",
            )}
          >
            AI research {ref?.llm_configured ? "on" : "off"}
          </span>
          <span
            className={cn(
              "rounded-full border px-2.5 py-0.5",
              ref?.search_configured
                ? "border-teal/40 bg-teal/10 text-teal"
                : "border-border text-muted-foreground",
            )}
          >
            News and web search {ref?.search_configured ? "on" : "off"}
          </span>
        </div>
        {ref && !ref.llm_configured && (
          <p className="mt-2 text-sm text-muted-foreground">
            Without AI, Halo still finds and maps businesses and scores them on distance and
            industry, but it can't read websites or spot signals.
          </p>
        )}
      </section>

      <h2 className="mt-10 text-xl font-bold">What happens when the agent runs</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        It happens automatically when you list a hotel, and again whenever you press{" "}
        <span className="text-foreground">Run agent</span>. Steps marked{" "}
        <span className="text-violet">AI</span> use the AI model; the others are plain rules anyone
        can check.
      </p>
      <ol className="mt-5 space-y-3">
        {STEPS.map((s, i) => (
          <li key={s.title} className="card-halo flex gap-4 p-4">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-surface-2 text-gold">
              <s.icon className="size-5" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2 font-medium">
                <span className="font-mono text-xs text-muted-foreground">{i + 1}</span>
                {s.title}
                {s.ai && (
                  <span className="rounded-full bg-violet/15 px-2 py-0.5 text-[11px] text-violet">
                    AI
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>

      <h2 className="mt-12 text-xl font-bold">Reading the results</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {TERMS.map((k) => (
          <div key={k} className="card-halo p-4">
            <div className="font-medium">{GLOSSARY[k].title}</div>
            <p className="mt-1 text-sm text-muted-foreground">{GLOSSARY[k].text}</p>
          </div>
        ))}
      </div>

      <h2 className="mt-12 text-xl font-bold">Our promises</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {PROMISES.map((p) => (
          <div key={p.title} className="card-halo p-4">
            <p.icon className="size-5 text-teal" />
            <div className="mt-2 font-medium">{p.title}</div>
            <p className="mt-1 text-sm text-muted-foreground">{p.text}</p>
          </div>
        ))}
      </div>

      <section className="mt-12 card-halo border-violet/30 p-6">
        <div className="flex flex-wrap items-center gap-2">
          <FlaskConical className="size-5 text-violet" />
          <h2 className="text-xl font-bold">Coming soon: the agent improvement lab</h2>
          <span className="rounded-full border border-violet/40 bg-violet/10 px-2 py-0.5 text-xs text-violet">
            Coming soon
          </span>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          We will regularly test the agent against a set of companies whose correct answers we
          already know: their industry, size and real buying signals. A research tool from Google
          (Harness²) then tries better instructions and safety checks for the agent, and we keep
          only the changes that make it measurably more accurate. The AI model itself stays the
          same; it just gets better guidance.
        </p>
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          {[
            { icon: Brain, t: "Same AI, smarter instructions" },
            { icon: Gauge, t: "Accuracy shown as a version number on this page" },
            { icon: ShieldCheck, t: "Runs on our side only: your data isn't used" },
          ].map((x) => (
            <div key={x.t} className="flex items-center gap-2 rounded-xl bg-surface-2 p-3">
              <x.icon className="size-4 shrink-0 text-violet" />
              {x.t}
            </div>
          ))}
        </div>
      </section>

      <p className="mt-10 text-center text-sm text-muted-foreground">
        Want results in your own tools?{" "}
        <Link to="/connectors" className="text-gold hover:underline">
          See connectors
        </Link>
        .
      </p>
    </div>
  );
}
