import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  Building2,
  CalendarClock,
  MapPin,
  MoreHorizontal,
  Plus,
  Search,
  Sparkles,
  Target,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  AgentPulse,
  ErrorState,
  Explain,
  HaloRadar,
  RadarLegend,
  errorText,
} from "@/components/halo";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  isJobActive,
  useAccountsMap,
  useDeleteProperty,
  useMe,
  useProperties,
  useRuns,
} from "@/hooks/use-halo";
import { ago, date, dist, firstName, greeting } from "@/lib/halo-format";
import { getLastProject, setLastProject } from "@/lib/halo-projects";
import type { JobSummary, PropertySummary } from "@/lib/halo-types";
import { PageHeader } from "./PlaceholderPage";

/** One plain-English line about where the agent is for this hotel. */
function statusLine(p: PropertySummary, run: JobSummary | undefined) {
  if (run) return { text: `Agent is working: ${Math.round(run.progress * 100)}% done`, live: true };
  const j = p.latest_job;
  if (!j) return { text: "The agent hasn't searched yet", live: false };
  switch (j.status) {
    case "completed":
    case "completed_with_errors":
      return {
        text: `Found ${p.account_count} ${p.account_count === 1 ? "business" : "businesses"} · ${ago(j.finished_at)}`,
        live: false,
      };
    case "paused_budget":
      return { text: "Paused at its spending cap. Open to continue", live: false };
    case "failed":
      return { text: "The last search hit a problem. Open to try again", live: false };
    case "cancelled":
      return { text: "The last search was stopped", live: false };
    default:
      return { text: "The agent is working…", live: true };
  }
}

function ProjectCard({
  p,
  run,
  i,
  canDelete,
  onDelete,
}: {
  p: PropertySummary;
  run: JobSummary | undefined;
  i: number;
  canDelete: boolean;
  onDelete: (p: PropertySummary) => void;
}) {
  const reduce = useReducedMotion();
  const { data: points } = useAccountsMap(p.id);
  const hot = points?.filter((x) => x.tier === "A").length;
  const s = statusLine(p, run);
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * i, duration: 0.4 }}
      className="relative"
    >
      <Link
        to="/p/$propertyId"
        params={{ propertyId: p.id }}
        className="card-halo group block overflow-hidden"
      >
        <div className="relative border-b border-border bg-background/40 p-4">
          <HaloRadar
            center={p.location}
            radiusKm={p.radius_km}
            points={points}
            labels={false}
            sweep={!!run}
            unit={p.distance_unit}
            className="mx-auto max-w-[200px]"
          />
          {run && (
            <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full border border-violet/40 bg-violet/15 px-2.5 py-1 text-[11px] font-medium text-violet backdrop-blur">
              <AgentPulse />
              Agent {Math.round(run.progress * 100)}%
            </span>
          )}
        </div>
        <div className="p-5">
          <div className="flex items-start justify-between gap-3 pr-6">
            <div className="min-w-0">
              <h3 className="truncate text-lg font-bold">{p.name}</h3>
              <p className="mt-0.5 flex items-center gap-1 truncate text-sm text-muted-foreground">
                <MapPin className="size-3.5 shrink-0" />
                {[p.locality, p.city].filter(Boolean).join(", ") || "Location pinned"}
              </p>
            </div>
            {p.lifecycle === "pre_opening" && (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-teal/40 bg-teal/10 px-2 py-0.5 text-[11px] text-teal">
                <CalendarClock className="size-3" />
                {p.opening_date ? `Opens ${date(p.opening_date)}` : "Opening soon"}
              </span>
            )}
          </div>
          <p
            className={`mt-3 flex items-center gap-1.5 text-sm ${s.live ? "text-violet" : "text-muted-foreground"}`}
          >
            {s.live && <AgentPulse />}
            {s.text}
          </p>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            {[
              { k: "Businesses", v: p.account_count },
              { k: "Hot leads", v: hot, gold: true },
              { k: "Search area", v: dist(p.radius_km, p.distance_unit, 0) },
            ].map((x) => (
              <div key={x.k} className="rounded-xl bg-surface-2 py-2">
                <div
                  className={`font-mono text-lg font-semibold tabular ${x.gold ? "text-gold" : ""}`}
                >
                  {x.v ?? "—"}
                </div>
                <div className="text-[11px] text-muted-foreground">{x.k}</div>
              </div>
            ))}
          </div>
        </div>
      </Link>
      {canDelete && (
        // modal={false}: opening the delete dialog from this menu must not leave the page unclickable.
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger
            className="absolute right-3 top-3 grid size-8 place-items-center rounded-lg border border-border bg-surface/80 text-muted-foreground backdrop-blur hover:text-foreground"
            aria-label={`Options for ${p.name}`}
          >
            <MoreHorizontal className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              className="text-coral"
              onSelect={() => setTimeout(() => onDelete(p), 0)}
            >
              <Trash2 className="size-4" />
              Delete project
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </motion.div>
  );
}

