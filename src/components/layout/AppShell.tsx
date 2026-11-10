import { Link, useLocation, useParams } from "@tanstack/react-router";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useState, type ReactNode } from "react";
import { Bot, ChevronsUpDown, Kanban, LayoutDashboard, LogOut, MapPin, Moon, PanelLeftClose, PanelLeftOpen, Search, Settings, Sparkles, Sun, Users } from "lucide-react";
import { Logo, useTheme } from "@/components/halo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

function SidebarBody({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const { theme, toggle } = useTheme();
  const params = useParams({ strict: false }) as { propertyId?: string };
  const pid = params.propertyId;
  const nav = [
    { label: "Command center", icon: LayoutDashboard, to: pid ? "/p/$propertyId" : "/", exact: true },
    { label: "Agent runs", icon: Bot, to: pid ? "/p/$propertyId/agent/new" : "/" },
    { label: "Prospects", icon: Users, to: pid ? "/p/$propertyId/accounts" : "/" },
    { label: "Pipeline", icon: Kanban, to: pid ? "/p/$propertyId/pipeline" : "/" },
  ] as const;
  const item = "flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground";
  return (
    <div className="flex h-full flex-col gap-4 p-3">
      <Link to="/" className="rounded-xl px-2 py-1" onClick={onNavigate}><Logo compact={collapsed} /></Link>
      <button className={cn("flex items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2 text-left text-sm", collapsed && "justify-center px-0")} aria-label="Switch location">
        <MapPin className="size-4 shrink-0 text-gold" />
        {!collapsed && <><span className="flex-1 truncate">{pid ? "Current location" : "All locations"}</span><ChevronsUpDown className="size-3.5 text-muted-foreground" /></>}
      </button>
      <nav className="flex flex-col gap-1" aria-label="Main">
        {nav.map((n) => (
          <Link key={n.label} to={n.to} params={{ propertyId: pid ?? "" } as never} onClick={onNavigate}
            activeOptions={{ exact: "exact" in n }}
            className={cn(item, collapsed && "justify-center px-0")}
            activeProps={{ className: "bg-surface-2 !text-foreground [&>svg]:text-gold" }} title={collapsed ? n.label : undefined}>
            <n.icon className="size-4 shrink-0" />{!collapsed && n.label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto flex flex-col gap-1">
        <Link to="/settings" onClick={onNavigate} className={cn(item, collapsed && "justify-center px-0")} activeProps={{ className: "bg-surface-2 !text-foreground" }}>
          <Settings className="size-4 shrink-0" />{!collapsed && "Settings"}
        </Link>
        <button onClick={toggle} className={cn(item, collapsed && "justify-center px-0")} aria-label="Toggle theme">
          {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}{!collapsed && (theme === "dark" ? "Light theme" : "Dark theme")}
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger className={cn(item, "mt-1 border border-border", collapsed && "justify-center px-0")}>
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-signature text-[11px] font-bold text-primary-foreground">H</span>
            {!collapsed && <span className="truncate">Account</span>}
          </DropdownMenuTrigger>
          <DropdownMenuContent side="top" align="start" className="w-52">
            <DropdownMenuLabel className="text-muted-foreground">Signed in</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild><Link to="/login"><LogOut className="size-4" />Sign out</Link></DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

function Breadcrumbs() {
  const { pathname } = useLocation();
  const parts = pathname.split("/").filter(Boolean);
  const labels: Record<string, string> = { p: "", agent: "Agent runs", new: "New run", accounts: "Prospects", pipeline: "Pipeline", settings: "Settings" };
  const crumbs = ["Portfolio"];
  parts.forEach((p, i) => {
    if (p === "p") return;
    if (parts[i - 1] === "p") crumbs.push("Location");
    else if (labels[p] !== undefined) crumbs.push(labels[p]);
    else crumbs.push(parts[i - 1] === "agent" ? "Run" : "Prospect");
  });
  return (
    <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-2 text-sm md:flex">
      {crumbs.map((c, i) => (
        <span key={i} className="flex items-center gap-2 truncate">
          {i > 0 && <span className="text-muted-foreground/50">/</span>}
          <span className={i === crumbs.length - 1 ? "font-medium" : "text-muted-foreground"}>{c}</span>
        </span>
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const { pathname } = useLocation();
  const reduce = useReducedMotion();
  const params = useParams({ strict: false }) as { propertyId?: string };
  return (
    <div className="flex min-h-screen">
      <aside className={cn("sticky top-0 hidden h-screen shrink-0 border-r border-border bg-surface/60 backdrop-blur transition-[width] md:block", collapsed ? "w-[72px]" : "w-64")}>
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
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobile(true)} aria-label="Open navigation"><PanelLeftOpen /></Button>
          <Button variant="ghost" size="icon" className="hidden md:inline-flex" onClick={() => setCollapsed((c) => !c)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
          </Button>
          <Breadcrumbs />
          <div className="relative ml-auto w-full max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Search prospects" aria-label="Search prospects" className="h-9 rounded-xl border-border bg-surface pl-9" />
          </div>
          {params.propertyId ? (
            <Button variant="signature" className="rounded-xl" asChild>
              <Link to="/p/$propertyId/agent/new" params={{ propertyId: params.propertyId }}><Sparkles />Run agent</Link>
            </Button>
          ) : (
            <Button variant="signature" className="rounded-xl" disabled title="Pick a location first"><Sparkles /><span className="hidden sm:inline">Run agent</span></Button>
          )}
        </header>
        <AnimatePresence mode="wait">
          <motion.main key={pathname} className="flex-1 p-4 md:p-8"
            initial={reduce ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: reduce ? 1 : 0 }} transition={{ duration: 0.15 }}>
            {children}
          </motion.main>
        </AnimatePresence>
      </div>
    </div>
  );
}
