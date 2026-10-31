import type {
  AnalysisResponse,
  AnalyzeRequest,
  FetchResponse,
  HealthResponse,
  SampleAnalysis,
} from "./types";

/** Backend base URL. Frontend-only config: no secret ever lives here. */
const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown; loc?: unknown };
      if (typeof first.msg === "string") {
        const where = Array.isArray(first.loc) ? first.loc.slice(1).join(".") : "";
        return where ? `${where}: ${first.msg}` : first.msg;
      }
    }
  }
  if (status === 422) return "The backend rejected this request. Check the inputs and try again.";
  return `Backend returned ${status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(
      "Could not reach the GapLens backend. Is it running on " + API_BASE + "?",
    );
  }
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw new ApiError(errorMessage(response.status, body), response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  sample: () => request<SampleAnalysis>("/api/sample"),
  fetchUrl: (url: string) =>
    request<FetchResponse>("/api/fetch", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  analyze: (payload: AnalyzeRequest) =>
    request<AnalysisResponse>("/api/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
