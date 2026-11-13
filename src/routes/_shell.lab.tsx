import { createFileRoute } from "@tanstack/react-router";
import { LabPage } from "@/pages/LabPage";

export const Route = createFileRoute("/_shell/lab")({
  head: () => ({
    meta: [
      { title: "Halo Lab · Halo" },
      { name: "description", content: "Teach Halo what a good lead looks like and improve the agent safely." },
      { property: "og:title", content: "Halo Lab · Halo" },
      {
        property: "og:description",
        content: "Teach Halo what a good lead looks like and improve the agent safely.",
      },
    ],
  }),
  component: LabPage,
});
