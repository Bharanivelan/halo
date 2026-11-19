/**
 * TanStack Query hooks over the Halo API client. All screens read and write data through these.
 */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { halo, type AccountFilters } from "@/lib/halo-api";
import type {
  DiscoveryConfig,
  JobStatus,
  Offering,
  OpportunityInput,
  PropertyInput,
  ContactInput,
  LeadVerdict,
  SignalVerdict,
} from "@/lib/halo-types";

export const ACTIVE_JOB: JobStatus[] = ["queued", "running", "cancelling"];
export const isJobActive = (s?: JobStatus) => !!s && ACTIVE_JOB.includes(s);

/* ── Session & reference ── */
export const useMe = () =>
  useQuery({
    queryKey: ["me"],
    queryFn: halo.me,
    enabled: halo.isSignedIn(),
    staleTime: 60_000,
    retry: false,
  });
export const useReference = () =>
  useQuery({
    queryKey: ["reference"],
    queryFn: halo.reference,
    enabled: halo.isSignedIn(),
    staleTime: 5 * 60_000,
  });
export const useMembers = () =>
  useQuery({ queryKey: ["members"], queryFn: halo.members, staleTime: 5 * 60_000 });
export const useHealth = () =>
  useQuery({ queryKey: ["health"], queryFn: halo.health, retry: false });

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      halo.login(email, password),
    onSuccess: (me) => {
      qc.clear();
      qc.setQueryData(["me"], me);
    },
  });
}
export function useSignup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: halo.signup,
    onSuccess: (me) => {
      qc.clear();
      qc.setQueryData(["me"], me);
    },
  });
}
/** Public: which sign-in options this server offers (sign-up on/off; Google later). */
export const useAuthOptions = () =>
  useQuery({
    queryKey: ["auth-options"],
    queryFn: halo.authOptions,
    retry: false,
    staleTime: 5 * 60_000,
  });
export function useLogout() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: halo.logout, onSettled: () => qc.clear() });
}

/* ── Locations ── */
export const useProperties = () => useQuery({ queryKey: ["properties"], queryFn: halo.properties });
export const useProperty = (id?: string) =>
  useQuery({ queryKey: ["property", id], queryFn: () => halo.property(id!), enabled: !!id });
export const useOverview = (id?: string) =>
  useQuery({
    queryKey: ["overview", id],
    queryFn: () => halo.overview(id!),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data?.running_jobs?.some((j) => isJobActive(j.status)) ? 5000 : false,
  });
export const useGeocode = (q: string, country?: string) =>
  useQuery({
    queryKey: ["geocode", q, country],
    queryFn: () => halo.geocode(q, country),
    enabled: q.trim().length >= 3,
    staleTime: 10 * 60_000,
  });
export function useCreateProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: PropertyInput) => halo.createProperty(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["properties"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
export function useDeleteProperty() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => halo.deleteProperty(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["properties"] });
      qc.invalidateQueries({ queryKey: ["runs"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

/** Distance unit and currency for a project, from the cached project list. Defaults to US. */
export function useProjectUnits(id?: string) {
  const { data } = useQuery({ queryKey: ["properties"], queryFn: halo.properties });
  const p = data?.find((x) => x.id === id);
  return { unit: p?.distance_unit ?? "mi", currency: p?.currency ?? "USD" } as const;
}

export function useUpdateProperty(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: Partial<PropertyInput>) => halo.updateProperty(id, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["property", id] });
      qc.invalidateQueries({ queryKey: ["properties"] });
    },
  });
}

/* ── Agent runs ── */
export const useEstimate = (config: DiscoveryConfig | null) =>
  useQuery({
    queryKey: ["estimate", config],
    queryFn: () => halo.estimate(config!),
    enabled: !!config,
    placeholderData: keepPreviousData,
  });
export const useParseRequest = () =>
  useMutation({
    mutationFn: (a: { propertyId: string; text: string; config: DiscoveryConfig }) =>
      halo.parseRequest(a.propertyId, a.text, a.config),
  });
export function useStartRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (c: DiscoveryConfig) => halo.startRun(c),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });
}
/** Data that changes while the agent works: refreshed on every live poll and once more when a run ends. */
const LIVE_KEYS = [["accounts-map"], ["properties"], ["overview"], ["accounts"]] as const;
function refreshLive(qc: ReturnType<typeof useQueryClient>) {
  for (const k of LIVE_KEYS) void qc.invalidateQueries({ queryKey: [...k] });
}

