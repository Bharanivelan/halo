/**
 * Halo API v1 — TypeScript contract. Generated from the backend; do not edit by hand.
 * Base path: <API_URL>/api/v1. All timestamps are ISO-8601 UTC strings. All ids are UUID strings.
 * Auth for this app: Authorization: Bearer <access_token> (from POST /auth/login with header X-Auth-Mode: token).
 * No CSRF header is needed with a bearer token. Errors are RFC 9457 problem+json: see ProblemDetails.
 */

export type UUID = string;
export type ISODate = string; // "2026-11-09T06:30:00Z" or "2026-11-09"

/* ───────── Errors ───────── */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  request_id?: string;
  errors?: { field: string; code: string; message: string }[];
}

/* ───────── Enums ───────── */
export type Role = "admin" | "manager" | "rep";
export type Offering = "corporate_rate" | "mice" | "long_stay" | "fnb";
export type Lifecycle = "pre_opening" | "operating";
export type DataOrigin = "real" | "mock" | "manual";
export type AccountStatus =
  | "discovered"
  | "qualified"
  | "contact_identified"
  | "outreach_prepared"
  | "outreach_sent"
  | "engaged"
  | "dismissed";
export type OpportunityStage = "interested" | "meeting_scheduled" | "negotiation" | "won" | "lost";
export type Tier = "A" | "B" | "C";
export type Actionability = "none" | "roles_identified" | "contact_available";
export type ClaimKind = "fact" | "inference" | "unknown";
export type GroundingStatus = "passed" | "passed_fuzzy" | "failed" | "not_applicable";
export type JobStatus =
  | "queued"
  | "running"
  | "paused_budget"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | "cancelling"
  | "cancelled";
export type StageStatus = "pending" | "running" | "succeeded" | "failed" | "partial" | "skipped";
export type ResearchStatus = "not_researched" | "researching" | "researched" | "failed";
export type SourceType =
  | "website"
  | "news"
  | "search_result"
  | "osm"
  | "google_places"
  | "csv_import"
  | "manual"
  | "provider";
export type ActivityType =
  | "note"
  | "call"
  | "meeting"
  | "email_sent"
  | "status_change"
  | "stage_change"
  | "draft_copied"
  | "system";
export type ProviderKey = "osm" | "web_search" | "csv" | "google_places";
export type DismissReason =
  | "not_relevant_industry"
  | "too_small"
  | "too_far"
  | "already_customer"
  | "competitor_relationship"
  | "bad_data"
  | "duplicate"
  | "other";
export type LossReason =
  | "price"
  | "location"
  | "existing_hotel_contract"
  | "no_current_need"
  | "chose_competitor"
  | "no_response"
  | "other";

/* ───────── Reference data: GET /reference ───────── */
export interface Option<T extends string = string> {
  code: T;
  label: string;
}
export interface ReferenceData {
  industries: Option[];
  offerings: Option<Offering>[];
  account_statuses: Option<AccountStatus>[];
  opportunity_stages: Option<OpportunityStage>[];
  dismiss_reasons: Option<DismissReason>[];
  loss_reasons: Option<LossReason>[];
  signal_types: Option[];
  role_codes: Option[];
  providers: { key: ProviderKey; label: string; enabled: boolean; reason?: string }[];
  regions: Region[];
  default_country: CountryCode;
  llm_configured: boolean;
  search_configured: boolean;
  scoring: {
    tier_a_min: number;
    tier_b_min: number;
    signal_window_days: number;
    fresh_days: number;
  };
}

/** Any ISO 3166-1 alpha-2 country (D-43). Currency and distance unit follow the project's country. */
export type CountryCode = string;
export type DistanceUnit = "mi" | "km";
export interface Region {
  code: CountryCode;
  label: string;
  currency: string;
  distance_unit: DistanceUnit;
  locale: string;
  default_radius_km: number;
}

