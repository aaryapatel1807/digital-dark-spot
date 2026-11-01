/** Frontend types mirroring backend/app/schemas.py and
 *  backend/app/analysis_schemas.py exactly.
 *  If a backend schema changes, this file changes with it. */

export type SlotStatus = "covered" | "partial" | "gap";
export type FetchStatus =
  | "ok"
  | "blocked"
  | "failed"
  | "unsupported"
  | "not_found"
  | "nonexistent"
  | "timeout"
  | "too_large";

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  groq_configured: boolean;
  search_configured?: boolean;
  sample_mode_available: boolean;
  checked_at: string;
}

export interface DiscoverResult {
  title: string;
  link: string;
  snippet: string | null;
}

export interface PdfTextResponse {
  filename: string;
  pages: number;
  pages_with_text: number;
  total_chars: number;
  text: string;
  page_texts: { page: number; text: string }[];
}

export interface DiscoverResponse {
  query: string;
  provider: string;
  configured: boolean;
  results: DiscoverResult[];
}

export interface SampleSource {
  id: string;
  label: string;
  kind: "official" | "blog" | "forum" | "other";
  url: string | null;
  note: string;
  is_sample: true;
}

export interface CoverageSlot {
  slot: string;
  question: string;
  status: SlotStatus;
  source_ids: string[];
}

export interface SampleGap {
  slot: string;
  title: string;
  detail: string;
  severity: "high" | "medium" | "low";
}

export interface ConflictValue {
  source_id: string;
  value: string;
  quote: string;
}

export interface SampleConflict {
  slot: string;
  label: "possible conflict";
  detail: string;
  values: ConflictValue[];
}

export interface SampleChecklistItem {
  rank: number;
  action: string;
  reason: string;
  priority: "high" | "medium" | "low";
}

export interface SampleAnalysis {
  mode: "offline_sample";
  topic: string;
  disclaimer: string;
  coverage_percent: number;
  sources: SampleSource[];
  slots: CoverageSlot[];
  gaps: SampleGap[];
  conflicts: SampleConflict[];
  checklist: SampleChecklistItem[];
}

export interface FetchResponse {
  url: string;
  status: FetchStatus;
  title: string | null;
  text_excerpt: string | null;
  content_type: string | null;
  error: string | null;
  fetched_at: string;
  note: string;
}

/* ---- /api/analyze (backend/app/analysis_schemas.py) ---- */

export type CoverageStatus = "covered" | "partial" | "not_found";
export type GapKind = "unanswered" | "partial" | "single_source" | "stale_only" | "undated_only";
export type FreshnessKind = "stale" | "undated";
export type Priority = "high" | "medium" | "low";
export type QuestionOrigin = "user" | "derived";
export type SourceKind = "url" | "pasted_text";
export type AnalysisMode = "live" | "offline_sample";

export interface PastedTextInput {
  title?: string;
  text: string;
}

export interface AnalyzeRequest {
  goal?: string;
  questions?: string[];
  urls?: string[];
  texts?: PastedTextInput[];
  mode: AnalysisMode;
}

export interface SourceRecord {
  id: string;
  kind: SourceKind;
  url: string | null;
  title: string | null;
  fetch_status: FetchStatus;
  date_status: "known" | "unknown";
  published_date: string | null;
  text_excerpt: string | null;
  text_length: number;
  error: string | null;
  is_sample: boolean;
}

export interface EvidenceQuote {
  source_id: string;
  quote: string;
}

export interface QuestionCoverage {
  question_id: string;
  question: string;
  origin: QuestionOrigin;
  status: CoverageStatus;
  supporting_source_ids: string[];
  evidence: EvidenceQuote[];
}

export interface PossibleConflict {
  question_id: string;
  question: string;
  label: "possible conflict";
  detail: string;
  values: EvidenceQuote[];
}

export interface GapItem {
  kind: GapKind;
  question_id: string | null;
  question: string | null;
  detail: string;
  severity: Priority;
}

export interface FreshnessWarning {
  source_id: string;
  kind: FreshnessKind;
  detail: string;
  age_days: number | null;
}

export interface ActionItem {
  rank: number;
  action: string;
  reason: string;
  priority: Priority;
  question_ids: string[];
  source_ids: string[];
}

export interface AnalysisResponse {
  mode: AnalysisMode;
  goal: string;
  questions_analyzed: number;
  coverage_percent: number;
  summary: string;
  disclaimer: string;
  sources: SourceRecord[];
  coverage: QuestionCoverage[];
  unanswered_questions: string[];
  gaps: GapItem[];
  conflicts: PossibleConflict[];
  freshness_warnings: FreshnessWarning[];
  actions: ActionItem[];
  inaccessible_source_ids: string[];
  analysis_method: string;
  notes: string[];
  analyzed_at: string;
}