export function useRuns(propertyId?: string) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["runs", propertyId],
    queryFn: async () => {
      const prev = qc.getQueryData<{ id: string; status: JobStatus }[]>(["runs", propertyId]);
      const next = await halo.runs(propertyId);
      const wasActive = prev?.some((j) => isJobActive(j.status)) ?? false;
      if (wasActive || next.some((j) => isJobActive(j.status))) refreshLive(qc);
      return next;
    },
    refetchInterval: (q) => (q.state.data?.some((j) => isJobActive(j.status)) ? 4000 : false),
  });
}
export function useRun(id?: string) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["run", id],
    queryFn: async () => {
      const prev = qc.getQueryData<{ status: JobStatus }>(["run", id]);
      const next = await halo.run(id!);
      if (isJobActive(prev?.status) && !isJobActive(next.status)) {
        refreshLive(qc);
        void qc.invalidateQueries({ queryKey: ["runs"] });
      }
      return next;
    },
    enabled: !!id,
    // Poll while the run is live; stop on errors (e.g. 404) instead of retrying forever.
    refetchInterval: (q) =>
      q.state.status === "error"
        ? false
        : isJobActive(q.state.data?.status) || !q.state.data
          ? 2000
          : false,
  });
}
function useRunAction<A, R>(fn: (a: A) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["run"] });
      qc.invalidateQueries({ queryKey: ["runs"] });
    },
  });
}
export const useCancelRun = () => useRunAction((id: string) => halo.cancelRun(id));
export const useRetryFailed = () => useRunAction((id: string) => halo.retryFailed(id));
export const useResumeRun = () =>
  useRunAction((a: { id: string; budget: number }) => halo.resumeRun(a.id, a.budget));

/* ── Prospects ── */
export const useAccounts = (
  propertyId?: string,
  filters: AccountFilters = {},
  opts: { live?: boolean } = {},
) =>
  useQuery({
    queryKey: ["accounts", propertyId, filters],
    queryFn: () => halo.accounts(propertyId!, filters),
    enabled: !!propertyId,
    placeholderData: keepPreviousData,
    refetchInterval: opts.live ? 5000 : false,
  });
export const useAccountsMap = (propertyId?: string) =>
  useQuery({
    queryKey: ["accounts-map", propertyId],
    queryFn: () => halo.accountsMap(propertyId!),
    enabled: !!propertyId,
  });
/** After "Re-research", keep the dossier fresh for a few minutes so new evidence appears without a reload. */
const refreshUntil = new Map<string, number>();
export const useAccount = (id?: string) =>
  useQuery({
    queryKey: ["account", id],
    queryFn: () => halo.account(id!),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data?.company.research_status === "researching" ||
      (id && (refreshUntil.get(id) ?? 0) > Date.now())
        ? 4000
        : false,
  });

function useAccountMutation<A, R>(fn: (a: A) => Promise<R>, accountId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      if (accountId) qc.invalidateQueries({ queryKey: ["account", accountId] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}
export const useUpdateAccount = (id: string) =>
  useAccountMutation(
    (b: Parameters<typeof halo.updateAccount>[1]) => halo.updateAccount(id, b),
    id,
  );
export const useReResearch = (id: string) =>
  useAccountMutation(() => {
    refreshUntil.set(id, Date.now() + 3 * 60_000);
    return halo.reResearch(id);
  }, id);
export const useBulk = (propertyId: string) =>
  useAccountMutation((b: Parameters<typeof halo.bulk>[1]) => halo.bulk(propertyId, b));

/* ── Contacts ── */
export const useAddContact = (accountId: string, companyId: string) =>
  useAccountMutation((c: ContactInput) => halo.addContact(companyId, c), accountId);
export const useDeleteContact = (accountId: string) =>
  useAccountMutation((id: string) => halo.deleteContact(id), accountId);

/* ── Pitch ── */
export const usePitches = (accountId?: string) =>
  useQuery({
    queryKey: ["pitches", accountId],
    queryFn: () => halo.pitches(accountId!),
    enabled: !!accountId,
  });
function usePitchMutation<A, R>(accountId: string, fn: (a: A) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pitches", accountId] });
      qc.invalidateQueries({ queryKey: ["account", accountId] });
    },
  });
}
export const useGeneratePitch = (accountId: string) =>
  usePitchMutation(
    accountId,
    (b: {
      offering: Offering;
      contact_id?: string;
      role_code?: string;
      tone?: "warm" | "formal";
    }) => halo.generatePitch(accountId, b),
  );
