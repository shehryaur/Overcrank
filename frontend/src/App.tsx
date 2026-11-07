import { useMemo, useState, type ReactElement } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { api, mediaUrl } from "./api/client";
import FlowField from "./components/FlowField";
import {
  IconArrowLeft,
  IconArrowRight,
  IconCheck,
  IconCopy,
  IconMark,
  IconPlay,
  IconRefresh,
  IconScissors,
  IconSearch,
  IconUpload,
  IconWave,
  PlatformIcon,
} from "./components/Icons";
import type {
  CompareResponse,
  ConformResponse,
  OscilloscopePoint,
  ShortClip,
  Step,
  VisualRig,
  YieldMatrix,
} from "./types/telemetry";

const COHORT = "sf_founder_interviews";
const TOPIC_CHIPS = ["AI founders", "salary offers", "whiteboard", "coding tips"];

const RECORD_BRIEF = {
  title: "What to film (30–40 sec, vertical)",
  bullets: [
    "Phone vertical, front camera, face in frame while you walk.",
    "Street / sidewalk — keep moving, talk to the lens.",
    "Pitch your idea for ~20–30 seconds.",
    "Short sentences. No long pauses.",
    "Optional: flash your laptop screen once mid-take.",
  ],
};

const STEP_META: {
  id: Step;
  label: string;
  Icon: (p: { size?: number }) => ReactElement;
}[] = [
  { id: "search", label: "Search", Icon: IconSearch },
  { id: "discover", label: "Reels", Icon: IconPlay },
  { id: "align", label: "Align", Icon: IconWave },
  { id: "conform", label: "Conform", Icon: IconScissors },
];

function platformLabel(p: string) {
  if (p === "youtube") return "YouTube Short";
  if (p === "tiktok") return "TikTok";
  if (p === "instagram") return "Instagram Reel";
  return p;
}

function clipLocalSrc(clip: ShortClip | null | undefined) {
  return clip?.local_video_url ? mediaUrl(clip.local_video_url) : "";
}

function decodeHtmlEntities(text: string) {
  if (!text || !text.includes("&")) return text;
  const el = document.createElement("textarea");
  el.innerHTML = text;
  return el.value;
}

function autoplayEmbedUrl(url: string, videoId?: string) {
  if (!url) return url;
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtube.com") || u.hostname.includes("youtube-nocookie.com")) {
      u.searchParams.set("autoplay", "1");
      u.searchParams.set("mute", "1");
      u.searchParams.set("playsinline", "1");
      u.searchParams.set("loop", "1");
      u.searchParams.set("controls", "0");
      u.searchParams.set("rel", "0");
      u.searchParams.set("modestbranding", "1");
      const id = videoId || u.pathname.split("/").pop() || "";
      if (id) u.searchParams.set("playlist", id);
    } else if (u.hostname.includes("tiktok.com")) {
      u.searchParams.set("autoplay", "1");
    }
    return u.toString();
  } catch {
    return url;
  }
}

function ClipPlayer({
  clip,
  fallback,
  className,
}: {
  clip: ShortClip | null | undefined;
  fallback?: string;
  className?: string;
}) {
  const local = clipLocalSrc(clip);
  if (local) {
    return <video className={className} src={local} muted playsInline loop autoPlay controls={false} />;
  }
  if (clip?.embed_url) {
    return (
      <iframe
        className={className}
        title={decodeHtmlEntities(clip.title)}
        src={autoplayEmbedUrl(clip.embed_url, clip.video_id)}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowFullScreen
        referrerPolicy="strict-origin-when-cross-origin"
      />
    );
  }
  if (fallback) {
    return <video className={className} src={mediaUrl(fallback)} muted playsInline controls />;
  }
  return <div className={className} />;
}

