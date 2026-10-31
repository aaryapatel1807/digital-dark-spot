/** Frontend types mirroring backend/app/schemas.py exactly.
 *  If the backend schema changes, this file changes with it. */

export type SlotStatus = "covered" | "partial" | "gap";
export type FetchStatus = "ok" | "blocked" | "failed" | "unsupported";

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  groq_configured: boolean;
  sample_mode_available: boolean;
  checked_at: string;
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
