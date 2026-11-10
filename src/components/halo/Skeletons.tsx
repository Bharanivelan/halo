import { Skeleton } from "@/components/ui/skeleton";

export function KpiSkeleton() {
  return <div className="card-halo p-5"><Skeleton className="h-3 w-24" /><Skeleton className="mt-4 h-8 w-20" /><Skeleton className="mt-2 h-3 w-32" /></div>;
}
export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card-halo space-y-3 p-5">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => <Skeleton key={i} className="h-3" style={{ width: `${90 - i * 15}%` }} />)}
    </div>
  );
}
export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="card-halo divide-y divide-border">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4"><Skeleton className="size-9 rounded-full" /><Skeleton className="h-3 flex-1" /><Skeleton className="h-5 w-16 rounded-full" /></div>
      ))}
    </div>
  );
}
