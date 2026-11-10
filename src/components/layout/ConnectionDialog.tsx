import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

/** Server URL dialog. Saving is wired to the Halo API client in the next step. */
export function ConnectionDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [url, setUrl] = useState("");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-2xl border-border bg-surface">
        <DialogHeader>
          <DialogTitle className="font-display">Connection settings</DialogTitle>
          <DialogDescription>Point Halo at your Halo API server.</DialogDescription>
        </DialogHeader>
        <form id="conn" className="space-y-2" onSubmit={(e) => { e.preventDefault(); onOpenChange(false); }}>
          <Label htmlFor="server-url">Server URL</Label>
          <Input id="server-url" type="url" placeholder="https://api.example.com" value={url} onChange={(e) => setUrl(e.target.value)} className="font-mono" />
        </form>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" form="conn">Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
