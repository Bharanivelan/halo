import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/pages/SettingsPage";

export const Route = createFileRoute("/_shell/settings")({
  head: () => ({
    meta: [
      { title: "Settings · Halo" },
      { name: "description", content: "Connection, AI usage and team settings for Halo." },
      { property: "og:title", content: "Settings · Halo" },
      { property: "og:description", content: "Connection, AI usage and team settings for Halo." },
    ],
  }),
  component: SettingsPage,
});
