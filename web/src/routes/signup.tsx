import { createFileRoute } from "@tanstack/react-router";
import { LoginPage } from "@/pages/LoginPage";

function SignupPage() {
  return <LoginPage initialMode="signup" />;
}

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create account · Halo" },
      { name: "description", content: "Create a Halo account: the AI sales agent for hotels." },
      { property: "og:title", content: "Create account · Halo" },
      {
        property: "og:description",
        content: "Create a Halo account: the AI sales agent for hotels.",
      },
    ],
  }),
  component: SignupPage,
});
