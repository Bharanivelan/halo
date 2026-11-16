import { createFileRoute } from "@tanstack/react-router";
import { ConnectorsPage } from "@/pages/ConnectorsPage";

export const Route = createFileRoute("/_shell/connectors")({
  head: () => ({
    meta: [
      { title: "Connectors · Halo" },
      { name: "description", content: "Connect Halo to your data sources, CRM, email and chat." },
      { property: "og:title", content: "Connectors · Halo" },
      {
        property: "og:description",
        content: "Connect Halo to your data sources, CRM, email and chat.",
      },
    ],
  }),
  component: ConnectorsPage,
});
