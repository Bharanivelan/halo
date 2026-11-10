import { AgentPulse, EmptyState, KpiSkeleton, KpiTile, ScoreRing, SignalChip, TierBadge } from "@/components/halo";
import { PageHeader } from "./PlaceholderPage";

export function PortfolioPage() {
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title="Portfolio" sub="Every location and the prospects inside its halo." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Locations" value={null} sub="Connect the Halo API to load" />
        <KpiTile label="Prospects" value={null} sub="—" />
        <KpiTile label="Hot prospects" value={null} accent sub="—" />
        <KpiSkeleton />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="card-halo lg:col-span-2"><EmptyState title="No locations yet" text="Once Halo is connected, your pinned locations appear here with their catchment rings." /></div>
        <div className="card-halo space-y-5 p-5">
          <h2 className="text-sm font-semibold text-muted-foreground">Component preview</h2>
          <div className="flex justify-between">
            <ScoreRing value={82} kind="fit" label="Fit" />
            <ScoreRing value={64} kind="intent" label="Intent" />
            <ScoreRing value={null} kind="confidence" label="Confidence" />
          </div>
          <div className="flex flex-wrap gap-2"><TierBadge tier="A" /><TierBadge tier="B" /><TierBadge tier="C" /></div>
          <div className="flex flex-wrap gap-2"><SignalChip label="Hiring" age="6d" /><SignalChip label="Expansion" age="2w" /></div>
          <div className="flex items-center gap-2 text-sm text-violet"><AgentPulse /> <span className="font-mono">Agent idle preview</span></div>
          <p className="text-xs text-muted-foreground">Sample values shown for design review only.</p>
        </div>
      </div>
    </div>
  );
}