/* ───────── Auth ───────── */
export interface LoginRequest {
  email: string;
  password: string;
}
export interface LoginResponse extends Me {
  access_token: string;
  token_type: "bearer";
}
export interface Me {
  user: { id: UUID; email: string; full_name: string };
  workspace: { id: UUID; name: string; is_demo: boolean };
  role: Role;
  membership_id: UUID;
  csrf_token: string;
  properties: PropertySummary[];
}
// POST /auth/login (header X-Auth-Mode: token) -> LoginResponse ; POST /auth/logout -> 204 ; GET /auth/me -> Me (401 if not signed in)

/* ───────── Members: GET /members ───────── */
export interface Member {
  id: UUID /* membership id */;
  full_name: string;
  email: string;
  role: Role;
}

/* ───────── Properties ───────── */
export interface GeoPoint {
  lat: number;
  lng: number;
}
export interface TargetProfile {
  radius_km: number;
  industries: string[]; // industry codes
  employee_min: number | null;
  employee_max: number | null;
  notes: string | null;
}
export interface PropertySummary {
  id: UUID;
  name: string;
  brand: string | null;
  locality: string | null;
  city: string | null;
  lifecycle: Lifecycle;
  opening_date: ISODate | null;
  is_hypothetical: boolean;
  location: GeoPoint;
  radius_km: number;
  account_count: number;
  country: CountryCode;
  currency: string;
  distance_unit: DistanceUnit;
  created_at: ISODate;
  /** Most recent agent run for this project, if any. */
  latest_job: { id: UUID; status: JobStatus; created_at: ISODate; finished_at: ISODate | null } | null;
}
export interface Property extends PropertySummary {
  address_line: string | null;
  state: string | null;
  postal_code: string | null;
  rooms_count: number | null;
  meeting_rooms_count: number | null;
  largest_meeting_capacity: number | null;
  banquet_capacity: number | null;
  restaurants_count: number | null;
  facilities: string[];
  description: string | null;
  offerings: Offering[];
  target: TargetProfile;
  /** Present when the project was created with start_agent: the first run's id. */
  started_job_id?: UUID;
}
export type PropertyInput = Omit<
  Property,
  | "id"
  | "account_count"
  | "created_at"
  | "radius_km"
  | "currency"
  | "distance_unit"
  | "latest_job"
  | "started_job_id"
> & {
  /** Create the project and start the first discovery run in one step (D-40). */
  start_agent?: boolean;
};
// GET /properties -> PropertySummary[]
// POST /properties (PropertyInput) -> Property
// GET /properties/{id} -> Property
// PATCH /properties/{id} (Partial<PropertyInput>) -> Property
// DELETE /properties/{id} -> 204 (soft delete; stops running agent work; admin/manager)
// GET /geocode?q=...&country=US -> GeocodeResult[]
export interface GeocodeResult {
  label: string;
  lat: number;
  lng: number;
  locality: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
}

/* ───────── Overview: GET /properties/{id}/overview ───────── */
export interface Overview {
  property: PropertySummary;
  account_count: number;
  tier_counts: Record<Tier, number>;
  funnel: Record<AccountStatus, number>;
  opportunities: Record<OpportunityStage, number> & { open_value: number; currency: string };
  recent_signals: (SignalItem & { account_id: UUID; company_name: string })[];
  attention: AccountListItem[]; // up to 5 accounts needing action
  running_jobs: JobSummary[];
  usage_30d: { cost_usd: number; llm_calls: number };
}

