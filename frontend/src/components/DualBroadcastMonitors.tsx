import { Button, ButtonGroup, FileInput, Tag } from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import { useEffect, useRef, useState } from "react";
import { mediaUrl } from "../api/client";
import type { VisualRig } from "../types/telemetry";

type Props = {
  rig: VisualRig | null;
  referenceUrl: string;
  rawUrl: string;
  conformedUrl: string | null;
  showConformed: boolean;
  onToggleConformed: (v: boolean) => void;
  alignmentScore: number;
  onUpload: (file: File) => void;
};

function formatTc(sec: number) {
  const s = Math.max(0, sec);
  const mm = Math.floor(s / 60);
  const ss = Math.floor(s % 60);
  const ff = Math.floor((s % 1) * 100);
  return `00:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}.${String(ff).padStart(2, "0")}`;
}

export default function DualBroadcastMonitors({
  rig,
  referenceUrl,
  rawUrl,
  conformedUrl,
  showConformed,
  onToggleConformed,
  alignmentScore,
  onUpload,
}: Props) {
  const refVideo = useRef<HTMLVideoElement>(null);
  const bVideo = useRef<HTMLVideoElement>(null);
  const [tc, setTc] = useState(0);
  const [playing, setPlaying] = useState(false);
  const bSrc = showConformed && conformedUrl ? conformedUrl : rawUrl;

  useEffect(() => {
    const a = refVideo.current;
    if (!a) return;
    const onTime = () => setTc(a.currentTime);
    a.addEventListener("timeupdate", onTime);
    return () => a.removeEventListener("timeupdate", onTime);
  }, []);

  useEffect(() => {
    refVideo.current?.load();
    bVideo.current?.load();
    setPlaying(false);
    setTc(0);
  }, [referenceUrl, bSrc]);

  const togglePlay = async () => {
    const a = refVideo.current;
    const b = bVideo.current;
    if (!a || !b) return;
    if (playing) {
      a.pause();
      b.pause();
      setPlaying(false);
      return;
    }
    try {
      b.currentTime = a.currentTime;
      await Promise.all([a.play(), b.play()]);
      setPlaying(true);
    } catch {
      setPlaying(false);
    }
  };

  return (
    <section className="oc-panel flex h-full min-h-[440px] flex-col">
      <div className="oc-panel-header">
        <div className="oc-panel-title">Dual Broadcast Monitors</div>
        <div className="flex items-center gap-2">
          <Button
            small
            icon={playing ? IconNames.PAUSE : IconNames.PLAY}
            onClick={togglePlay}
            text={playing ? "Pause Sync" : "Play Sync"}
          />
          <Tag minimal intent="primary" className="font-mono">
            {formatTc(tc)}
          </Tag>
        </div>
      </div>

      <div className="grid flex-1 grid-cols-[1fr_auto_1fr] gap-2 p-2">
        <div className="oc-monitor is-ref">
          <div className="absolute left-1.5 top-1.5 z-10">
            <Tag minimal intent="success">
              Outlier Reference Rig
            </Tag>
          </div>
          {rig && (
            <div className="absolute right-1.5 top-1.5 z-10">
              <Tag intent="success">
                {rig.yield_multiplier.toFixed(2)}x · {rig.target_specs.splices_per_10s}/10s
              </Tag>
            </div>
          )}
          <video
            ref={refVideo}
            src={mediaUrl(referenceUrl)}
            className="h-full max-h-[340px] w-full object-contain"
            muted
            playsInline
            loop
          />
        </div>

        <div className="flex flex-col items-center justify-center gap-1.5 px-1">
          <div className="oc-panel-meta">Rig Alignment</div>
          <div
            className="font-mono text-[28px] font-semibold tabular-nums leading-none"
            style={{ color: alignmentScore >= 90 ? "var(--phosphor)" : "var(--amber)" }}
          >
            {alignmentScore}%
          </div>
          <div className="oc-align-rail">
            <div
              className="oc-align-fill"
              style={{
                height: `${alignmentScore}%`,
                background: alignmentScore >= 90 ? "var(--phosphor)" : "var(--amber)",
              }}
            />
          </div>
        </div>

        <div className={`oc-monitor ${showConformed ? "is-conf" : "is-raw"}`}>
          <div className="absolute left-1.5 top-1.5 z-10 flex flex-wrap gap-1">
            <ButtonGroup>
              <Button
                small
                intent={!showConformed ? "warning" : "none"}
                active={!showConformed}
                onClick={() => onToggleConformed(false)}
                text="Raw Ingest"
              />
              <Button
                small
                intent={showConformed ? "success" : "none"}
                active={showConformed}
                disabled={!conformedUrl}
                onClick={() => conformedUrl && onToggleConformed(true)}
                text="Conformed"
              />
            </ButtonGroup>
          </div>
          <div className="absolute right-1.5 top-1.5 z-10">
            <FileInput
              text="Upload .MP4"
              inputProps={{
                accept: "video/mp4,video/*",
                onChange: (e) => {
                  const f = (e.currentTarget as HTMLInputElement).files?.[0];
                  if (f) onUpload(f);
                },
              }}
              buttonText="Browse"
            />
          </div>
          <video
            ref={bVideo}
            src={mediaUrl(bSrc)}
            className="h-full max-h-[340px] w-full object-contain"
            muted
            playsInline
            loop
          />
        </div>
      </div>
    </section>
  );
}
