import { Link } from "@tanstack/react-router";
import {
  Building,
  Calendar,
  Database,
  FileSpreadsheet,
  Globe,
  Linkedin,
  Mail,
  Map as MapIcon,
  MessageSquare,
  Newspaper,
  Plug,
  type LucideIcon,
} from "lucide-react";
import { useReference } from "@/hooks/use-halo";
import { cn } from "@/lib/utils";
import { PageHeader } from "./PlaceholderPage";

type Status = "on" | "off" | "soon";
interface Connector {
  name: string;
  icon: LucideIcon;
  what: string;
  status: Status;
  note?: string;
}

export function ConnectorsPage() {
  const { data: ref } = useReference();
  const search: Status = ref?.search_configured ? "on" : "off";
  const groups: { title: string; sub: string; items: Connector[] }[] = [
    {
      title: "Where Halo finds businesses",
      sub: "Sources the agent searches when it looks around your hotel.",
      items: [
        {
          name: "OpenStreetMap",
          icon: MapIcon,
          what: "Free public map of offices, factories, hospitals and colleges.",
          status: "on",
        },
        {
          name: "Upload a list (CSV)",
          icon: FileSpreadsheet,
          what: "Add companies you already know about from a spreadsheet. Start a new agent run in a project to upload.",
          status: "on",
        },
        {
          name: "Web and news search",
          icon: Newspaper,
          what: "Finds recent hiring, expansions and events for each company.",
          status: search,
          ...(search === "off" ? { note: "Needs a search key on the server" } : {}),
        },
        {
          name: "Google Maps / Places",
          icon: Globe,
          what: "Richer business listings, ratings and opening hours.",
          status: "soon",
        },
        {
          name: "Apollo",
          icon: Database,
          what: "Company size, revenue and verified work contacts.",
          status: "soon",
        },
        {
          name: "LinkedIn Sales Navigator",
          icon: Linkedin,
          what: "Find the right travel, HR and admin decision makers.",
          status: "soon",
        },
      ],
    },
    {
      title: "Where your results go",
      sub: "Send prospects, notes and deals into the tools your team already uses.",
      items: [
        {
          name: "HubSpot",
          icon: Building,
          what: "Sync prospects and deals both ways.",
          status: "soon",
        },
        {
          name: "Salesforce",
          icon: Building,
          what: "Create leads and opportunities automatically.",
          status: "soon",
        },
        {
          name: "Gmail and Outlook",
          icon: Mail,
          what: "Send the drafted pitch from your own inbox and log replies.",
          status: "soon",
        },
        {
          name: "Google and Outlook Calendar",
          icon: Calendar,
          what: "Book site visits and follow-ups.",
          status: "soon",
        },
        {
          name: "Slack",
          icon: MessageSquare,
          what: "Get a message when the agent finds a hot lead.",
          status: "soon",
        },
        {
          name: "CSV export",
          icon: FileSpreadsheet,
          what: "Download any project's prospects as a spreadsheet from the Prospects page.",
          status: "on",
        },
      ],
    },
  ];

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Connectors"
        sub="Connect Halo to where your data comes from and where your team works."
      />
      {groups.map((g) => (
        <section key={g.title} className="mb-10">
          <h2 className="text-xl font-bold">{g.title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{g.sub}</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {g.items.map((c) => (
              <div
                key={c.name}
                className={cn("card-halo flex flex-col p-5", c.status === "soon" && "opacity-80")}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="grid size-10 place-items-center rounded-xl bg-surface-2 text-gold">
                    <c.icon className="size-5" />
                  </span>
                  <span
                    className={cn(
                      "rounded-full border px-2.5 py-0.5 text-xs",
                      c.status === "on" && "border-teal/40 bg-teal/10 text-teal",
                      c.status === "off" && "border-border text-muted-foreground",
                      c.status === "soon" && "border-violet/40 bg-violet/10 text-violet",
                    )}
                  >
                    {c.status === "on" ? "Connected" : c.status === "off" ? "Off" : "Coming soon"}
                  </span>
                </div>
                <div className="mt-3 font-medium">{c.name}</div>
                <p className="mt-1 flex-1 text-sm text-muted-foreground">{c.what}</p>
                {c.note && <p className="mt-2 text-xs text-muted-foreground">{c.note}</p>}
              </div>
            ))}
          </div>
        </section>
      ))}
      <div className="card-halo flex flex-wrap items-center gap-4 p-5">
        <Plug className="size-5 text-gold" />
        <p className="flex-1 text-sm text-muted-foreground">
          Need a tool that isn't listed? Tell us which one, and we'll prioritise it.
        </p>
        <Link to="/how-it-works" className="text-sm text-gold hover:underline">
          How the agent uses these sources
        </Link>
      </div>
    </div>
  );
}