/* ───────── Discovery ───────── */
export interface DiscoveryConfig {
  property_id: UUID;
  radius_km: number;
  industries: string[];
  employee_min: number | null;
  employee_max: number | null;
  offerings_focus: Offering[];
  sources: ProviderKey[];
  csv_import_id: UUID | null;
  max_companies: number;
  research_depth: "light" | "standard";
  signal_window_days: number;
  prioritisation_notes: string | null;
  budget_usd: number;
}
export interface Range {
  low: number;
  expected: number;
  high: number;
}
export interface Estimate {
  candidates: Range;
  researched: Range;
  cost_usd: Range;
  duration_min: Range;
  assumptions: string[];
  is_calibrated: boolean;
  warnings: string[]; // e.g. "LLM not configured: research will use OpenStreetMap data only"
}
// POST /discovery/estimate {config} -> Estimate
// POST /discovery/parse-request {property_id, text, current_config} -> ParseResult (409 problem if LLM not configured)
export interface ParseResult {
  patch: { field: keyof DiscoveryConfig; from: unknown; to: unknown; reason: string }[];
  config: DiscoveryConfig;
}
export interface JobSummary {
  id: UUID;
  property_id: UUID;
  property_name: string;
  status: JobStatus;
  created_at: ISODate;
  started_at: ISODate | null;
  finished_at: ISODate | null;
  budget_usd: number;
  spent_usd: number;
  reserved_usd: number;
  progress: number; // 0..1
  counts: { found: number; companies: number; researched: number; failed: number; scored: number };
  created_by: string;
}
export interface Stage {
  key: "plan" | "discover" | "resolve" | "classify" | "research" | "signals" | "score";
  label: string;
  status: StageStatus;
  counts: { pending: number; running: number; succeeded: number; failed: number; skipped: number };
  detail: string | null; // human summary, e.g. "124 found · 17 merged"
}
export interface JobEvent {
  id: number;
  level: "info" | "warning" | "error";
  stage: string | null;
  message: string;
  created_at: ISODate;
}
export interface JobDetail extends JobSummary {
  config: DiscoveryConfig;
  estimate: Estimate | null;
  stages: Stage[];
  events: JobEvent[]; // newest last, up to 200
  error: string | null;
}
// POST /discovery/jobs {config} -> 202 {job_id, status}
// GET /discovery/jobs?property_id= -> JobSummary[]
// GET /discovery/jobs/{id} -> JobDetail   (poll every 2s while status is queued|running|cancelling)
// POST /discovery/jobs/{id}/cancel -> JobDetail
// POST /discovery/jobs/{id}/resume {budget_usd?} -> JobDetail
// POST /discovery/jobs/{id}/retry-failed -> JobDetail
// GET /discovery/jobs/{id}/results?outcome=new|merged|filtered_out|duplicate -> DiscoveryResult[]
export interface DiscoveryResult {
  id: UUID;
  name: string;
  provider: ProviderKey;
  outcome: "new" | "merged" | "filtered_out" | "duplicate";
  filter_reason: string | null;
  company_id: UUID | null;
  account_id: UUID | null;
}

/* ───────── CSV import ───────── */
// POST /properties/{id}/imports (multipart: file) -> CsvImport  (auto-maps common headers)
export interface CsvImport {
  id: UUID;
  file_name: string;
  status: "parsed" | "failed";
  row_count: number;
  mapping: Record<string, string | null>; // field -> csv header
  preview: Record<string, string>[]; // first 5 rows
  errors: { row: number; message: string }[];
}

/* ───────── Evidence ───────── */
export interface SourceRef {
  id: UUID;
  url: string | null;
  title: string | null;
  source_type: SourceType;
  retrieved_at: ISODate;
  published_at: ISODate | null;
  domain: string | null;
}
export interface Claim {
  id: UUID;
  field: string;
  field_label: string;
  value: unknown;
  display_value: string;
  kind: ClaimKind;
  confidence: number; // 0..1
  grounding_status: GroundingStatus;
  evidence_quote: string | null;
  rationale: string | null;
  supports: UUID[];
  source: SourceRef | null;
  data_origin: DataOrigin;
}
export interface SignalItem {
  id: UUID;
  signal_type: string;
  type_label: string;
  title: string;
  description: string | null;
  published_at: ISODate | null;
  age_days: number | null;
  is_historical: boolean;
  confidence: number;
  implied_offerings: Offering[];
  recommended_approach: string | null;
  evidence_quote: string | null;
  source: SourceRef | null;
}

