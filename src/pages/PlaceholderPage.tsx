import type { ReactNode } from "react";
import { EmptyState } from "@/components/halo";

export function PageHeader({ title, sub, right }: { title: string; sub?: string | undefined; right?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="text-[32px] font-bold leading-tight">{title}</h1>{sub && <p className="mt-1 text-muted-foreground">{sub}</p>}</div>
      {right}
    </div>
  );
}

export function PlaceholderPage({ title, sub, emptyTitle, emptyText }: { title: string; sub?: string; emptyTitle: string; emptyText: string }) {
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title={title} sub={sub} />
      <div className="card-halo"><EmptyState title={emptyTitle} text={emptyText} /></div>
    </div>
  );
}
