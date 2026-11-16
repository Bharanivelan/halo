import { createFileRoute } from "@tanstack/react-router";
import { AgentRunPage } from "@/pages/AgentRunPage";

export const Route = createFileRoute("/_shell/p/$propertyId/agent/$jobId")({
  head: () => ({
    meta: [
      { title: "Agent run · Halo" },
      { name: "description", content: "Watch the Halo agent work in real time." },
      { property: "og:title", content: "Agent run · Halo" },
      { property: "og:description", content: "Watch the Halo agent work in real time." },
    ],
  }),
  component: AgentRunPage,
});