/* ───────── Scores ───────── */
export interface FitFactor {
  key: "industry" | "inbound_travel" | "proximity" | "scale";
  label: string;
  weight: number;
  value: number;
  points: number;
  explanation: string;
  evidence: { claims: UUID[] };
}
export interface ScoreDetail {
  fit: number;
  intent: number;
  confidence: number;
  priority: number;
  tier: Tier;
  actionability: Actionability;
  model_version: number;
  computed_at: ISODate;
  breakdown: {
    fit: { total: number; factors: FitFactor[] };
    intent: {
      total: number;
      signals: {
        id: UUID;
        title: string;
        signal_type: string;
        contribution: number;
        age_days: number | null;
      }[];
    };
    confidence: {
      total: number;
      components: { coverage: number; diversity: number; freshness: number };
    };
    missing: string[];
  };
}

/* ───────── Accounts ───────── */
export interface CompanyBrief {
  id: UUID;
  name: string;
  domain: string | null;
  industry: string | null;
  industry_label: string | null;
  employee_range: string | null;
  locality: string | null;
  data_origin: DataOrigin;
}
export interface AccountListItem {
  id: UUID;
  property_id: UUID;
  company: CompanyBrief;
  distance_km: number | null;
  tier: Tier | null;
  priority: number | null;
  fit: number | null;
  intent: number | null;
  confidence: number | null;
  actionability: Actionability;
  top_signal: { type: string; type_label: string; title: string; age_days: number | null } | null;
  status: AccountStatus;
  owner: { id: UUID; name: string } | null;
  research_status: ResearchStatus;
  updated_at: ISODate;
}
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
  total: number;
}
// GET /properties/{id}/accounts?q&status&tier&industry&distance_max_km&owner(me|unassigned|<id>)&min_fit&min_intent&has_signal&job_id&ids(comma-separated)&sort(-priority|priority|-fit|-intent|-confidence|distance_km|name|-updated_at)&limit&cursor -> Page<AccountListItem>
// GET /properties/{id}/accounts/map -> MapPoint[]
// GET /properties/{id}/accounts/export.csv  (same filters; file download)
// POST /properties/{id}/accounts/bulk {account_ids, action: "assign"|"set_status"|"dismiss", owner_membership_id?, status?, dismissed_reason?, dismissed_note?} -> {updated: number}
export interface MapPoint {
  id: UUID;
  name: string;
  lat: number;
  lng: number;
  tier: Tier | null;
  status: AccountStatus;
}

export interface CompanyDetail extends CompanyBrief {
  description: string | null;
  hq_city: string | null;
  address: string | null;
  location: GeoPoint | null;
  website: string | null;
  research_status: ResearchStatus;
  last_researched_at: ISODate | null;
  do_not_contact: boolean;
}
export interface RoleRecommendation {
  role_code: string;
  label: string;
  offering: Offering;
  rank: number;
  rationale: string;
}
export interface Contact {
  id: UUID;
  company_id: UUID;
  full_name: string;
  title: string | null;
  role_code: string | null;
  email: string | null;
  phone: string | null;
  profile_url: string | null;
  source_note: string;
  verification_status: "unverified" | "user_verified" | "provider_verified";
  do_not_contact: boolean;
  created_at: ISODate;
  company_name?: string;
  account_id?: UUID;
}
export interface Activity {
  id: UUID;
  type: ActivityType;
  body: string | null;
  occurred_at: ISODate;
  actor: { id: UUID; name: string } | null;
  opportunity_id: UUID | null;
  metadata: Record<string, unknown>;
}
export interface Opportunity {
  id: UUID;
  account_id: UUID;
  company_name: string;
  name: string;
  offering: Offering;
  stage: OpportunityStage;
  value_amount: number | null;
  currency: string;
  expected_close_date: ISODate | null;
  probability: number | null;
  owner: { id: UUID; name: string } | null;
  loss_reason: LossReason | null;
  loss_note: string | null;
  updated_at: ISODate;
}
export interface AccountDetail extends AccountListItem {
  property_name: string;
  dismissed_reason: DismissReason | null;
  dismissed_note: string | null;
  company: CompanyDetail;
  score: ScoreDetail | null;
  claims: Claim[];
  signals: SignalItem[];
  sources: SourceRef[];
  roles: RoleRecommendation[];
  contacts: Contact[];
  opportunities: Opportunity[];
  activities: Activity[];
  related_accounts: {
    id: UUID;
    property_id: UUID;
    property_name: string;
    tier: Tier | null;
    status: AccountStatus;
  }[];
  next_action: {
    title: string;
    detail: string;
    kind:
      "research" | "add_contact" | "prepare_outreach" | "follow_up" | "create_opportunity" | "none";
  };
}
// GET /accounts/{id} -> AccountDetail
// PATCH /accounts/{id} {status?, owner_membership_id?, dismissed_reason?, dismissed_note?} -> AccountDetail  (409 on invalid transition)
// POST /accounts/{id}/research -> 202 {job_id}   (re-research one account)

