import type {
  CompareResponse,
  ConformResponse,
  TopicSearchResponse,
} from "../types/telemetry";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function mediaUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}

export const api = {
  topicSearch: (query: string, cohortId = "sf_founder_interviews") =>
    jsonFetch<TopicSearchResponse>("/api/topic/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, cohort_id: cohortId, limit: 8 }),
    }),
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
  openInCompound: (payload: {
    conformed_filename: string;
    compound_prompt: string;
    compound_edl?: ConformResponse["compound_edl"];
    rig_title: string;
  }) =>
    jsonFetch<{
      project_dir: string;
      display_name: string;
      zip_url: string;
      agent_line: string;
      hint: string;
      steps: string[];
      assist: { finder?: boolean; clipboard?: boolean; app?: string };
    }>("/api/compound/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, launch: true }),
    }),
};
