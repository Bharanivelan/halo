import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Run agent" sub="Configure what the agent should look for." emptyTitle="Agent setup coming next" emptyText="Choose radius, offerings and depth, then launch." />;

export const Route = createFileRoute("/_shell/p/$propertyId/agent/new")({
  head: () => ({ meta: [
    { title: "Run agent · Halo" },
    { name: "description", content: "Configure an agent run for this location." },
    { property: "og:title", content: "Run agent · Halo" },
    { property: "og:description", content: "Configure an agent run for this location." },
  ] }),
  component: Page,
});