/* ───────── Contacts ───────── */
export interface ContactInput {
  full_name: string;
  title?: string | null;
  role_code?: string | null;
  email?: string | null;
  phone?: string | null;
  profile_url?: string | null;
  source_note: string;
}
// GET /properties/{id}/contacts?q -> Contact[]
// POST /companies/{companyId}/contacts (ContactInput) -> Contact
// PATCH /contacts/{id} (Partial<ContactInput> & {do_not_contact?, verification_status?}) -> Contact
// DELETE /contacts/{id} -> 204
// PATCH /companies/{id} {do_not_contact} -> CompanyDetail

/* ───────── Copilot ───────── */
export interface CopilotBlock {
  text: string;
  claims: UUID[];
  is_inference?: boolean;
}
export interface CopilotContent {
  brief: {
    summary: CopilotBlock[];
    opportunity: CopilotBlock[];
    recommended_offering: Offering;
    approach: string;
  };
  email: { subject: string; body_blocks: CopilotBlock[] };
  call_questions: string[];
}
export interface CopilotOutput {
  id: UUID;
  account_id: UUID;
  contact_id: UUID | null;
  offering: Offering;
  version: number;
  status: "generated" | "edited" | "copied" | "marked_sent";
  content: CopilotContent;
  edited: { subject: string; body: string } | null;
  generated_by: "llm" | "template";
  created_at: ISODate;
}
// POST /accounts/{id}/copilot {offering, contact_id?, role_code?, tone?: "warm"|"formal"} -> CopilotOutput   (may take 10–40s)
// GET /accounts/{id}/copilot -> CopilotOutput[] (newest first)
// PATCH /copilot-outputs/{id} {subject, body} -> CopilotOutput
// POST /copilot-outputs/{id}/copied -> CopilotOutput
// POST /copilot-outputs/{id}/mark-sent -> CopilotOutput   (sets account status outreach_sent)

/* ───────── Pipeline ───────── */
export interface OpportunityInput {
  name: string;
  offering: Offering;
  value_amount?: number | null;
  expected_close_date?: ISODate | null;
  probability?: number | null;
  owner_membership_id?: UUID | null;
}
// GET /properties/{id}/opportunities -> Opportunity[]
// POST /accounts/{id}/opportunities (OpportunityInput) -> Opportunity   (sets account status engaged)
// PATCH /opportunities/{id} (Partial<OpportunityInput> & {stage?, loss_reason?, loss_note?}) -> Opportunity  (422 if stage=lost without loss_reason)
// GET /accounts/{id}/activities -> Activity[]
// POST /accounts/{id}/activities {type: "note"|"call"|"meeting"|"email_sent", body, opportunity_id?} -> Activity

/* ───────── Activity & usage ───────── */
// GET /activity/jobs -> JobSummary[]
// GET /activity/usage?group_by=step|model|job&days=30 -> UsageRow[]
export interface UsageRow {
  key: string;
  label: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}
// GET /activity/llm-calls?job_id= -> LlmCall[]
export interface LlmCall {
  id: UUID;
  step: string;
  model: string;
  prompt_id: string;
  prompt_version: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  status: "ok" | "error";
  error: string | null;
  created_at: ISODate;
}
