import type { AnalysisResponse } from './types';

export interface SavedResearch {
  id: string;
  title: string;
  result: AnalysisResponse;
  completed: number[];
}
export const STORAGE_KEY = 'gaplens.workspace.v2';
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(s => typeof s === 'string');
const list = (v: unknown, valid: (item: Record<string, unknown>) => boolean) => Array.isArray(v) && v.every(item => object(item) && valid(item));
const quote = (v: Record<string, unknown>) => typeof v.source_id === 'string' && typeof v.quote === 'string';
const validReport = (r: unknown) => {
  if (!object(r) || typeof r.id !== 'string' || typeof r.title !== 'string' || !object(r.result)) return false;
  const a = r.result;
  return Array.isArray(r.completed) && r.completed.every(Number.isInteger) &&
    ['live', 'offline_sample'].includes(String(a.mode)) && typeof a.goal === 'string' &&
    typeof a.analyzed_at === 'string' && Number.isFinite(Date.parse(a.analyzed_at)) &&
    typeof a.summary === 'string' && typeof a.disclaimer === 'string' && typeof a.analysis_method === 'string' &&
    typeof a.coverage_percent === 'number' && a.coverage_percent >= 0 && a.coverage_percent <= 100 &&
    typeof a.questions_analyzed === 'number' && strings(a.notes) && strings(a.inaccessible_source_ids) && strings(a.unanswered_questions) &&
    list(a.sources, s => typeof s.id === 'string' && typeof s.fetch_status === 'string' && typeof s.text_length === 'number' &&
      (s.title === null || typeof s.title === 'string') && (s.url === null || (typeof s.url === 'string' && /^https?:\/\//i.test(s.url))) &&
      (s.text_excerpt === null || typeof s.text_excerpt === 'string') && (s.error === null || typeof s.error === 'string') &&
      (s.published_date === null || typeof s.published_date === 'string')) &&
    list(a.coverage, c => typeof c.question_id === 'string' && typeof c.question === 'string' && ['covered','partial','not_found'].includes(String(c.status)) && strings(c.supporting_source_ids) && list(c.evidence, quote)) &&
    list(a.actions, c => typeof c.rank === 'number' && typeof c.action === 'string' && typeof c.reason === 'string' && ['high','medium','low'].includes(String(c.priority)) && strings(c.source_ids) && strings(c.question_ids)) &&
    list(a.gaps, g => typeof g.kind === 'string' && typeof g.detail === 'string' && ['high','medium','low'].includes(String(g.severity)) && (g.question === null || typeof g.question === 'string')) &&
    list(a.conflicts, c => typeof c.question_id === 'string' && typeof c.question === 'string' && typeof c.detail === 'string' && list(c.values, quote)) &&
    list(a.freshness_warnings, w => typeof w.source_id === 'string' && typeof w.kind === 'string' && typeof w.detail === 'string');
};
export function loadResearch(): { reports: SavedResearch[]; error: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { reports: [], error: null };
    const data = JSON.parse(raw);
    if (!Array.isArray(data) || !data.every(validReport)) {
      throw new Error('Invalid saved workspace');
    }
    return { reports: data.map(r => ({...r, completed: [...new Set(r.completed as number[])].filter(rank => r.result.actions.some((a: {rank:number}) => a.rank === rank))})), error: null };
  } catch {
    return { reports: [], error: 'Saved research could not be read. Existing browser data has not been changed. Export any open report before resetting storage in Settings.' };
  }
}
export function saveResearch(reports: SavedResearch[]): string | null {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reports));
    return null;
  } catch {
    return 'Browser storage is unavailable or full. Changes are kept in memory only; export your report before closing this page.';
  }
}
export function downloadReport(report: SavedResearch) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `gaplens-${report.id}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
