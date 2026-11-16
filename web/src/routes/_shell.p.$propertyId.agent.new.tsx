import { createFileRoute } from "@tanstack/react-router";
import { AgentNewPage } from "@/pages/AgentNewPage";

export const Route = createFileRoute("/_shell/p/$propertyId/agent/new")({
  head: () => ({
    meta: [
      { title: "Run agent · Halo" },
      { name: "description", content: "Configure an agent run for this location." },
      { property: "og:title", content: "Run agent · Halo" },
      { property: "og:description", content: "Configure an agent run for this location." },
    ],
  }),
  component: AgentNewPage,
});