function ContinueCard({ p, run }: { p: PropertySummary; run: JobSummary | undefined }) {
  const s = statusLine(p, run);
  return (
    <Link
      to="/p/$propertyId"
      params={{ propertyId: p.id }}
      className="card-halo group flex flex-wrap items-center gap-5 p-5 transition-colors hover:border-gold/40"
    >
      <span className="grid size-12 place-items-center rounded-2xl bg-gold/15 text-gold">
        <Building2 />
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Continue where you left off
        </div>
        <div className="mt-0.5 truncate text-xl font-bold">{p.name}</div>
        <div
          className={`mt-0.5 flex items-center gap-1.5 text-sm ${s.live ? "text-violet" : "text-muted-foreground"}`}
        >
          {s.live && <AgentPulse />}
          {s.text}
        </div>
      </div>
      <span className="inline-flex items-center gap-1.5 rounded-xl bg-signature px-4 py-2 text-sm font-medium text-primary-foreground">
        Open project
        <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

const STEPS = [
  {
    icon: Search,
    title: "Finds",
    text: "Every business in the area around your hotel, from public maps.",
  },
  {
    icon: BookOpen,
    title: "Researches",
    text: "Reads their websites and the news for signs they need rooms or events.",
  },
  {
    icon: Target,
    title: "Recommends",
    text: "Ranks who to call first, explains why, and drafts the first email.",
  },
];

export function ProjectsPage() {
  const navigate = useNavigate();
  const { data: me } = useMe();
  const props = useProperties();
  const { data: runs = [] } = useRuns();
  const del = useDeleteProperty();
  const [toDelete, setToDelete] = useState<PropertySummary | null>(null);
  const list = props.data ?? [];
  const activeRuns = runs.filter((r) => isJobActive(r.status));
  const canManage = me?.role === "admin" || me?.role === "manager";
  const runFor = (id: string) => activeRuns.find((r) => r.property_id === id);

  // First visit with no hotels yet: go straight to setup. Only on arrival, not after deleting the last one.
  const checkedFirstVisit = useRef(false);
  useEffect(() => {
    if (!props.isSuccess || !me || checkedFirstVisit.current) return;
    checkedFirstVisit.current = true;
    if (list.length === 0 && canManage) void navigate({ to: "/new", replace: true });
  }, [props.isSuccess, me, list.length, canManage, navigate]);

  const lastId = getLastProject();
  const last =
    list.find((p) => p.id === lastId) ??
    [...list].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""))[0];

  const confirmDelete = () => {
    if (!toDelete) return;
    const name = toDelete.name;
    del.mutate(toDelete.id, {
      onSuccess: () => {
        if (getLastProject() === toDelete.id) setLastProject(null);
        toast.success(`${name} deleted`);
        setToDelete(null);
      },
      onError: (e) =>
        toast.error("Couldn't delete the project", { description: errorText(e).detail }),
    });
  };

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title={me ? `${greeting()}, ${firstName(me.user.full_name)}` : "Your projects"}
        sub="Each project is one hotel. Pick one to continue, or list a new hotel to start the agent."
        right={
          canManage ? (
            <Button variant="signature" className="rounded-xl" asChild>
              <Link to="/new">
                <Plus />
                List a new hotel
              </Link>
            </Button>
          ) : undefined
        }
      />

      {last && <ContinueCard p={last} run={runFor(last.id)} />}

      <div className="mt-10 flex flex-wrap items-end justify-between gap-3">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          Your projects <Explain k="project" />
        </h2>
        <RadarLegend />
      </div>

      {props.error ? (
        <ErrorState className="mt-4" error={props.error} onRetry={() => void props.refetch()} />
      ) : (
        <div className="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {props.isLoading &&
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="card-halo p-5">
                <Skeleton className="mx-auto aspect-square w-44 rounded-full" />
                <Skeleton className="mt-5 h-5 w-2/3" />
                <Skeleton className="mt-2 h-3 w-1/2" />
              </div>
            ))}
          {list.map((p, i) => (
            <ProjectCard
              key={p.id}
              p={p}
              i={i}
              run={runFor(p.id)}
              canDelete={canManage}
              onDelete={setToDelete}
            />
          ))}
          {props.isSuccess && canManage && (
            <Link
              to="/new"
              className="group flex min-h-[320px] flex-col items-center justify-center rounded-[var(--radius)] border border-dashed border-border p-6 text-center text-muted-foreground transition-colors hover:border-gold/50 hover:text-foreground"
            >
              <span className="grid size-12 place-items-center rounded-full border border-border transition-colors group-hover:border-gold/50 group-hover:text-gold">
                <Plus />
              </span>
              <span className="mt-3 font-medium">List a new hotel</span>
              <span className="mt-1 max-w-56 text-xs">
                Takes about a minute. The agent starts finding businesses right after.
              </span>
            </Link>
          )}
          {props.isSuccess && list.length === 0 && !canManage && (
            <div className="card-halo col-span-full p-8 text-center text-muted-foreground">
              No hotels have been shared with you yet. Ask your manager to give you access.
            </div>
          )}
        </div>
      )}

      <section className="mt-12 card-halo p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <Sparkles className="size-5 text-violet" />
            What the AI agent does for each hotel
          </h2>
          <Button variant="outline" className="rounded-xl" asChild>
            <Link to="/how-it-works">How it works, step by step</Link>
          </Button>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="rounded-xl bg-surface-2 p-4">
              <div className="flex items-center gap-2 font-medium">
                <span className="grid size-7 place-items-center rounded-full bg-violet/15 text-xs text-violet">
                  {i + 1}
                </span>
                <s.icon className="size-4 text-gold" />
                {s.title}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent className="rounded-2xl border-border bg-surface">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {toDelete?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              The hotel, its businesses and its pipeline disappear from Halo for everyone on your
              team. If the agent is working on it, it stops. An administrator can restore it if
              needed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              className="bg-coral text-white hover:bg-coral/90"
              disabled={del.isPending}
              onClick={(e) => {
                e.preventDefault();
                confirmDelete();
              }}
            >
              Delete project
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
