import { createFileRoute } from "@tanstack/react-router";
import { NewProjectPage } from "@/pages/NewProjectPage";

export const Route = createFileRoute("/_shell/new")({
  head: () => ({
    meta: [
      { title: "List a new hotel · Halo" },
      {
        name: "description",
        content: "Set up a hotel in three steps and let Halo's AI agent find nearby businesses.",
      },
      { property: "og:title", content: "List a new hotel · Halo" },
      {
        property: "og:description",
        content: "Set up a hotel in three steps and let Halo's AI agent find nearby businesses.",
      },
    ],
  }),
  component: NewProjectPage,
});
