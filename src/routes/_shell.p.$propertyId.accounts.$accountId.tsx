import { createFileRoute } from "@tanstack/react-router";
import { AccountDetailPage } from "@/pages/AccountDetailPage";

export const Route = createFileRoute("/_shell/p/$propertyId/accounts/$accountId")({
  head: () => ({
    meta: [
      { title: "Prospect dossier · Halo" },
      { name: "description", content: "Evidence-backed research and pitch for a prospect." },
      { property: "og:title", content: "Prospect dossier · Halo" },
      { property: "og:description", content: "Evidence-backed research and pitch for a prospect." },
    ],
  }),
  component: AccountDetailPage,
});
