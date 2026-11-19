/**
 * Halo API client. Single fetch wrapper for the whole app.
 *
 * - Server URL is a runtime setting (the demo backend sits behind a tunnel whose URL changes),
 *   stored in localStorage; falls back to VITE_HALO_API_URL, then DEFAULT_API_URL.
 * - Auth: bearer token from POST /auth/login (sent with X-Auth-Mode: token). No cookies, no CSRF.
 * - Errors: RFC 9457 problem+json parsed into ApiError.
 * - 401 clears the token and fires "halo:signed-out" so the app can route to /login.
 */
import type {
  AccountDetail,
  AccountListItem,
  Activity,
  CopilotOutput,
  DiscoveryConfig,
  DiscoveryResult,
  Estimate,
  GeocodeResult,
  JobDetail,
  JobSummary,
  LoginResponse,
  AuthOptions,
  SignupInput,
  MapPoint,
  Me,
  Member,
  Opportunity,
  Overview,
  Page,
  ParseResult,
  ProblemDetails,
  Property,
  PropertyInput,
  PropertySummary,
  ReferenceData,
  Contact,
  ContactInput,
  OpportunityInput,
  UsageRow,
  CsvImport,
  Offering,
  AgentVersion,
  LabSummary,
  LeadFeedback,
  LeadVerdict,
  RatingsImport,
  SignalVerdict,
} from "./halo-types";

// Demo tunnel to the Halo API (Cloudflare quick tunnel; changes on restart, so update here or via Connection settings).
export const DEFAULT_API_URL = "https://pillow-picks-textiles-interim.trycloudflare.com";
const URL_KEY = "halo.apiUrl";
const TOKEN_KEY = "halo.token";

function store(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

// Free tunnel addresses change on every restart. A remembered one that differs from the current
// default is stale, so it is dropped instead of leaving the browser stuck on a dead server.
const ROTATING_TUNNEL = /\.(lhr\.life|trycloudflare\.com|ngrok-free\.app|ngrok\.io)$/i;
function isStaleTunnel(url: string): boolean {
  try {
    const host = new URL(url).host;
    return ROTATING_TUNNEL.test(host) && host !== new URL(DEFAULT_API_URL).host;
  } catch {
    return true;
  }
}

export function getApiUrl(): string {
  let saved = store()?.getItem(URL_KEY);
  if (saved && isStaleTunnel(saved)) {
    store()?.removeItem(URL_KEY);
    saved = null;
  }
  const env = (import.meta as { env?: Record<string, string | undefined> }).env?.[
    "VITE_HALO_API_URL"
  ];
  return (saved || env || DEFAULT_API_URL).replace(/\/+$/, "");
}
export function setApiUrl(url: string) {
  store()?.setItem(URL_KEY, url.trim().replace(/\/+$/, ""));
}
export function getToken(): string | null {
  return store()?.getItem(TOKEN_KEY) ?? null;
}
function setToken(t: string | null) {
  const s = store();
  if (!s) return;
  if (t) s.setItem(TOKEN_KEY, t);
  else s.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  readonly status: number;
  readonly title: string;
  readonly detail: string | undefined;
  readonly errors: { field: string; code: string; message: string }[];
  constructor(status: number, p: Partial<ProblemDetails>) {
    super(p.detail || p.title || `Request failed (${status})`);
    this.status = status;
    this.title =
      p.title ||
      (status === 0
        ? "Can't reach the Halo server"
        : status === 401
          ? "You're signed out"
          : "Request failed");
    this.detail = p.detail;
    this.errors = p.errors ?? [];
  }
}

type Query = Record<string, string | number | boolean | null | undefined | (string | number)[]>;

function buildUrl(path: string, query?: Query) {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) {
      if (v.length) params.set(k, v.join(","));
    } else params.set(k, String(v));
  }
  const qs = params.toString();
  return `${getApiUrl()}/api/v1${path}${qs ? `?${qs}` : ""}`;
}

// Endpoints that work without signing in.
const PUBLIC_PATHS = new Set(["/auth/login", "/auth/signup", "/auth/options"]);

async function request<T>(
  path: string,
  opts: {
    method?: string;
    query?: Query | undefined;
    body?: unknown;
    form?: FormData;
    headers?: Record<string, string>;
    raw?: boolean;
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json, application/problem+json",
    // Skips the free-ngrok browser warning page when the API is reached through an ngrok tunnel (D-37).
    "ngrok-skip-browser-warning": "1",
    ...(opts.headers ?? {}),
  };
  const token = getToken();
  // Signed out: don't call the server at all (screens still mounted during sign-out would loop on 401s).
  if (!token && !PUBLIC_PATHS.has(path)) throw new ApiError(401, { detail: "Please sign in." });
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let body: BodyInit | null = null;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), { method: opts.method ?? "GET", headers, body });
  } catch {
    throw new ApiError(0, {
      detail: `Check the server URL (${getApiUrl()}) and that the Halo API is running.`,
    });
  }
  if (res.status === 401 && !PUBLIC_PATHS.has(path)) {
    setToken(null);
    window.dispatchEvent(new Event("halo:signed-out"));
  }
  if (!res.ok) {
    let p: Partial<ProblemDetails> = {};
    try {
      p = await res.json();
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, p);
  }
  if (opts.raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return (res.headers.get("content-type") ?? "").includes("json")
    ? ((await res.json()) as T)
    : (undefined as T);
}