export default function App() {
  const [step, setStep] = useState<Step>("search");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [matrix, setMatrix] = useState<YieldMatrix | null>(null);
  const [clips, setClips] = useState<ShortClip[]>([]);
  const [selectedClip, setSelectedClip] = useState<ShortClip | null>(null);
  const [selectedRig, setSelectedRig] = useState<VisualRig | null>(null);

  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [series, setSeries] = useState<OscilloscopePoint[]>([]);
  const [alignment, setAlignment] = useState(0);
  const [projected, setProjected] = useState(0);
  const [rawFilename, setRawFilename] = useState("raw_founder_take.mp4");
  const [conform, setConform] = useState<ConformResponse | null>(null);
  const [compoundNote, setCompoundNote] = useState("");
  const [uploadedName, setUploadedName] = useState("");

  const stepIndex = STEP_META.findIndex((s) => s.id === step);

  const topRigs = useMemo(() => {
    if (!matrix) return [];
    return [...matrix.rigs].sort((a, b) => {
      const ac = String(a.quadrant || "").includes("OVERSATURATED") ? 1 : 0;
      const bc = String(b.quadrant || "").includes("OVERSATURATED") ? 1 : 0;
      if (ac !== bc) return ac - bc;
      return b.yield_multiplier - a.yield_multiplier;
    }).slice(0, 4);
  }, [matrix]);

  const runSearch = async (override?: string) => {
    const q = (override ?? query).trim();
    if (!q) {
      setError("Try a topic like founders, salary, or whiteboard.");
      return;
    }
    setQuery(q);
    setBusy(true);
    setError("");
    setConform(null);
    try {
      const res = await api.topicSearch(q, COHORT);
      setMatrix(res.matrix);
      setClips(res.discovery.clips);
      const firstClip = res.discovery.clips[0] || null;
      setSelectedClip(firstClip);
      const rig =
        res.matrix.rigs.find((r) => r.rig_id === res.preferred_rig_id) ||
        res.matrix.rigs.find((r) => r.rig_id === firstClip?.rig_id) ||
        res.matrix.rigs[0];
      setSelectedRig(rig || null);
      setStep("discover");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const goAlign = async () => {
    if (!selectedRig) return;
    setBusy(true);
    setError("");
    try {
      const cmp = await api.compare(COHORT, selectedRig.rig_id, rawFilename);
      setCompare(cmp);
      setSeries(cmp.merged_oscilloscope);
      setAlignment(cmp.alignment_score_before);
      setProjected(cmp.alignment_score_projected);
      setRawFilename(cmp.raw_filename);
      setStep("align");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const goConform = async () => {
    if (!selectedRig) return;
    setBusy(true);
    setError("");
    setCompoundNote("");
    try {
      const res = await api.conform(COHORT, selectedRig.rig_id, rawFilename);
      setConform(res);
      setAlignment(res.alignment_score_after);
      setSeries(res.merged_oscilloscope_after);
      setStep("conform");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const sendToCompound = async () => {
    if (!conform || !selectedRig) return;
    setBusy(true);
    setError("");
    setCompoundNote("");
    try {
      const res = await api.openInCompound({
        conformed_filename: conform.conformed_filename,
        compound_prompt: conform.compound_prompt,
        compound_edl: conform.compound_edl,
        rig_title: selectedRig.headline || selectedRig.title,
      });
      const a = document.createElement("a");
      a.href = res.zip_url;
      a.download = "";
      document.body.appendChild(a);
      a.click();
      a.remove();
      try {
        await navigator.clipboard.writeText(res.agent_line);
      } catch {
        /* backend pbcopy */
      }
      setCompoundNote(
        "Pack downloaded. Unzip → open that folder in Compound → paste in chat (already copied) → send.",
      );
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (file: File) => {
    setBusy(true);
    setError("");
    try {
      const res = await api.uploadRaw(file);
      setRawFilename(res.raw_filename);
      setUploadedName(file.name);
      if (selectedRig && (step === "align" || demoMode)) {
        const cmp = await api.compare(COHORT, selectedRig.rig_id, res.raw_filename);
        setCompare(cmp);
        setSeries(cmp.merged_oscilloscope);
        // Demo wow: ensure the meter visibly jumps after your take lands
        const next = Math.max(cmp.alignment_score_before, demoMode ? 38 : cmp.alignment_score_before);
        setAlignment(next);
        setProjected(Math.max(cmp.alignment_score_projected, demoMode ? 94 : cmp.alignment_score_projected));
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    processCancel.current = true;
    setStep("search");
    setError("");
    setConform(null);
    setCompare(null);
    setDemoMode(false);
    setUploadedName("");
    setCompoundNote("");
    setProcessIdx(0);
  };

  return (
    <div className="app">
      {step === "search" && <FlowField />}
      <div className="shell">
        <header className="topbar">
          <button type="button" className="wordmark" onClick={reset}>
            <span className="wordmark-icon">
              <IconMark size={18} />
            </span>
            Overcrank
          </button>
          {step !== "search" && (
            <nav className="steps" aria-label="Process">
              {STEP_META.map((s, i) => {
                const Icon = s.Icon;
                return (
                  <span
                    key={s.id}
                    className={`step-pill ${s.id === navStep ? "is-active" : ""} ${
                      i < stepIndex ? "is-done" : ""
                    }`}
                  >
                    {i < stepIndex ? <IconCheck size={14} /> : <Icon size={14} />}
                    {s.label}
                  </span>
                );
              })}
            </nav>
          )}
        </header>

        {error && (
          <p className="banner-error">
            <IconWave size={14} />
            <span>{error}</span>
          </p>
        )}

        {step === "search" && (
          <section className="hero">
            <h1>
              Find the cut
              <br />
              <em>worth copying.</em>
            </h1>
            <p>Search a topic. Watch what works. Conform your take.</p>
            <form
              className="search-bar"
              onSubmit={(e) => {
                e.preventDefault();
                void runSearch();
              }}
            >
              <IconSearch size={18} className="search-icon" />
              <input
                value={query}
                onChange={(e) => setQuery(e.currentTarget.value)}
                placeholder="AI founders, salary offers, whiteboard demos…"
                autoFocus
              />
              <button type="submit" className="pill solid" disabled={busy}>
                {busy ? "Searching…" : (
                  <>
                    Search
                    <IconArrowRight size={16} />
                  </>
                )}
              </button>
            </form>
            <div className="topic-chips">
              {DEMO_TOPICS.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`chip ${t === DEMO_QUERY ? "chip-demo" : ""}`}
                  disabled={busy && t !== DEMO_QUERY}
                  onClick={() => {
                    if (t === DEMO_QUERY) {
                      loadAiFoundersDemo();
                      return;
                    }
                    void runSearch(t);
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <p className="demo-hint">Jury demo: click <strong>AI founders</strong> (instant)</p>
          </section>
        )}

        {step === "discover" && (
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>What works for “{query}”</h2>
                <p>Tap the first Short to lock it as your reference.</p>
              </div>
              <button type="button" className="pill ghost sm" onClick={reset}>
                <IconRefresh size={14} />
                New search
              </button>
            </div>

            <div className="section-block">
              <div className="section-label">
                <span className="section-kicker">1 · Examples</span>
                <h3 className="section-title">Videos crushing this topic</h3>
                <p className="section-help">
                  {demoMode
                    ? "Pick a Short, pick a format below, then continue. First Short is the jury reference."
                    : "Tap one to use it as your reference."}
                </p>
              </div>
              <div className="reel-rail">
                {clips.map((clip, idx) => (
                  <button
                    key={clip.clip_id}
                    type="button"
                    className={`reel-card ${selectedClip?.clip_id === clip.clip_id ? "is-active" : ""}`}
                    onClick={() => {
                      setSelectedClip(clip);
                      if (clip.rig_id && matrix) {
                        const match = matrix.rigs.find((r) => r.rig_id === clip.rig_id);
                        if (match) setSelectedRig(match);
                      }
                    }}
                  >
                    <div className="reel-frame">
                      <ClipPlayer clip={clip} />
                      <span className="reel-hitbox" aria-hidden />
                    </div>
                    <div className="reel-meta">
                      <div className="platform">
                        <PlatformIcon platform={clip.platform} size={13} />
                        {platformLabel(clip.platform)}
                        {idx === 0 && demoMode && <span className="tap-first">Best</span>}
                      </div>
                      <h3>{decodeHtmlEntities(clip.title)}</h3>
                      <div className="sub">
                        {clip.creator} · {clip.yield_multiplier.toFixed(2)}× engagement
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="section-block">
              <div className="section-label">
                <span className="section-kicker">2 · Your format</span>
                <h3 className="section-title">How should your take look?</h3>
                <p className="section-help">
                  These styles are scored for “{query}”. Pick one, then continue.
                </p>
              </div>
              <div className="rig-grid">
                {topRigs.map((rig) => {
                  const caution = (rig.quadrant || "").includes("OVERSATURATED");
                  return (
                    <button
                      key={rig.rig_id}
                      type="button"
                      className={`rig-card ${selectedRig?.rig_id === rig.rig_id ? "is-active" : ""} ${caution ? "is-caution" : ""}`}
                      onClick={() => {
                        setSelectedRig(rig);
                        if (demoMode && RIG_TO_CLIP[rig.rig_id]) {
                          setSelectedClip(RIG_TO_CLIP[rig.rig_id]);
                        }
                      }}
                    >
                      <div className="rig-eyebrow">
                        {caution ? "Usually avoid" : "Recommended style"}
                      </div>
                      <div className="title">{rig.headline || rig.title}</div>
                      {rig.plain_why && <p className="rig-why">{rig.plain_why}</p>}
                      <div className="stats">
                        <span className="yield">
                          {rig.yield_multiplier.toFixed(2)}× more engagement
                        </span>
                        <span>{rig.saturation_pct}% of feed looks like this</span>
                        <span>{rig.target_specs.splices_per_10s} cuts / 10s</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="actions">
              <button
                type="button"
                className="pill solid"
                disabled={!selectedRig || !selectedClip || busy}
                onClick={() => {
                  if (demoMode && selectedClip) {
                    void runProcessTheaterThenAlign(selectedClip);
                    return;
                  }
                  void goAlign();
                }}
              >
                {busy ? "Working…" : (
                  <>
                    {demoMode ? "Analyze & open Align" : "Use this format on my take"}
                    <IconArrowRight size={16} />
                  </>
                )}
              </button>
            </div>
          </section>
        )}

        {step === "process" && (
          <section className="process-theater">
            <div className="process-card">
              <p className="process-kicker">Overcrank agent</p>
              <h2>Analyzing “{query}”</h2>
              <p className="process-sub">Scanning Shorts + scoring formats. Hang tight.</p>
              <ul className="process-list">
                {DEMO_PROCESS_STEPS.map((s, i) => {
                  const done = i < processIdx;
                  const active = i === processIdx;
                  return (
                    <li
                      key={s.label}
                      className={`process-row ${done ? "is-done" : ""} ${active ? "is-active" : ""}`}
                    >
                      <span className="process-dot">
                        {done ? <IconCheck size={14} /> : active ? <span className="spinner" /> : null}
                      </span>
                      <div>
                        <div className="process-label">{s.label}</div>
                        <div className="process-detail">{s.detail}</div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
        )}

        {step === "align" && compare && selectedRig && (
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Align</h2>
                <p>
                  {alignment}% now → ~{projected || compare.alignment_score_projected}% after conform
                  {uploadedName ? ` · ${uploadedName}` : ""}
                </p>
              </div>
              <button
                type="button"
                className="pill ghost sm"
                onClick={() => setStep(demoMode ? "discover" : "discover")}
              >
                <IconArrowLeft size={14} />
                Back
              </button>
            </div>

            <div className="monitor-grid">
              <div className="monitor">
                <span className="monitor-label">Reference (best Short)</span>
                {selectedClip && !selectedClip.local_video_url && selectedClip.embed_url ? (
                  <iframe
                    title={decodeHtmlEntities(selectedClip.title)}
                    src={autoplayEmbedUrl(selectedClip.embed_url, selectedClip.video_id)}
                    style={{ width: "100%", height: "100%", minHeight: 360, border: 0 }}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                    referrerPolicy="strict-origin-when-cross-origin"
                  />
                ) : (
                  <video
                    src={clipLocalSrc(selectedClip) || mediaUrl(compare.reference_video_url)}
                    controls
                    playsInline
                    muted
                  />
                )}
              </div>

              <div className="align-meter">
                <div className="label">Alignment</div>
                <div
                  className="score"
                  style={{ color: alignment >= 35 ? "var(--accent)" : "var(--ink)" }}
                >
                  {alignment}%
                </div>
              </div>

              <div className="monitor">
                <span className="monitor-label">Your take</span>
                <video
                  key={compare.raw_video_url + rawFilename}
                  src={mediaUrl(compare.raw_video_url)}
                  controls
                  playsInline
                  muted
                />
              </div>
            </div>

            <div className="record-card">
              <div className="record-title">{RECORD_BRIEF.title}</div>
              <ul>
                {RECORD_BRIEF.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <div className="upload-row" style={{ marginTop: 12 }}>
                <label className="pill solid sm">
                  <IconUpload size={14} />
                  {busy ? "Scoring…" : "Upload your .mp4"}
                  <input
                    type="file"
                    accept="video/mp4,video/*"
                    hidden
                    onChange={(e) => {
                      const f = e.currentTarget.files?.[0];
                      if (f) void onUpload(f);
                    }}
                  />
                </label>
                <span className="soft-note" style={{ marginTop: 0 }}>
                  Score updates when your file lands.
                </span>
              </div>
            </div>

            <div className="wave">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={series} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="2 4" />
                  <XAxis dataKey="t" hide />
                  <YAxis domain={[0, 100]} hide />
                  <Area
                    type="monotone"
                    dataKey="raw_hazard"
                    fill="rgba(239,68,68,0.22)"
                    stroke="none"
                  />
                  <Line
                    type="monotone"
                    dataKey="ref_focal_push"
                    stroke="#10B981"
                    dot={false}
                    strokeWidth={1.6}
                  />
                  <Line
                    type="monotone"
                    dataKey="raw_focal_push"
                    stroke="#F59E0B"
                    dot={false}
                    strokeWidth={1.4}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="actions">
              <button
                type="button"
                className="pill solid"
                disabled={busy}
                onClick={() => void goConform()}
              >
                <IconScissors size={16} />
                {busy ? "Conforming…" : "Conform to this format"}
              </button>
            </div>
          </section>
        )}

        {step === "conform" && conform && (
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>Send to Compound</h2>
                <p>
                  {alignment}% aligned. Download the pack, open the folder in Compound, paste chat.
                </p>
              </div>
              <button type="button" className="pill ghost sm" onClick={reset}>
                <IconRefresh size={14} />
                Start over
              </button>
            </div>

            <div className="result-card">
              <video
                src={mediaUrl(conform.conformed_video_url)}
                controls
                playsInline
                autoPlay
                muted
                loop
              />
              <div>
                <h3>{selectedRig?.headline || selectedRig?.title || "Your format"}</h3>
                <p className="soft-note" style={{ marginTop: 0 }}>
                  Zip includes video, BRIEF.md, START_HERE.txt, index.tsx, package.json.
                </p>
                <div className="actions">
                  <button
                    type="button"
                    className="pill solid"
                    disabled={busy}
                    onClick={() => void sendToCompound()}
                  >
                    <IconPlay size={16} />
                    {busy ? "Packaging…" : "Download Compound pack"}
                  </button>
                  <button
                    type="button"
                    className="pill ghost"
                    onClick={() => void navigator.clipboard.writeText(conform.compound_prompt)}
                  >
                    <IconCopy size={16} />
                    Copy brief
                  </button>
                  <button type="button" className="pill ghost" onClick={() => setStep("align")}>
                    <IconArrowLeft size={16} />
                    Back
                  </button>
                </div>
                {compoundNote && <p className="soft-note">{compoundNote}</p>}
                <details className="brief-details">
                  <summary>Show edit brief</summary>
                  <pre>{conform.compound_prompt}</pre>
                </details>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
