import { createFileRoute } from "@tanstack/react-router";
import { PipelinePage } from "@/pages/PipelinePage";

export const Route = createFileRoute("/_shell/p/$propertyId/pipeline")({
  head: () => ({
    meta: [
      { title: "Pipeline · Halo" },
      { name: "description", content: "Opportunities by stage for this location." },
      { property: "og:title", content: "Pipeline · Halo" },
      { property: "og:description", content: "Opportunities by stage for this location." },
    ],
  }),
  component: PipelinePage,
});