const get = <T>(p: string, q?: Query) => request<T>(p, { query: q });
const post = <T>(p: string, b?: unknown) => request<T>(p, { method: "POST", body: b ?? {} });
const patch = <T>(p: string, b: unknown) => request<T>(p, { method: "PATCH", body: b });
const put = <T>(p: string, b: unknown) => request<T>(p, { method: "PUT", body: b });
const del = (p: string) => request<void>(p, { method: "DELETE" });

export type AccountFilters = {
  q?: string;
  status?: string;
  tier?: string;
  industry?: string;
  distance_max_km?: number;
  owner?: string;
  min_fit?: number;
  min_intent?: number;
  has_signal?: boolean;
  job_id?: string;
  ids?: string[];
  sort?: string;
  limit?: number;
  cursor?: string;
};

export const halo = {
  /* Auth */
  async login(email: string, password: string): Promise<Me> {
    const r = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      headers: { "X-Auth-Mode": "token" },
    });
    setToken(r.access_token);
    return r;
  },
  async logout() {
    try {
      await post<void>("/auth/logout");
    } finally {
      setToken(null);
    }
  },
  async signup(input: SignupInput): Promise<Me> {
    const r = await request<LoginResponse>("/auth/signup", {
      method: "POST",
      body: input,
      headers: { "X-Auth-Mode": "token" },
    });
    setToken(r.access_token);
    return r;
  },
  authOptions: () => get<AuthOptions>("/auth/options"),
  me: () => get<Me>("/auth/me"),
  isSignedIn: () => !!getToken(),

  /* Reference & workspace */
  reference: () => get<ReferenceData>("/reference"),
  members: () => get<Member[]>("/members"),
  geocode: (q: string, country?: string) => get<GeocodeResult[]>("/geocode", { q, country }),
  health: async () =>
    (
      await fetch(`${getApiUrl()}/readyz`, { headers: { "ngrok-skip-browser-warning": "1" } })
    ).json() as Promise<{
      ok: boolean;
      llm_provider: string;
      llm_configured: boolean;
      search_configured: boolean;
    }>,

  /* Properties (locations) */
  properties: () => get<PropertySummary[]>("/properties"),
  property: (id: string) => get<Property>(`/properties/${id}`),
  createProperty: (input: PropertyInput) => post<Property>("/properties", input),
  updateProperty: (id: string, input: Partial<PropertyInput>) =>
    patch<Property>(`/properties/${id}`, input),
  deleteProperty: (id: string) => request<void>(`/properties/${id}`, { method: "DELETE" }),
  overview: (id: string) => get<Overview>(`/properties/${id}/overview`),
  importCsv: (id: string, file: File) => {
    const f = new FormData();
    f.append("file", file);
    return request<CsvImport>(`/properties/${id}/imports`, { method: "POST", form: f });
  },

  /* Discovery (the agent run) */
  estimate: (config: DiscoveryConfig) => post<Estimate>("/discovery/estimate", { config }),
  parseRequest: (property_id: string, text: string, current_config: DiscoveryConfig) =>
    post<ParseResult>("/discovery/parse-request", { property_id, text, current_config }),
  startRun: (config: DiscoveryConfig) =>
    post<{ job_id: string; status: string }>("/discovery/jobs", { config }),
  runs: (property_id?: string) => get<JobSummary[]>("/discovery/jobs", { property_id }),
  run: (id: string) => get<JobDetail>(`/discovery/jobs/${id}`), // poll every 2s while queued|running|cancelling
  cancelRun: (id: string) => post<JobDetail>(`/discovery/jobs/${id}/cancel`),
  resumeRun: (id: string, budget_usd?: number) =>
    post<JobDetail>(`/discovery/jobs/${id}/resume`, { budget_usd }),
  retryFailed: (id: string) => post<JobDetail>(`/discovery/jobs/${id}/retry-failed`),
  runResults: (id: string, outcome?: string) =>
    get<DiscoveryResult[]>(`/discovery/jobs/${id}/results`, { outcome }),

  /* Accounts */
  accounts: (propertyId: string, f: AccountFilters = {}) =>
    get<Page<AccountListItem>>(`/properties/${propertyId}/accounts`, f as Query),
  accountsMap: (propertyId: string) => get<MapPoint[]>(`/properties/${propertyId}/accounts/map`),
  account: (id: string) => get<AccountDetail>(`/accounts/${id}`),
  updateAccount: (
    id: string,
    b: {
      status?: string;
      owner_membership_id?: string | null;
      dismissed_reason?: string;
      dismissed_note?: string;
    },
  ) => patch<AccountDetail>(`/accounts/${id}`, b),
  reResearch: (id: string) => post<{ job_id: string }>(`/accounts/${id}/research`),
  bulk: (
    propertyId: string,
    b: {
      account_ids: string[];
      action: "assign" | "set_status" | "dismiss";
      owner_membership_id?: string;
      status?: string;
      dismissed_reason?: string;
    },
  ) => post<{ updated: number }>(`/properties/${propertyId}/accounts/bulk`, b),
  /** Downloads the CSV (needs the bearer token, so a plain <a href> won't work). */
  async downloadAccountsCsv(
    propertyId: string,
    f: AccountFilters = {},
    fileName = "halo-accounts.csv",
  ) {
    const res = await request<Response>(`/properties/${propertyId}/accounts/export.csv`, {
      query: f as Query,
      raw: true,
    });
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },

  /* Contacts */
  contacts: (propertyId: string, q?: string) =>
    get<Contact[]>(`/properties/${propertyId}/contacts`, { q }),
  addContact: (companyId: string, c: ContactInput) =>
    post<Contact>(`/companies/${companyId}/contacts`, c),
  updateContact: (id: string, c: Partial<ContactInput> & { do_not_contact?: boolean }) =>
    patch<Contact>(`/contacts/${id}`, c),
  deleteContact: (id: string) => request<void>(`/contacts/${id}`, { method: "DELETE" }),

  /* Pitch copilot (drafts only — never sends) */
  generatePitch: (
    accountId: string,
    b: { offering: Offering; contact_id?: string; role_code?: string; tone?: "warm" | "formal" },
  ) => post<CopilotOutput>(`/accounts/${accountId}/copilot`, b), // 10–40s
  pitches: (accountId: string) => get<CopilotOutput[]>(`/accounts/${accountId}/copilot`),
  editPitch: (id: string, b: { subject: string; body: string }) =>
    patch<CopilotOutput>(`/copilot-outputs/${id}`, b),
  pitchCopied: (id: string) => post<CopilotOutput>(`/copilot-outputs/${id}/copied`),
  pitchSent: (id: string) => post<CopilotOutput>(`/copilot-outputs/${id}/mark-sent`),

  /* Pipeline */
  opportunities: (propertyId: string) =>
    get<Opportunity[]>(`/properties/${propertyId}/opportunities`),
  createOpportunity: (accountId: string, b: OpportunityInput) =>
    post<Opportunity>(`/accounts/${accountId}/opportunities`, b),
  updateOpportunity: (
    id: string,
    b: Partial<OpportunityInput> & { stage?: string; loss_reason?: string; loss_note?: string },
  ) => patch<Opportunity>(`/opportunities/${id}`, b),
  activities: (accountId: string) => get<Activity[]>(`/accounts/${accountId}/activities`),
  addActivity: (
    accountId: string,
    b: { type: "note" | "call" | "meeting" | "email_sent"; body: string; opportunity_id?: string },
  ) => post<Activity>(`/accounts/${accountId}/activities`, b),

  /* Halo Lab (D-47) */
  rateProspect: (
    id: string,
    b: { verdict: LeadVerdict; reason?: string | null; note?: string | null },
  ) => put<LeadFeedback>(`/accounts/${id}/feedback`, b),
  clearRating: (id: string) => del(`/accounts/${id}/feedback`),
  rateSignal: (id: string, verdict: SignalVerdict) =>
    put<{ signal_id: string; verdict: SignalVerdict }>(`/signals/${id}/feedback`, { verdict }),
  clearSignalRating: (id: string) => del(`/signals/${id}/feedback`),
  labSummary: () => get<LabSummary>("/lab/summary"),
  labVersions: () => get<AgentVersion[]>("/lab/versions"),
  importRatings: (propertyId: string, file: File) => {
    const f = new FormData();
    f.append("file", file);
    return request<RatingsImport>(`/lab/ratings/import`, {
      method: "POST",
      form: f,
      query: { property_id: propertyId },
    });
  },
  startLabRun: (propertyId: string) =>
    post<{ job_id: string }>("/lab/runs", { property_id: propertyId }),
  approveVersion: (id: string) => post<AgentVersion>(`/lab/versions/${id}/approve`),
  rejectVersion: (id: string) => post<AgentVersion>(`/lab/versions/${id}/reject`),
  activateVersion: (id: string) => post<AgentVersion>(`/lab/versions/${id}/activate`),

  /* Usage */
  usage: (group_by: "step" | "model" | "job" = "step", days = 30) =>
    get<UsageRow[]>("/activity/usage", { group_by, days }),
};
