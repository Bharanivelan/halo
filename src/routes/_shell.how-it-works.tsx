import { createFileRoute } from "@tanstack/react-router";
import { HowItWorksPage } from "@/pages/HowItWorksPage";

export const Route = createFileRoute("/_shell/how-it-works")({
  head: () => ({
    meta: [
      { title: "How Halo's AI works · Halo" },
      {
        name: "description",
        content: "A plain-English tour of what Halo's AI agent does and how to read its results.",
      },
      { property: "og:title", content: "How Halo's AI works · Halo" },
      {
        property: "og:description",
        content: "A plain-English tour of what Halo's AI agent does and how to read its results.",
      },
    ],
  }),
  component: HowItWorksPage,
});
