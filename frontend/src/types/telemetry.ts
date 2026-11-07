export type TargetSpecs = {
  splices_per_10s: number;
  mean_shot_ms: number;
  dead_air_max_ms: number;
  focal_push_scale: number;
  hook_broll_timestamps: number[];
};

export type VisualRig = {
  rig_id: string;
  title: string;
  headline?: string;
  plain_why?: string;
  visual_query: string;
  saturation_pct: number;
  yield_multiplier: number;
  quadrant: string;
  sample_count: number;
  mean_views: number;
  reference_video: string;
  reference_creator: string;
  data_source?: string;
  target_specs: TargetSpecs;
};

export type YieldMatrix = {
  cohort_id: string;
  label: string;
  indexed_videos: number;
  baseline_er: number;
  topic?: string;
  oriane_mode?: string;
  rigs: VisualRig[];
};

export type OscilloscopePoint = {
  t: number;
  ref_focal_push: number;
  raw_focal_push: number;
  ref_vocal_energy: number;
  raw_vocal_energy: number;
  ref_splice: number;
  raw_splice: number;
  raw_hazard: number;
};

export type CompareResponse = {
  rig: VisualRig;
  reference_video_url: string;
  raw_video_url: string;
  raw_filename: string;
  alignment_score_before: number;
  alignment_score_projected: number;
  reference: Record<string, unknown>;
  raw: Record<string, unknown>;
  merged_oscilloscope: OscilloscopePoint[];
};

export type CompoundEdl = {
  engine: string;
  rig_id: string;
  rig_title: string;
  target_splices_per_10s: number;
  silence_gate: {
    threshold_db: number;
    max_pause_ms: number;
    pad_margin_ms: number;
  };
  focal_push_keyframes: Array<{
    timecode_sec: number;
    scale: number;
    easing: string;
  }>;
  broll_insert_markers: number[];
};

export type ConformResponse = {
  conformed_filename: string;
  conformed_video_url: string;
  compound_edl: CompoundEdl;
  compound_prompt: string;
  conformed_telemetry: Record<string, unknown>;
  alignment_score_after: number;
  merged_oscilloscope_after: OscilloscopePoint[];
};

export type ShortClip = {
  clip_id: string;
  platform: "youtube" | "tiktok" | "instagram" | string;
  title: string;
  creator: string;
  topics: string[];
  video_id: string;
  embed_url: string;
  watch_url: string;
  local_video_url?: string | null;
  thumbnail_url?: string | null;
  views: number;
  yield_multiplier: number;
  saturation_pct: number;
  rig_id?: string | null;
  source: string;
  score: number;
};

export type TopicSearchResponse = {
  query: string;
  discovery: {
    query: string;
    mode: string;
    total: number;
    platforms: Record<string, number>;
    clips: ShortClip[];
  };
  matrix: YieldMatrix;
  preferred_rig_id: string;
};

export type Step = "search" | "discover" | "align" | "conform";
