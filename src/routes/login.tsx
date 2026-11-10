import { createFileRoute } from "@tanstack/react-router";
import { LoginPage } from "@/pages/LoginPage";

export const Route = createFileRoute("/login")({
  head: () => ({ meta: [
    { title: "Sign in · Halo" },
    { name: "description", content: "Sign in to Halo, the AI go-to-market agent for hospitality groups." },
    { property: "og:title", content: "Sign in · Halo" },
    { property: "og:description", content: "Sign in to Halo, the AI go-to-market agent for hospitality groups." },
  ] }),
  component: LoginPage,
});
