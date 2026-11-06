import type {
  CohortSummary,
  CompareResponse,
  ConformResponse,
  HealthResponse,
  YieldMatrix,
} from "../types/telemetry";

const API_BASE = "";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

export type SecretsStatus = {
  env_file: string;
  instructions: string;
  vars: Array<{
    name: string;
    required: boolean;
    set: boolean;
    value?: string;
    purpose: string;
  }>;
};

export const api = {
  health: () => jsonFetch<HealthResponse>("/api/health"),
  secretsStatus: () => jsonFetch<SecretsStatus>("/api/secrets/status"),
  cohorts: () => jsonFetch<CohortSummary[]>("/api/cohorts"),
  yieldMatrix: (cohortId: string, visualQuery?: string) => {
    const q = new URLSearchParams({ cohort_id: cohortId });
    if (visualQuery) q.set("visual_query", visualQuery);
    return jsonFetch<YieldMatrix>(`/api/yield-matrix?${q.toString()}`);
  },
  compare: (cohortId: string, rigId: string, rawFilename?: string) =>
    jsonFetch<CompareResponse>("/api/telemetry/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cohort_id: cohortId,
        rig_id: rigId,
        raw_filename: rawFilename || null,
      }),
    }),
  conform: (cohortId: string, rigId: string, rawFilename?: string) =>
    jsonFetch<ConformResponse>("/api/conform/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cohort_id: cohortId,
        rig_id: rigId,
        raw_filename: rawFilename || null,
      }),
    }),
  uploadRaw: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return jsonFetch<{ raw_filename: string; raw_video_url: string }>("/api/upload-raw", {
      method: "POST",
      body,
    });
  },
};
