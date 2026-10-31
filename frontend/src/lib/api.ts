import type { FetchResponse, HealthResponse, SampleAnalysis } from "./types";

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
    throw new ApiError(`Backend returned ${response.status} for ${path}.`, response.status);
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
};
