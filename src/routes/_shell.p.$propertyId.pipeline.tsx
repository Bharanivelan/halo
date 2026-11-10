import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Pipeline" sub="Opportunities by stage." emptyTitle="No opportunities yet" emptyText="Move a prospect into the pipeline from its dossier." />;

export const Route = createFileRoute("/_shell/p/$propertyId/pipeline")({
  head: () => ({ meta: [
    { title: "Pipeline · Halo" },
    { name: "description", content: "Opportunities by stage for this location." },
    { property: "og:title", content: "Pipeline · Halo" },
    { property: "og:description", content: "Opportunities by stage for this location." },
  ] }),
  component: Page,
});
