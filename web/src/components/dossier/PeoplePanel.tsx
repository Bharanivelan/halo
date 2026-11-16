import { useState } from "react";
import {
  BadgeCheck,
  Ban,
  Link2,
  Loader2,
  Mail,
  Phone,
  Plus,
  Sparkles,
  Trash2,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";
import { EmptyState, SectionTitle, errorText } from "@/components/halo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAddContact, useDeleteContact, useReference } from "@/hooks/use-halo";
import { OFFERING_LABEL } from "@/lib/halo-format";
import type { AccountDetail, ContactInput, Offering } from "@/lib/halo-types";

const NONE = "__none";

export function PeoplePanel({
  account,
  onDraft,
}: {
  account: AccountDetail;
  onDraft: (p: { role_code?: string; offering?: Offering; contact_id?: string }) => void;
}) {
  const { data: ref } = useReference();
  const add = useAddContact(account.id, account.company.id);
  const del = useDeleteContact(account.id);
  const [open, setOpen] = useState(false);
  const empty: ContactInput = {
    full_name: "",
    title: "",
    role_code: null,
    email: "",
    phone: "",
    profile_url: "",
    source_note: "",
  };
  const [f, setF] = useState<ContactInput>(empty);
  const onErr = (e: unknown) => {
    const t = errorText(e);
    toast.error(t.title, { description: t.detail });
  };
  const clean = (v: string | null | undefined) => (v && v.trim() ? v.trim() : null);

  const submit = () =>
    add.mutate(
      {
        full_name: f.full_name.trim(),
        title: clean(f.title),
        role_code: f.role_code ?? null,
        email: clean(f.email),
        phone: clean(f.phone),
        profile_url: clean(f.profile_url),
        source_note: f.source_note.trim(),
      },
      {
        onSuccess: () => {
          toast.success("Contact added");
          setF(empty);
          setOpen(false);
        },
        onError: onErr,
      },
    );

  return (
    <div className="grid items-start gap-5 lg:grid-cols-2">
      <div className="card-halo p-5">
        <SectionTitle>Who to talk to</SectionTitle>
        {account.roles.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No role recommendations yet: research this company first.
          </p>
        ) : (
          <ol className="space-y-3">
            {account.roles.map((r) => (
              <li
                key={`${r.role_code}-${r.offering}`}
                className="flex gap-3 rounded-xl border border-border bg-surface-2/50 p-3.5"
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-signature font-mono text-sm font-bold text-primary-foreground">
                  {r.rank}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{r.label}</span>
                    <span className="rounded-full bg-gold/10 px-2 py-0.5 text-[11px] text-gold">
                      {OFFERING_LABEL[r.offering]}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{r.rationale}</p>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="-ml-2 mt-1 h-7 text-gold hover:text-gold"
                    onClick={() => onDraft({ role_code: r.role_code, offering: r.offering })}
                  >
                    <Sparkles />
                    Draft pitch for this role
                  </Button>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="card-halo p-5">
        <SectionTitle
          right={
            !open && (
              <Button
                size="sm"
                variant="outline"
                className="rounded-lg"
                onClick={() => setOpen(true)}
              >
                <Plus />
                Add contact
              </Button>
            )
          }
        >
          Contacts
        </SectionTitle>
        {account.company.do_not_contact && (
          <p className="mb-3 flex items-center gap-2 rounded-xl border border-coral/30 bg-coral/10 p-3 text-sm text-coral">
            <Ban className="size-4" />
            This company is marked do-not-contact.
          </p>
        )}
        {open && (
          <form
            className="mb-5 space-y-3 rounded-xl border border-gold/30 bg-gold/5 p-4"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="c-name">Full name</Label>
                <Input
                  id="c-name"
                  required
                  minLength={2}
                  value={f.full_name}
                  onChange={(e) => setF({ ...f, full_name: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-title">Job title</Label>
                <Input
                  id="c-title"
                  value={f.title ?? ""}
                  onChange={(e) => setF({ ...f, title: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-email">Email</Label>
                <Input
                  id="c-email"
                  type="email"
                  value={f.email ?? ""}
                  onChange={(e) => setF({ ...f, email: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-phone">Phone</Label>
                <Input
                  id="c-phone"
                  value={f.phone ?? ""}
                  onChange={(e) => setF({ ...f, phone: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label>Role</Label>
                <Select
                  value={f.role_code ?? NONE}
                  onValueChange={(v) => setF({ ...f, role_code: v === NONE ? null : v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>Not sure</SelectItem>
                    {ref?.role_codes.map((r) => (
                      <SelectItem key={r.code} value={r.code}>
                        {r.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="c-url">Profile link</Label>
                <Input
                  id="c-url"
                  type="url"
                  value={f.profile_url ?? ""}
                  onChange={(e) => setF({ ...f, profile_url: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label htmlFor="c-src">Where did you get this?</Label>
              <Input
                id="c-src"
                required
                minLength={3}
                placeholder="e.g. Met at CII event, company website team page"
                value={f.source_note}
                onChange={(e) => setF({ ...f, source_note: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={add.isPending}>
                {add.isPending && <Loader2 className="animate-spin" />}Save contact
              </Button>
            </div>
          </form>
        )}
        {account.contacts.length === 0 && !open ? (
          <EmptyState
            title="No contacts yet"
            text="Halo doesn't guess personal details. Add the people you know, or use the recommended roles to find them."
          />
        ) : (
          <ul className="space-y-2">
            {account.contacts.map((c) => (
              <li key={c.id} className="group flex gap-3 rounded-xl border border-border p-3.5">
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-surface-2">
                  <UserRound className="size-4 text-muted-foreground" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{c.full_name}</span>
                    {c.verification_status !== "unverified" && (
                      <BadgeCheck className="size-4 text-teal" aria-label="Verified" />
                    )}
                    {c.do_not_contact && (
                      <span className="rounded-full bg-coral/15 px-2 text-[11px] text-coral">
                        Do not contact
                      </span>
                    )}
                  </div>
                  {c.title && <div className="text-sm text-muted-foreground">{c.title}</div>}
                  <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                    {c.email && (
                      <a
                        href={`mailto:${c.email}`}
                        className="inline-flex items-center gap-1 hover:text-gold"
                      >
                        <Mail className="size-3" />
                        {c.email}
                      </a>
                    )}
                    {c.phone && (
                      <a
                        href={`tel:${c.phone}`}
                        className="inline-flex items-center gap-1 hover:text-gold"
                      >
                        <Phone className="size-3" />
                        {c.phone}
                      </a>
                    )}
                    {c.profile_url && (
                      <a
                        href={c.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 hover:text-gold"
                      >
                        <Link2 className="size-3" />
                        Profile
                      </a>
                    )}
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">Source: {c.source_note}</p>
                  {!c.do_not_contact && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="-ml-2 mt-1 h-7 text-gold hover:text-gold"
                      onClick={() =>
                        onDraft({
                          contact_id: c.id,
                          ...(c.role_code ? { role_code: c.role_code } : {}),
                        })
                      }
                    >
                      <Sparkles />
                      Draft pitch to {c.full_name.split(" ")[0]}
                    </Button>
                  )}
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                  aria-label="Delete contact"
                  onClick={() => {
                    if (confirm(`Delete ${c.full_name}?`)) del.mutate(c.id, { onError: onErr });
                  }}
                >
                  <Trash2 className="text-coral" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