export const useEditPitch = (accountId: string) =>
  usePitchMutation(accountId, (a: { id: string; subject: string; body: string }) =>
    halo.editPitch(a.id, { subject: a.subject, body: a.body }),
  );
export const usePitchCopied = (accountId: string) =>
  usePitchMutation(accountId, (id: string) => halo.pitchCopied(id));
export const usePitchSent = (accountId: string) =>
  usePitchMutation(accountId, (id: string) => halo.pitchSent(id));

/* ── Pipeline ── */
export const useOpportunities = (propertyId?: string) =>
  useQuery({
    queryKey: ["opps", propertyId],
    queryFn: () => halo.opportunities(propertyId!),
    enabled: !!propertyId,
  });
export function useCreateOpportunity(accountId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: OpportunityInput) => halo.createOpportunity(accountId, b),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["opps"] });
      qc.invalidateQueries({ queryKey: ["account", accountId] });
    },
  });
}
export function useUpdateOpportunity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (a: { id: string } & Parameters<typeof halo.updateOpportunity>[1]) => {
      const { id, ...b } = a;
      return halo.updateOpportunity(id, b);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["opps"] });
      qc.invalidateQueries({ queryKey: ["account"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}
export const useAddActivity = (accountId: string) =>
  useAccountMutation(
    (b: Parameters<typeof halo.addActivity>[1]) => halo.addActivity(accountId, b),
    accountId,
  );

/* ── Usage ── */
export const useUsage = (group_by: "step" | "model" | "job") =>
  useQuery({ queryKey: ["usage", group_by], queryFn: () => halo.usage(group_by) });

/* ── Halo Lab (D-47) ── */
function useLabMutation<A, R>(fn: (a: A) => Promise<R>, accountId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      if (accountId) qc.invalidateQueries({ queryKey: ["account", accountId] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      qc.invalidateQueries({ queryKey: ["lab"] });
    },
  });
}
/** Rate a prospect 👍/👎. Pass verdict null to clear the rating. */
export function useRateProspect() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      verdict,
      reason,
    }: {
      id: string;
      verdict: LeadVerdict | null;
      reason?: string | null | undefined;
    }) => {
      if (verdict) await halo.rateProspect(id, { verdict, reason: reason ?? null });
      else await halo.clearRating(id);
    },
    onSuccess: (_r, v) => {
      qc.invalidateQueries({ queryKey: ["account", v.id] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      qc.invalidateQueries({ queryKey: ["lab"] });
    },
  });
}
export const useRateSignal = (accountId: string) =>
  useLabMutation(async ({ id, verdict }: { id: string; verdict: SignalVerdict | null }) => {
    if (verdict) await halo.rateSignal(id, verdict);
    else await halo.clearSignalRating(id);
  }, accountId);
export const useLabSummary = (opts: { live?: boolean } = {}) =>
  useQuery({
    queryKey: ["lab", "summary"],
    queryFn: halo.labSummary,
    refetchInterval: opts.live ? 3000 : false,
  });
export const useLabVersions = () =>
  useQuery({ queryKey: ["lab", "versions"], queryFn: halo.labVersions });
export const useImportRatings = (propertyId: string) =>
  useLabMutation((file: File) => halo.importRatings(propertyId, file));
export const useStartLabRun = () =>
  useLabMutation((propertyId: string) => halo.startLabRun(propertyId));
export function useDecideVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" | "activate" }) =>
      action === "approve"
        ? halo.approveVersion(id)
        : action === "reject"
          ? halo.rejectVersion(id)
          : halo.activateVersion(id),
    onSuccess: () => {
      // Approving or rolling back re-scores every prospect.
      qc.invalidateQueries({ queryKey: ["lab"] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      qc.invalidateQueries({ queryKey: ["accounts-map"] });
      qc.invalidateQueries({ queryKey: ["account"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["properties"] });
    },
  });
}
