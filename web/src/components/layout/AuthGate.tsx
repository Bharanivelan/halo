import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { halo } from "@/lib/halo-api";
import { HaloRings } from "@/components/halo";

/**
 * Client-only sign-in gate. The token lives in localStorage, so the server render can't know it;
 * we render a splash until mounted, then either show the app or go to /login.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!halo.isSignedIn()) {
      void navigate({ to: "/login", replace: true });
      return;
    }
    setReady(true);
    const out = () => {
      qc.clear();
      void navigate({ to: "/login", replace: true });
    };
    window.addEventListener("halo:signed-out", out);
    return () => window.removeEventListener("halo:signed-out", out);
  }, [navigate, qc]);

  if (!ready) {
    return (
      <div className="grid min-h-screen place-items-center">
        <HaloRings size={120} />
      </div>
    );
  }
  return <>{children}</>;
}
