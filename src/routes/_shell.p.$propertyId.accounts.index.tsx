import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Prospects" sub="Companies inside this location's halo." emptyTitle="No prospects yet" emptyText="Run the agent to find and score nearby companies." />;

export const Route = createFileRoute("/_shell/p/$propertyId/accounts/")({
  head: () => ({ meta: [
    { title: "Prospects · Halo" },
    { name: "description", content: "Scored prospects around this location." },
    { property: "og:title", content: "Prospects · Halo" },
    { property: "og:description", content: "Scored prospects around this location." },
  ] }),
  component: Page,
});
