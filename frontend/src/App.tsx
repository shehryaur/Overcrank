import { Classes } from "@blueprintjs/core";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import StudioHeader from "./components/StudioHeader";
import FormatYieldMatrix from "./components/FormatYieldMatrix";
import DualBroadcastMonitors from "./components/DualBroadcastMonitors";
import TelemetryOscilloscope from "./components/TelemetryOscilloscope";
import CompoundEdlModal from "./components/CompoundEdlModal";
import SecretsPanel from "./components/SecretsPanel";
import type {
  CohortSummary,
  CompoundEdl,
  HealthResponse,
  OscilloscopePoint,
  VisualRig,
  YieldMatrix,
} from "./types/telemetry";

export default function App() {
  const [cohorts, setCohorts] = useState<CohortSummary[]>([]);
  const [cohortId, setCohortId] = useState("sf_founder_interviews");
  const [matrix, setMatrix] = useState<YieldMatrix | null>(null);
  const [selectedRig, setSelectedRig] = useState<VisualRig | null>(null);
  const [visualQuery, setVisualQuery] = useState("");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [referenceUrl, setReferenceUrl] = useState("/media/references/ref_hippolyte_outlier.mp4");
  const [rawUrl, setRawUrl] = useState("/media/raw/raw_founder_take.mp4");
  const [rawFilename, setRawFilename] = useState<string | undefined>("raw_founder_take.mp4");
  const [conformedUrl, setConformedUrl] = useState<string | null>(null);
  const [showConformed, setShowConformed] = useState(false);
  const [alignment, setAlignment] = useState(34);
  const [series, setSeries] = useState<OscilloscopePoint[]>([]);
  const [conforming, setConforming] = useState(false);
  const [statusLine, setStatusLine] = useState("");
  const [edlOpen, setEdlOpen] = useState(false);
  const [secretsOpen, setSecretsOpen] = useState(false);
  const [edl, setEdl] = useState<CompoundEdl | null>(null);
  const [prompt, setPrompt] = useState("");

  const loadMatrix = useCallback(async (id: string, q?: string) => {
    const m = await api.yieldMatrix(id, q);
    setMatrix(m);
    const first = m.rigs[0];
    if (first) {
      setSelectedRig((prev) => {
        const still = m.rigs.find((r) => r.rig_id === prev?.rig_id);
        return still || first;
      });
    }
    return m;
  }, []);

  const loadCompare = useCallback(async (id: string, rigId: string, raw?: string) => {
    setStatusLine(`Auditing rig telemetry · ${rigId}`);
    const cmp = await api.compare(id, rigId, raw);
    setSelectedRig(cmp.rig);
    setReferenceUrl(cmp.reference_video_url);
    setRawUrl(cmp.raw_video_url);
    setRawFilename(cmp.raw_filename);
    setAlignment(cmp.alignment_score_before);
    setSeries(cmp.merged_oscilloscope);
    setShowConformed(false);
    setStatusLine(
      `Alignment ${cmp.alignment_score_before}% · projected post-conform ${cmp.alignment_score_projected}%`
    );
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [h, c] = await Promise.all([api.health(), api.cohorts()]);
        setHealth(h);
        setCohorts(c);
        await loadMatrix(cohortId);
      } catch (err) {
        setStatusLine(`Boot error: ${String(err)}`);
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedRig) return;
    loadCompare(cohortId, selectedRig.rig_id, rawFilename).catch((err) =>
      setStatusLine(`Compare failed: ${String(err)}`)
    );
  }, [cohortId, selectedRig?.rig_id]);

  const onCohortChange = async (id: string) => {
    setCohortId(id);
    setConformedUrl(null);
    setShowConformed(false);
    await loadMatrix(id);
  };

  const onSearch = async () => {
    await loadMatrix(cohortId, visualQuery || undefined);
  };

  const onConform = async () => {
    if (!selectedRig) return;
    setConforming(true);
    setStatusLine("Running auto-editor dead-air slice + FFmpeg focal push…");
    try {
      const res = await api.conform(cohortId, selectedRig.rig_id, rawFilename);
      setConformedUrl(res.conformed_video_url);
      setShowConformed(true);
      setAlignment(res.alignment_score_after);
      setSeries(res.merged_oscilloscope_after);
      setEdl(res.compound_edl);
      setPrompt(res.compound_prompt);
      setEdlOpen(true);
      setStatusLine(
        `Conform complete · alignment ${res.alignment_score_after}% · ${res.conformed_filename}`
      );
    } catch (err) {
      setStatusLine(`Conform failed: ${String(err)}`);
    } finally {
      setConforming(false);
    }
  };

  const onUpload = async (file: File) => {
    try {
      const res = await api.uploadRaw(file);
      setRawFilename(res.raw_filename);
      setRawUrl(res.raw_video_url);
      setConformedUrl(null);
      setShowConformed(false);
      if (selectedRig) {
        await loadCompare(cohortId, selectedRig.rig_id, res.raw_filename);
      }
    } catch (err) {
      setStatusLine(`Upload failed: ${String(err)}`);
    }
  };

  return (
    <div className={`${Classes.DARK} oc-shell`}>
      <StudioHeader
        cohorts={cohorts}
        cohortId={cohortId}
        onCohortChange={onCohortChange}
        visualQuery={visualQuery}
        onVisualQueryChange={setVisualQuery}
        onSearch={onSearch}
        indexedVideos={matrix?.indexed_videos ?? 0}
        health={health}
        onOpenEdl={() => setEdlOpen(true)}
        onOpenSecrets={() => setSecretsOpen(true)}
      />

      <div className="grid gap-2 lg:grid-cols-[42%_58%]">
        <FormatYieldMatrix
          matrix={matrix}
          selectedRigId={selectedRig?.rig_id ?? ""}
          onSelectRig={(rig) => {
            setSelectedRig(rig);
            setConformedUrl(null);
            setShowConformed(false);
          }}
        />
        <DualBroadcastMonitors
          rig={selectedRig}
          referenceUrl={referenceUrl}
          rawUrl={rawUrl}
          conformedUrl={conformedUrl}
          showConformed={showConformed}
          onToggleConformed={setShowConformed}
          alignmentScore={alignment}
          onUpload={onUpload}
        />
      </div>

      <TelemetryOscilloscope
        series={series}
        conforming={conforming}
        onConform={onConform}
        statusLine={statusLine}
      />

      <CompoundEdlModal
        open={edlOpen}
        onClose={() => setEdlOpen(false)}
        edl={edl}
        prompt={prompt}
      />
      <SecretsPanel open={secretsOpen} onClose={() => setSecretsOpen(false)} />
    </div>
  );
}
