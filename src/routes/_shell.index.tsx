import { createFileRoute } from "@tanstack/react-router";
import { PortfolioPage } from "@/pages/PortfolioPage";

export const Route = createFileRoute("/_shell/")({
  head: () => ({ meta: [
    { title: "Portfolio · Halo" },
    { name: "description", content: "All your locations and the prospects inside each halo." },
    { property: "og:title", content: "Portfolio · Halo" },
    { property: "og:description", content: "All your locations and the prospects inside each halo." },
  ] }),
  component: PortfolioPage,
});
