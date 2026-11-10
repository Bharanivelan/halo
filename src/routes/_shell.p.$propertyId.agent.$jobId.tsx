import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Agent run" sub="Live progress of this run." emptyTitle="Waiting for the run" emptyText="Stages and the live log will stream here." />;

export const Route = createFileRoute("/_shell/p/$propertyId/agent/$jobId")({
  head: () => ({ meta: [
    { title: "Agent run · Halo" },
    { name: "description", content: "Watch the Halo agent work in real time." },
    { property: "og:title", content: "Agent run · Halo" },
    { property: "og:description", content: "Watch the Halo agent work in real time." },
  ] }),
  component: Page,
});
