import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Settings" sub="Connection, AI usage and team." emptyTitle="Settings coming next" emptyText="Server connection, AI usage and team management will live here." />;

export const Route = createFileRoute("/_shell/settings")({
  head: () => ({ meta: [
    { title: "Settings · Halo" },
    { name: "description", content: "Connection, AI usage and team settings for Halo." },
    { property: "og:title", content: "Settings · Halo" },
    { property: "og:description", content: "Connection, AI usage and team settings for Halo." },
  ] }),
  component: Page,
});
