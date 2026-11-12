import { useNavigate } from "@tanstack/react-router";
import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { ApiError, getApiUrl, halo } from "@/lib/halo-api";
import { useLogin } from "@/hooks/use-halo";
import { errorText } from "@/components/halo";
import { Loader2, Server } from "lucide-react";
import { Logo } from "@/components/halo";
import { ConnectionDialog } from "@/components/layout/ConnectionDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Fixed layout so SSR and client render identically (no randomness).
const CITIES = [
  { name: "Chennai", x: 74, y: 40, r: 22, color: "var(--gold)", delay: 0 },
  { name: "Vellore", x: 52, y: 30, r: 13, color: "var(--teal)", delay: 1.4 },
  { name: "Coimbatore", x: 24, y: 70, r: 17, color: "var(--coral)", delay: 2.6 },
];
const DOTS = Array.from({ length: 54 }, (_, i) => {
  const c = CITIES[i % 3]!;
  const a = i * 2.39996;
  const d = c.r * (0.25 + ((i * 37) % 70) / 100);
  return {
    x: c.x + Math.cos(a) * d,
    y: c.y + Math.sin(a) * d * 0.9,
    color: c.color,
    delay: (i * 0.37) % 5,
    big: i % 7 === 0,
  };
});

function HaloMap() {
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid slice"
      className="absolute inset-0 size-full"
      aria-hidden
    >
      <defs>
        <pattern id="grid" width="4" height="4" patternUnits="userSpaceOnUse">
          <path
            d="M4 0H0V4"
            fill="none"
            stroke="var(--foreground)"
            strokeOpacity="0.05"
            strokeWidth="0.1"
          />
        </pattern>
        {CITIES.map((c) => (
          <radialGradient key={c.name} id={`g-${c.name}`}>
            <stop offset="0%" stopColor={c.color} stopOpacity="0.22" />
            <stop offset="100%" stopColor={c.color} stopOpacity="0" />
          </radialGradient>
        ))}
      </defs>
      <g style={{ animation: "drift 40s ease-in-out infinite alternate" }}>
        <rect x="-10" y="-10" width="130" height="130" fill="url(#grid)" />
        {/* faint road / coast lines */}
        <path
          d="M-5 55 C 20 50, 40 62, 60 45 S 90 30, 110 38"
          fill="none"
          stroke="var(--foreground)"
          strokeOpacity="0.08"
          strokeWidth="0.25"
        />
        <path
          d="M24 70 C 35 55, 45 38, 52 30 L 74 40"
          fill="none"
          stroke="var(--gold)"
          strokeOpacity="0.18"
          strokeWidth="0.2"
          strokeDasharray="0.8 0.8"
        />
        <path
          d="M84 -5 C 80 20, 88 50, 80 110"
          fill="none"
          stroke="var(--teal)"
          strokeOpacity="0.1"
          strokeWidth="0.4"
        />
      </g>
      {CITIES.map((c) => (
        <g key={c.name}>
          <circle cx={c.x} cy={c.y} r={c.r * 1.3} fill={`url(#g-${c.name})`} />
          {[0.5, 1].map((s) => (
            <circle
              key={s}
              cx={c.x}
              cy={c.y}
              r={c.r * s}
              fill="none"
              stroke={c.color}
              strokeOpacity="0.15"
              strokeWidth="0.15"
            />
          ))}
          {[0, 1.5, 3].map((d) => (
            <circle
              key={d}
              cx={c.x}
              cy={c.y}
              r={c.r}
              fill="none"
              stroke={c.color}
              strokeWidth="0.25"
              className="anim-halo-ring"
              style={{ animationDelay: `${c.delay + d}s` }}
            />
          ))}
        </g>
      ))}
      {DOTS.map((d, i) => (
        <circle
          key={i}
          cx={d.x}
          cy={d.y}
          r={d.big ? 0.7 : 0.4}
          fill={d.color}
          className="anim-dot-light"
          style={{ animationDelay: `${d.delay}s`, filter: `drop-shadow(0 0 0.6px ${d.color})` }}
        />
      ))}
      {CITIES.map((c) => (
        <g key={c.name}>
          <circle
            cx={c.x}
            cy={c.y}
            r="1.1"
            fill="var(--gold)"
            style={{ filter: "drop-shadow(0 0 1.5px var(--gold))" }}
          />
          <text
            x={c.x + 2}
            y={c.y - 1.5}
            fontSize="1.9"
            fill="var(--foreground)"
            fillOpacity="0.6"
            fontFamily="var(--font-mono)"
          >
            {c.name}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function LoginPage() {
  const reduce = useReducedMotion();
  const navigate = useNavigate();
  const [conn, setConn] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState<string | null>(null);
  const login = useLogin();
  const busy = login.isPending;
  const err = login.error ? errorText(login.error) : null;

  useEffect(() => {
    if (halo.isSignedIn()) void navigate({ to: "/", replace: true });
    setServer(getApiUrl());
  }, [navigate, conn]);
  const fade = (d: number) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 12 },
          animate: { opacity: 1, y: 0 },
          transition: { delay: d, duration: 0.6 },
        };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.25fr_1fr]">
      <section className="relative min-h-[46vh] overflow-hidden border-b border-border bg-background lg:min-h-screen lg:border-b-0 lg:border-r">
        <HaloMap />
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/30 to-transparent" />
        <div className="relative flex h-full flex-col justify-between p-6 md:p-12">
          <Logo />
          <div className="max-w-xl pt-24 lg:pt-0">
            <motion.h1 {...fade(0.1)} className="text-3xl font-bold leading-[1.1] md:text-5xl">
              Every hotel has a halo.{" "}
              <span className="text-signature">Halo finds who's inside it.</span>
            </motion.h1>
            <motion.p {...fade(0.25)} className="mt-4 max-w-md text-muted-foreground md:text-lg">
              An AI sales agent for hotels. It finds the businesses around your hotel, learns
              which ones need rooms and event space, and tells you who to call first.
            </motion.p>
          </div>
        </div>
      </section>

      <section className="flex items-center justify-center p-6 md:p-12">
        <motion.div {...fade(0.15)} className="w-full max-w-sm">
          <div className="card-halo p-7 md:p-8">
            <h2 className="text-2xl font-bold">Sign in</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Pick up where you left off, or list a new hotel.
            </p>
            <form
              className="mt-6 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                login.mutate({ email, password }, { onSuccess: () => void navigate({ to: "/" }) });
              }}
            >
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 rounded-xl bg-surface-2"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 rounded-xl bg-surface-2"
                />
              </div>
              {err && (
                <div
                  role="alert"
                  className="rounded-xl border border-coral/30 bg-coral/10 p-3 text-sm"
                >
                  <p className="font-medium text-coral">{err.title}</p>
                  <p className="mt-0.5 text-muted-foreground">{err.detail}</p>
                  {login.error instanceof ApiError && login.error.status === 0 && (
                    <button
                      type="button"
                      onClick={() => setConn(true)}
                      className="mt-1 font-medium text-gold hover:underline"
                    >
                      Change server
                    </button>
                  )}
                </div>
              )}
              <Button
                type="submit"
                variant="signature"
                className="h-11 w-full rounded-xl"
                disabled={busy}
              >
                {busy && <Loader2 className="animate-spin" />}Sign in
              </Button>
            </form>
          </div>
          <button
            onClick={() => setConn(true)}
            className="mx-auto mt-5 flex items-center gap-1.5 rounded text-xs text-muted-foreground hover:text-foreground"
          >
            <Server className="size-3.5" />
            Connection settings
          </button>
          {server && (
            <p className="mt-1 truncate text-center font-mono text-[11px] text-muted-foreground/70">
              {server.replace(/^https?:\/\//, "")}
            </p>
          )}
        </motion.div>
      </section>
      <ConnectionDialog open={conn} onOpenChange={setConn} />
    </div>
  );
}
