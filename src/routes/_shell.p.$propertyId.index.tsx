import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Command center" sub="Everything happening around this location." emptyTitle="No activity yet" emptyText="Run the agent to discover the companies inside this location's halo." />;

export const Route = createFileRoute("/_shell/p/$propertyId/")({
  head: () => ({ meta: [
    { title: "Command center · Halo" },
    { name: "description", content: "Live command center for one location." },
    { property: "og:title", content: "Command center · Halo" },
    { property: "og:description", content: "Live command center for one location." },
  ] }),
  component: Page,
});
