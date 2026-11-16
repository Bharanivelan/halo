import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Loader2, Moon, Server, Sun, UserRound } from "lucide-react";
import { ErrorState, SectionTitle, useTheme } from "@/components/halo";
import {
  ConnectionDialog,
  HealthLine,
  probe,
  type Health,
} from "@/components/layout/ConnectionDialog";
import { Button } from "@/components/ui/button";
import { useMe, useMembers, useUsage } from "@/hooks/use-halo";
import { getApiUrl } from "@/lib/halo-api";
import { num, usd } from "@/lib/halo-format";
import { cn } from "@/lib/utils";
import { PageHeader } from "./PlaceholderPage";

const ROLE = { admin: "Admin", manager: "Manager", rep: "Sales rep" } as const;
type Group = "step" | "model" | "job";

function Usage() {
  const [g, setG] = useState<Group>("step");
  const u = useUsage(g);
  const rows = u.data ?? [];
  const total = rows.reduce((s, r) => s + r.cost_usd, 0);
  const calls = rows.reduce((s, r) => s + r.calls, 0);
  return (
    <div className="card-halo p-5 lg:col-span-2">
      <SectionTitle
        right={
          <div className="flex gap-1 rounded-xl bg-surface-2 p-1">
            {(["step", "model", "job"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setG(k)}
                className={cn(
                  "rounded-lg px-3 py-1 text-xs capitalize",
                  g === k ? "bg-surface font-medium shadow" : "text-muted-foreground",
                )}
              >
                By {k === "job" ? "run" : k}
              </button>
            ))}
          </div>
        }
      >
        AI usage · last 30 days
      </SectionTitle>
      <div className="mb-4 flex gap-8">
        <div>
          <div className="font-mono text-3xl font-semibold text-signature">{usd(total)}</div>
          <div className="text-xs text-muted-foreground">spent</div>
        </div>
        <div>
          <div className="font-mono text-3xl font-semibold">{num(calls)}</div>
          <div className="text-xs text-muted-foreground">AI calls</div>
        </div>
      </div>
      {u.error ? (
        <ErrorState error={u.error} />
      ) : u.isLoading ? (
        <div className="grid h-56 place-items-center">
          <Loader2 className="animate-spin text-muted-foreground" />
        </div>
      ) : rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No AI calls yet. Usage appears after the first agent run with AI on.
        </p>
      ) : (
        <>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows.slice(0, 10)} margin={{ left: -10, right: 8 }}>
                <defs>
                  <linearGradient id="usagebar" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--gold)" />
                    <stop offset="100%" stopColor="var(--coral)" stopOpacity={0.7} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  interval={0}
                  tickFormatter={(v: string) => (v.length > 14 ? `${v.slice(0, 13)}…` : v)}
                />
                <YAxis
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => `$${v.toFixed(2)}`}
                />
                <Tooltip
                  cursor={{ fill: "var(--surface-2)" }}
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                  formatter={(v: number) => [usd(v), "Cost"]}
                />
                <Bar
                  dataKey="cost_usd"
                  fill="url(#usagebar)"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={44}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="mt-4 w-full text-sm">
            <thead className="text-xs text-muted-foreground">
              <tr>
                <th className="py-2 text-left font-medium">
                  {g === "job" ? "Run" : g === "model" ? "Model" : "Step"}
                </th>
                <th className="py-2 text-right font-medium">Calls</th>
                <th className="py-2 text-right font-medium">Tokens in / out</th>
                <th className="py-2 text-right font-medium">Cost</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {rows.map((r) => (
                <tr key={r.key} className="border-t border-border">
                  <td className="max-w-[220px] truncate py-2 font-sans">{r.label}</td>
                  <td className="py-2 text-right">{num(r.calls)}</td>
                  <td className="py-2 text-right text-muted-foreground">
                    {num(r.input_tokens)} / {num(r.output_tokens)}
                  </td>
                  <td className="py-2 text-right">{usd(r.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

export function SettingsPage() {
  const { data: me } = useMe();
  const members = useMembers();
  const { theme, toggle } = useTheme();
  const [conn, setConn] = useState(false);
  const [url, setUrl] = useState("");
  const [health, setHealth] = useState<{ h?: Health; err?: string } | null>(null);

  useEffect(() => {
    if (conn) return;
    const u = getApiUrl();
    setUrl(u);
    setHealth(null);
    probe(u)
      .then((h) => setHealth({ h }))
      .catch((e: unknown) => setHealth({ err: e instanceof Error ? e.message : "Unreachable" }));
  }, [conn]);

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Settings" sub="Connection, AI usage and your team." />
      <div className="grid items-start gap-5 lg:grid-cols-3">
        <div className="space-y-5">
          <div className="card-halo p-5">
            <SectionTitle
              right={
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-lg"
                  onClick={() => setConn(true)}
                >
                  Change
                </Button>
              }
            >
              <span className="inline-flex items-center gap-2">
                <Server className="size-4" />
                Halo server
              </span>
            </SectionTitle>
            <p className="truncate font-mono text-sm">{url}</p>
            <div className="mt-3">
              {!health ? (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  Checking…
                </p>
              ) : health.h ? (
                <HealthLine h={health.h} />
              ) : (
                <p className="text-sm text-coral">Can't reach the server: {health.err}</p>
              )}
            </div>
          </div>
          <div className="card-halo p-5">
            <SectionTitle>You</SectionTitle>
            {me && (
              <div className="flex items-center gap-3">
                <span className="grid size-11 place-items-center rounded-full bg-signature font-bold text-primary-foreground">
                  {me.user.full_name
                    .split(/\s+/)
                    .map((w) => w[0])
                    .slice(0, 2)
                    .join("")
                    .toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="truncate font-semibold">{me.user.full_name}</p>
                  <p className="truncate text-sm text-muted-foreground">{me.user.email}</p>
                </div>
              </div>
            )}
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Workspace</dt>
                <dd>
                  {me?.workspace.name}
                  {me?.workspace.is_demo && (
                    <span className="ml-2 rounded-full bg-amber-500/15 px-2 text-[11px] text-amber-400">
                      Demo
                    </span>
                  )}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Role</dt>
                <dd>{me ? ROLE[me.role] : "—"}</dd>
              </div>
            </dl>
            <Button variant="outline" className="mt-4 w-full rounded-xl" onClick={toggle}>
              {theme === "dark" ? <Sun /> : <Moon />}
              {theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            </Button>
          </div>
          <div className="card-halo p-5">
            <SectionTitle>Team</SectionTitle>
            <ul className="space-y-2">
              {members.data?.map((m) => (
                <li key={m.id} className="flex items-center gap-3 text-sm">
                  <span className="grid size-8 place-items-center rounded-full bg-surface-2">
                    <UserRound className="size-4 text-muted-foreground" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate">{m.full_name}</p>
                    <p className="truncate text-xs text-muted-foreground">{m.email}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">{ROLE[m.role]}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <Usage />
      </div>
      <ConnectionDialog open={conn} onOpenChange={setConn} />
    </div>
  );
}
