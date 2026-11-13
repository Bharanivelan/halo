import { Link, useLocation, useNavigate, useParams } from "@tanstack/react-router";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";
import {
  BookOpen,
  FlaskConical,
  Bot,
  Check,
  ChevronsUpDown,
  Globe2,
  Kanban,
  LayoutDashboard,
  LogOut,
  MapPin,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plug,
  Plus,
  Search,
  Settings,
  Sparkles,
  Sun,
  Users,
} from "lucide-react";
import { AgentPulse, Logo, useTheme } from "@/components/halo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { isJobActive, useLogout, useMe, useProperties, useRuns } from "@/hooks/use-halo";
import { setLastProject } from "@/lib/halo-projects";
import { AuthGate } from "./AuthGate";

const ROLE_LABEL = { admin: "Admin", manager: "Manager", rep: "Sales rep" } as const;

function LocationSwitcher({
  collapsed,
  pid,
  onNavigate,
}: {
  collapsed: boolean;
  pid: string | undefined;
  onNavigate?: (() => void) | undefined;
}) {
  const { data: props = [] } = useProperties();
  const current = props.find((p) => p.id === pid);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2 text-left text-sm transition-colors hover:border-gold/40",
          collapsed && "justify-center px-0",
        )}
        aria-label="Switch project"
      >
        <MapPin className="size-4 shrink-0 text-gold" />
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">{current?.name ?? "All projects"}</span>
              {current && (
                <span className="block truncate text-[11px] text-muted-foreground">
                  {[current.locality, current.city].filter(Boolean).join(", ")}
                </span>
              )}
            </span>
            <ChevronsUpDown className="size-3.5 text-muted-foreground" />
          </>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuItem asChild>
          <Link to="/" onClick={onNavigate}>
            <Globe2 className="size-4" />
            All projects{!pid && <Check className="ml-auto size-4" />}
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-xs text-muted-foreground">Your hotels</DropdownMenuLabel>
        {props.map((p) => (
          <DropdownMenuItem key={p.id} asChild>
            <Link to="/p/$propertyId" params={{ propertyId: p.id }} onClick={onNavigate}>
              <MapPin className="size-4 text-gold" />
              <span className="min-w-0 flex-1 truncate">{p.name}</span>
              {p.id === pid ? (
                <Check className="size-4" />
              ) : (
                <span className="font-mono text-xs text-muted-foreground">{p.account_count}</span>
              )}
            </Link>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/new" onClick={onNavigate}>
            <Plus className="size-4" />
            List a new hotel
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function SidebarBody({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const { data: me } = useMe();
  const logout = useLogout();
  const { data: runs = [] } = useRuns();
  const params = useParams({ strict: false }) as { propertyId?: string };
  const pid = params.propertyId;
  const active = runs.filter((r) => isJobActive(r.status) && (!pid || r.property_id === pid));
  const nav = [
    {
      label: "Overview",
      icon: LayoutDashboard,
      to: pid ? "/p/$propertyId" : "/",
      exact: true,
    },
    { label: "AI agent", icon: Bot, to: pid ? "/p/$propertyId/agent/new" : "/" },
    { label: "Prospects", icon: Users, to: pid ? "/p/$propertyId/accounts" : "/" },
    { label: "Pipeline", icon: Kanban, to: pid ? "/p/$propertyId/pipeline" : "/" },
  ] as const;
  const item =
    "flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground";
  const name = me?.user.full_name ?? "Account";
  return (
    <div className="flex h-full flex-col gap-4 p-3">
      <Link to="/" className="rounded-xl px-2 py-1" onClick={onNavigate}>
        <Logo compact={collapsed} />
      </Link>
      <LocationSwitcher collapsed={collapsed} pid={pid} onNavigate={onNavigate} />
      <nav className="flex flex-col gap-1" aria-label="Main">
        {nav.map((n) =>
          !pid && n.label !== "Overview" ? (
            <span
              key={n.label}
              aria-disabled
              title="Open a project first"
              className={cn(
                item,
                "cursor-not-allowed opacity-50 hover:bg-transparent hover:text-muted-foreground",
                collapsed && "justify-center px-0",
              )}
            >
              <n.icon className="size-4 shrink-0" />
              {!collapsed && n.label}
            </span>
          ) : (
            <Link
              key={n.label}
              to={n.to}
              params={{ propertyId: pid ?? "" } as never}
              onClick={onNavigate}
              activeOptions={{ exact: "exact" in n }}
              className={cn(item, collapsed && "justify-center px-0")}
              activeProps={{ className: "bg-surface-2 !text-foreground [&>svg]:text-gold" }}
              title={collapsed ? n.label : undefined}
            >
              <n.icon className="size-4 shrink-0" />
              {!collapsed && n.label}
              {!collapsed && n.label === "AI agent" && active.length > 0 && (
                <AgentPulse className="ml-auto" />
              )}
            </Link>
          ),
        )}
      </nav>

      {active[0] && !collapsed && (
        <Link
          to="/p/$propertyId/agent/$jobId"
          params={{ propertyId: active[0].property_id, jobId: active[0].id }}
          onClick={onNavigate}
          className="rounded-xl border border-violet/30 bg-violet/10 p-3 text-xs transition-colors hover:border-violet/60"
        >
          <div className="flex items-center gap-2 font-medium text-violet">
            <AgentPulse />
            Agent working
          </div>
          <div className="mt-1 truncate text-muted-foreground">{active[0].property_name}</div>
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-violet transition-[width] duration-700"
              style={{ width: `${Math.round(active[0].progress * 100)}%` }}
            />
          </div>
        </Link>
      )}

      <div className="mt-auto flex flex-col gap-1">
        {(
          [
            { to: "/lab", label: "Halo Lab", icon: FlaskConical },
            { to: "/how-it-works", label: "How it works", icon: BookOpen },
            { to: "/connectors", label: "Connectors", icon: Plug },
          ] as const
        ).map((l) => (
          <Link
            key={l.to}
            to={l.to}
            onClick={onNavigate}
            className={cn(item, collapsed && "justify-center px-0")}
            activeProps={{ className: "bg-surface-2 !text-foreground" }}
            title={collapsed ? l.label : undefined}
          >
            <l.icon className="size-4 shrink-0" />
            {!collapsed && l.label}
          </Link>
        ))}
        <Link
          to="/settings"
          onClick={onNavigate}
          className={cn(item, collapsed && "justify-center px-0")}
          activeProps={{ className: "bg-surface-2 !text-foreground" }}
        >
          <Settings className="size-4 shrink-0" />
          {!collapsed && "Settings"}
        </Link>
        <button
          onClick={toggle}
          className={cn(item, collapsed && "justify-center px-0")}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          {!collapsed && (theme === "dark" ? "Light theme" : "Dark theme")}
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger
            className={cn(item, "mt-1 border border-border", collapsed && "justify-center px-0")}
          >
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-signature text-[11px] font-bold text-primary-foreground">
              {name
                .split(/\s+/)
                .map((w) => w[0])
                .slice(0, 2)
                .join("")
                .toUpperCase()}
            </span>
            {!collapsed && (
              <span className="min-w-0 text-left">
                <span className="block truncate text-foreground">{name}</span>
                <span className="block truncate text-[11px]">
                  {me ? `${ROLE_LABEL[me.role]} · ${me.workspace.name}` : ""}
                </span>
              </span>
            )}
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="truncate font-medium">{name}</div>
              <div className="truncate text-xs text-muted-foreground">{me?.user.email}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() =>
                logout.mutate(undefined, { onSettled: () => void navigate({ to: "/login" }) })
              }
            >
              <LogOut className="size-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

function Breadcrumbs() {
  const { pathname } = useLocation();
  const { data: props = [] } = useProperties();
  const parts = pathname.split("/").filter(Boolean);
  const labels: Record<string, string> = {
    p: "",
    agent: "AI agent",
    new: "New run",
    accounts: "Prospects",
    pipeline: "Pipeline",
    settings: "Settings",
    "how-it-works": "How it works",
    connectors: "Connectors",
    lab: "Halo Lab",
  };
  const crumbs = ["Projects"];
  parts.forEach((p, i) => {
    if (p === "p") return;
    if (i === 0 && p === "new") {
      crumbs.push("List a new hotel");
      return;
    }
    if (parts[i - 1] === "p") crumbs.push(props.find((x) => x.id === p)?.name ?? "Project");
    else if (labels[p] !== undefined) crumbs.push(labels[p]);
    else crumbs.push(parts[i - 1] === "agent" ? "Run" : "Prospect");
  });
  return (
    <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-2 text-sm md:flex">
      {crumbs.map((c, i) => (
        <span key={i} className="flex items-center gap-2 truncate">
          {i > 0 && <span className="text-muted-foreground/50">/</span>}
          <span className={i === crumbs.length - 1 ? "font-medium" : "text-muted-foreground"}>
            {c}
          </span>
        </span>
      ))}
    </nav>
  );
}

function GlobalSearch({ pid }: { pid: string | undefined }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  return (
    <form
      className="relative ml-auto w-full max-w-xs"
      onSubmit={(e) => {
        e.preventDefault();
        if (pid)
          void navigate({
            to: "/p/$propertyId/accounts",
            params: { propertyId: pid },
            search: { q: q.trim() || undefined },
          });
      }}
    >
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        disabled={!pid}
        placeholder={pid ? "Search prospects" : "Open a project to search"}
        aria-label="Search prospects"
        className="h-9 rounded-xl border-border bg-surface pl-9"
      />
    </form>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const { pathname } = useLocation();
  const reduce = useReducedMotion();
  const params = useParams({ strict: false }) as { propertyId?: string };
  // Remember the project in use, so the next sign-in offers "Continue where you left off".
  useEffect(() => {
    if (params.propertyId) setLastProject(params.propertyId);
  }, [params.propertyId]);
  return (
    <AuthGate>
      <div className="flex min-h-screen">
        <aside
          className={cn(
            "sticky top-0 hidden h-screen shrink-0 border-r border-border bg-surface/60 backdrop-blur transition-[width] md:block",
            collapsed ? "w-[72px]" : "w-64",
          )}
        >
          <SidebarBody collapsed={collapsed} />
        </aside>
        <Sheet open={mobile} onOpenChange={setMobile}>
          <SheetContent side="left" className="w-64 border-border bg-surface p-0">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <SidebarBody collapsed={false} onNavigate={() => setMobile(false)} />
          </SheetContent>
        </Sheet>
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/70 px-4 backdrop-blur-xl md:px-6">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobile(true)}
              aria-label="Open navigation"
            >
              <PanelLeftOpen />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="hidden md:inline-flex"
              onClick={() => setCollapsed((c) => !c)}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
            </Button>
            <Breadcrumbs />
            <GlobalSearch key={params.propertyId ?? "none"} pid={params.propertyId} />
            {params.propertyId ? (
              <Button variant="signature" className="rounded-xl" asChild>
                <Link to="/p/$propertyId/agent/new" params={{ propertyId: params.propertyId }}>
                  <Sparkles />
                  <span className="hidden sm:inline">Run agent</span>
                </Link>
              </Button>
            ) : (
              <Button
                variant="signature"
                className="rounded-xl"
                disabled
                title="Open a project first"
              >
                <Sparkles />
                <span className="hidden sm:inline">Run agent</span>
              </Button>
            )}
          </header>
          <AnimatePresence mode="wait">
            <motion.main
              key={pathname}
              className="flex-1 p-4 md:p-8"
              initial={reduce ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: reduce ? 1 : 0 }}
              transition={{ duration: 0.15 }}
            >
              {children}
            </motion.main>
          </AnimatePresence>
        </div>
      </div>
    </AuthGate>
  );
}
