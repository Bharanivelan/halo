import { createFileRoute } from "@tanstack/react-router";
import { CommandCenterPage } from "@/pages/CommandCenterPage";

export const Route = createFileRoute("/_shell/p/$propertyId/")({
  head: () => ({
    meta: [
      { title: "Command center · Halo" },
      { name: "description", content: "Live command center for one location." },
      { property: "og:title", content: "Command center · Halo" },
      { property: "og:description", content: "Live command center for one location." },
    ],
  }),
  component: CommandCenterPage,
});
