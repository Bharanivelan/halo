import { createFileRoute } from "@tanstack/react-router";
import { AccountsPage } from "@/pages/AccountsPage";

export type AccountsSearch = {
  q?: string | undefined;
  job?: string | undefined;
  tier?: string | undefined;
};

export const Route = createFileRoute("/_shell/p/$propertyId/accounts/")({
  validateSearch: (s: Record<string, unknown>): AccountsSearch => ({
    q: typeof s["q"] === "string" && s["q"] ? s["q"] : undefined,
    job: typeof s["job"] === "string" && s["job"] ? s["job"] : undefined,
    tier: typeof s["tier"] === "string" && /^[ABC]$/.test(s["tier"]) ? s["tier"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Prospects · Halo" },
      { name: "description", content: "Scored prospects around this location." },
      { property: "og:title", content: "Prospects · Halo" },
      { property: "og:description", content: "Scored prospects around this location." },
    ],
  }),
  component: AccountsPage,
});
