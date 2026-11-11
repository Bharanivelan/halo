import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, PlugZap, XCircle } from "lucide-react";
import { toast } from "sonner";
import { getApiUrl, setApiUrl } from "@/lib/halo-api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export type Health = {
  ok: boolean;
  llm_provider?: string;
  llm_configured?: boolean;
  search_configured?: boolean;
};

/** Probe a server URL without saving it. */
export async function probe(url: string): Promise<Health> {
  const res = await fetch(`${url.trim().replace(/\/+$/, "")}/readyz`, {
    headers: { "ngrok-skip-browser-warning": "1" },
  });
  if (!res.ok) throw new Error(`Server answered ${res.status}`);
  return (await res.json()) as Health;
}

export function HealthLine({ h }: { h: Health }) {
  return (
    <ul className="space-y-1 text-sm">
      <li className="flex items-center gap-2">
        <CheckCircle2 className="size-4 text-teal" />
        Halo API is reachable
      </li>
      <li className="flex items-center gap-2">
        {h.llm_configured ? (
          <CheckCircle2 className="size-4 text-teal" />
        ) : (
          <XCircle className="size-4 text-coral" />
        )}
        AI research{" "}
        {h.llm_configured ? `on (${h.llm_provider ?? "AI"})` : "off: add an AI key on the server"}
      </li>
      <li className="flex items-center gap-2">
        {h.search_configured ? (
          <CheckCircle2 className="size-4 text-teal" />
        ) : (
          <XCircle className="size-4 text-muted-foreground" />
        )}
        Web search {h.search_configured ? "on" : "off"}
      </li>
    </ul>
  );
}

type ProbeState =
  { kind: "idle" } | { kind: "busy" } | { kind: "ok"; h: Health } | { kind: "err"; msg: string };

export function ConnectionDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const [url, setUrl] = useState("");
  const [state, setState] = useState<ProbeState>({ kind: "idle" });

  useEffect(() => {
    if (open) {
      setUrl(getApiUrl());
      setState({ kind: "idle" });
    }
  }, [open]);

  const test = async () => {
    setState({ kind: "busy" });
    try {
      setState({ kind: "ok", h: await probe(url) });
    } catch (e) {
      setState({ kind: "err", msg: `Can't reach ${url}. ${e instanceof Error ? e.message : ""}` });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-2xl border-border bg-surface">
        <DialogHeader>
          <DialogTitle className="font-display">Connection settings</DialogTitle>
          <DialogDescription>
            Where is your Halo API running? Use a tunnel URL when the app runs on Lovable.
          </DialogDescription>
        </DialogHeader>
        <form
          id="conn"
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setApiUrl(url);
            toast.success("Server saved", { description: getApiUrl() });
            onOpenChange(false);
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="server-url">Server URL</Label>
            <div className="flex gap-2">
              <Input
                id="server-url"
                type="url"
                required
                placeholder="https://your-domain.ngrok-free.app"
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setState({ kind: "idle" });
                }}
                className="font-mono"
              />
              <Button
                type="button"
                variant="outline"
                onClick={test}
                disabled={!url || state.kind === "busy"}
              >
                {state.kind === "busy" ? <Loader2 className="animate-spin" /> : <PlugZap />}Test
              </Button>
            </div>
          </div>
          {state.kind === "ok" && (
            <div className="rounded-xl border border-teal/30 bg-teal/5 p-3">
              <HealthLine h={state.h} />
            </div>
          )}
          {state.kind === "err" && (
            <p className="rounded-xl border border-coral/30 bg-coral/5 p-3 text-sm text-coral">
              {state.msg}
            </p>
          )}
        </form>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="conn">
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
