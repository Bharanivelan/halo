import { createFileRoute } from "@tanstack/react-router";
import { PlaceholderPage } from "@/pages/PlaceholderPage";
const Page = () => <PlaceholderPage title="Prospect dossier" sub="Research, signals and the recommended pitch." emptyTitle="Dossier coming next" emptyText="Scores, evidence and the pitch draft will appear here." />;

export const Route = createFileRoute("/_shell/p/$propertyId/accounts/$accountId")({
  head: () => ({ meta: [
    { title: "Prospect dossier · Halo" },
    { name: "description", content: "Evidence-backed research and pitch for a prospect." },
    { property: "og:title", content: "Prospect dossier · Halo" },
    { property: "og:description", content: "Evidence-backed research and pitch for a prospect." },
  ] }),
  component: Page,
});
