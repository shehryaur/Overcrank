import type { ShortClip, VisualRig, YieldMatrix } from "../types/telemetry";

/** Hardcoded jury demo for the "AI founders" chip — instant, reliable, no API wait. */

export const DEMO_QUERY = "AI founders";

export const DEMO_PROCESS_STEPS = [
  { label: "Expanding topic with Claude", detail: "AI founders → street pitch, demo, split-cam queries" },
  { label: "Searching YouTube Shorts", detail: "Scanning short-form index for founder outliers" },
  { label: "Ranking clips by engagement physics", detail: "Views, comments, shares → yield score" },
  { label: "Scoring formats with Oriane", detail: "Street mic vs desk vs over-shoulder saturation" },
  { label: "Locking the outlier reference", detail: "Highest-yield take locked for Align" },
  { label: "Opening Align", detail: "Ready for your raw take" },
];

function yt(id: string, title: string, creator: string, yieldX: number): ShortClip {
  return {
    clip_id: `demo_yt_${id}`,
    platform: "youtube",
    title,
    creator,
    topics: ["ai", "founders", "startup"],
    video_id: id,
    embed_url: `https://www.youtube.com/embed/${id}?autoplay=1&mute=1&loop=1&playlist=${id}&controls=0&rel=0&modestbranding=1&playsinline=1`,
    watch_url: `https://www.youtube.com/shorts/${id}`,
    local_video_url: null,
    thumbnail_url: `https://i.ytimg.com/vi/${id}/hqdefault.jpg`,
    views: 0,
    yield_multiplier: yieldX,
    saturation_pct: 2.1,
    rig_id: "rig_demo_street_mic",
    source: "demo-hardcoded",
    score: 5,
  };
}

export const DEMO_CLIPS: ShortClip[] = [
  // Face-to-camera walk-and-talk on a city street (Align reference for street mic)
  yt(
    "sdfla9Df8ok",
    "How to film yourself walking outside talking to camera #shorts",
    "@Street Walk Talk",
    3.45,
  ),
  yt(
    "gPjDfXYGNE0",
    "This is the BEST Way to Learn About San Francisco!",
    "@SF Guides",
    3.3,
  ),
  yt(
    "URMN0RrdS2Y",
    "AI Founders Street Interview at Palo Alto #ai #streetinterview",
    "@Street Founders",
    3.2,
  ),
  yt(
    "P6UbmAZHBLo",
    "Why Every Founder Moves to San Francisco #Shorts #Startup",
    "@Founder Cuts",
    3.1,
  ),
  yt(
    "ZlUIC9bJyEs",
    "Crazy Tech CEO Pitches an AI Startup to Investors... #shorts",
    "@Founders, Inc.",
    2.95,
  ),
  yt(
    "N5yyKQLyaww",
    "Dario Amodei (Anthropic CEO) on why he left OpenAI #shorts",
    "@AI Clips",
    2.9,
  ),
];

/** Person holding camera, face on screen, walking on street */
export const DEMO_STREET_CLIP = DEMO_CLIPS[0];
export const DEMO_BEST_CLIP = DEMO_STREET_CLIP;

export const RIG_TO_CLIP: Record<string, ShortClip> = {
  rig_demo_street_mic: DEMO_STREET_CLIP,
  rig_demo_code: DEMO_CLIPS[4],
  rig_demo_split: DEMO_CLIPS[5],
  rig_demo_desk: DEMO_CLIPS[2],
};

export const DEMO_RIGS: VisualRig[] = [
  {
    rig_id: "rig_demo_street_mic",
    headline: "Street mic AI founder pitch",
    plain_why: "High energy outdoor hook — best for AI founders demo.",
    title: "Walking Street Mic + 1.1s B-Roll Flash (0-4s)",
    visual_query: "person face to camera phone selfie walking city street talk",
    saturation_pct: 1.6,
    yield_multiplier: 3.45,
    quadrant: "HIGH_YIELD_UNSATURATED",
    sample_count: 237,
    mean_views: 412000,
    reference_video: "ref_street_walk_talk.mp4",
    reference_creator: "@Street Walk Talk",
    data_source: "demo",
    target_specs: {
      splices_per_10s: 7.8,
      mean_shot_ms: 1280,
      dead_air_max_ms: 120,
      focal_push_scale: 1.16,
      hook_broll_timestamps: [1.1, 2.3, 3.6],
    },
  },
  {
    rig_id: "rig_demo_code",
    headline: "Over-shoulder code demo",
    plain_why: "Show the product while you talk.",
    title: "Over-Shoulder Diagram Draw + Rapid 1.18x Punch",
    visual_query: "hand drawing architecture whiteboard zoom",
    saturation_pct: 2.4,
    yield_multiplier: 2.95,
    quadrant: "HIGH_YIELD_UNSATURATED",
    sample_count: 355,
    mean_views: 289000,
    reference_video: "ref_hippolyte_outlier.mp4",
    reference_creator: "@demo",
    data_source: "demo",
    target_specs: {
      splices_per_10s: 6.9,
      mean_shot_ms: 1450,
      dead_air_max_ms: 140,
      focal_push_scale: 1.18,
      hook_broll_timestamps: [0.9, 2.5, 4.1],
    },
  },
  {
    rig_id: "rig_demo_split",
    headline: "Split screen product + face",
    plain_why: "UI on top, you on bottom.",
    title: "Live Terminal / Chart Top-Half + Face Cam Bottom",
    visual_query: "split screen terminal talking head",
    saturation_pct: 4.1,
    yield_multiplier: 2.6,
    quadrant: "HIGH_YIELD_UNSATURATED",
    sample_count: 607,
    mean_views: 215000,
    reference_video: "ref_hippolyte_outlier.mp4",
    reference_creator: "@demo",
    data_source: "demo",
    target_specs: {
      splices_per_10s: 6.2,
      mean_shot_ms: 1610,
      dead_air_max_ms: 150,
      focal_push_scale: 1.14,
      hook_broll_timestamps: [1.4, 3.0],
    },
  },
  {
    rig_id: "rig_demo_desk",
    headline: "Static desk monologue",
    plain_why: "Usually avoid — oversaturated for this topic.",
    title: "Un-cut Desk Monologue (Zero Push First 5s)",
    visual_query: "person at desk webcam static",
    saturation_pct: 34.2,
    yield_multiplier: 0.71,
    quadrant: "OVERSATURATED_LOW_YIELD",
    sample_count: 5068,
    mean_views: 24100,
    reference_video: "ref_hippolyte_outlier.mp4",
    reference_creator: "Cohort Median",
    data_source: "demo",
    target_specs: {
      splices_per_10s: 1.8,
      mean_shot_ms: 5500,
      dead_air_max_ms: 480,
      focal_push_scale: 1.02,
      hook_broll_timestamps: [],
    },
  },
];

export const DEMO_MATRIX: YieldMatrix = {
  cohort_id: "sf_founder_interviews",
  label: 'Formats for “AI founders”',
  indexed_videos: 14820,
  baseline_er: 0.042,
  topic: DEMO_QUERY,
  oriane_mode: "demo-hardcoded",
  rigs: DEMO_RIGS,
};

export const RECORD_BRIEF = {
  title: "What to film (30–40 sec, vertical)",
  bullets: [
    "Phone vertical, front camera, face in frame while you walk.",
    "Street / sidewalk — keep moving, talk to the lens.",
    "Pitch your AI/startup idea for ~20–30 seconds.",
    "Short sentences. No long pauses.",
    "Optional: flash your laptop screen once mid-take.",
  ],
};
