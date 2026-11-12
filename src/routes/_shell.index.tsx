import { createFileRoute } from "@tanstack/react-router";
import { ProjectsPage } from "@/pages/ProjectsPage";

export const Route = createFileRoute("/_shell/")({
  head: () => ({
    meta: [
      { title: "Your projects · Halo" },
      {
        name: "description",
        content: "Each project is one hotel. Continue where you left off or list a new hotel.",
      },
      { property: "og:title", content: "Your projects · Halo" },
      {
        property: "og:description",
        content: "Each project is one hotel. Continue where you left off or list a new hotel.",
      },
    ],
  }),
  component: ProjectsPage,
});
