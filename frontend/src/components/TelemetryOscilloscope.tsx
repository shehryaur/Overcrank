import { Button, Tag } from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import type { ReactNode } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { OscilloscopePoint } from "../types/telemetry";

type Props = {
  series: OscilloscopePoint[];
  conforming: boolean;
  onConform: () => void;
  statusLine?: string;
};

function Track({
  title,
  height,
  children,
}: {
  title: string;
  height: number;
  children: ReactNode;
}) {
  return (
    <div className="oc-track" style={{ height }}>
      <div className="px-2 pt-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
        {title}
      </div>
      <div style={{ height: height - 22 }}>{children}</div>
    </div>
  );
}

export default function TelemetryOscilloscope({
  series,
  conforming,
  onConform,
  statusLine,
}: Props) {
  return (
    <section className="oc-panel">
      <div className="oc-panel-header">
        <div>
          <div className="oc-panel-title">Telemetry Oscilloscope</div>
          <div className="oc-panel-meta">Focal Push · Vocal RMS · Retention Hazard · Splice Cadence</div>
        </div>
        <Button
          className="oc-conform-btn"
          intent="success"
          large
          icon={IconNames.TIMELINE_EVENTS}
          loading={conforming}
          onClick={onConform}
          text={conforming ? "Conforming Footage…" : "[ Conform Footage To Outlier Rig ]"}
        />
      </div>

      {statusLine && (
        <div className="flex items-center gap-2 border-b border-rail px-2.5 py-1">
          <Tag minimal intent="primary">
            Status
          </Tag>
          <span className="font-mono text-[10px] text-cyanMark">{statusLine}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-3 px-2.5 pt-2 font-mono text-[9px] uppercase tracking-wider text-slate-500">
        <span className="text-phosphor">● Ref</span>
        <span className="text-amberSignal">● Raw / Conformed</span>
        <span className="text-cyanMark">┊ Splice</span>
        <span className="text-hazard">■ Hazard</span>
      </div>

      <div className="grid gap-1.5 p-2">
        <Track title="Track 1 — Focal Push Curve (Optical Flow 0–100)" height={132}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={series} margin={{ top: 4, right: 10, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#2F343C" strokeDasharray="2 3" />
              <XAxis dataKey="t" tick={{ fill: "#5C6578", fontSize: 8, fontFamily: "JetBrains Mono" }} unit="s" />
              <YAxis domain={[0, 100]} tick={{ fill: "#5C6578", fontSize: 8, fontFamily: "JetBrains Mono" }} />
              <Tooltip
                contentStyle={{
                  background: "#0E1017",
                  border: "1px solid #2F343C",
                  borderRadius: 2,
                  fontSize: 10,
                  fontFamily: "JetBrains Mono",
                }}
              />
              <Line type="monotone" dataKey="ref_focal_push" stroke="#10B981" dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="raw_focal_push" stroke="#F59E0B" dot={false} strokeWidth={1.4} />
              <Line type="step" dataKey="ref_splice" stroke="#22D3EE" strokeDasharray="3 2" dot={false} strokeWidth={1} />
            </ComposedChart>
          </ResponsiveContainer>
        </Track>

        <Track title="Track 2 — Vocal RMS Energy & Retention Hazard Zones" height={132}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={series} margin={{ top: 4, right: 10, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#2F343C" strokeDasharray="2 3" />
              <XAxis dataKey="t" tick={{ fill: "#5C6578", fontSize: 8, fontFamily: "JetBrains Mono" }} unit="s" />
              <YAxis domain={[0, 100]} tick={{ fill: "#5C6578", fontSize: 8, fontFamily: "JetBrains Mono" }} />
              <Tooltip
                contentStyle={{
                  background: "#0E1017",
                  border: "1px solid #2F343C",
                  borderRadius: 2,
                  fontSize: 10,
                  fontFamily: "JetBrains Mono",
                }}
              />
              <Area type="monotone" dataKey="raw_hazard" fill="#EF444433" stroke="#EF4444" />
              <Line type="monotone" dataKey="ref_vocal_energy" stroke="#10B981" dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="raw_vocal_energy" stroke="#F59E0B" dot={false} strokeWidth={1.4} />
            </ComposedChart>
          </ResponsiveContainer>
        </Track>

        <Track title="Track 3 — Splice Cadence Markers (Ref vs Raw)" height={96}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={series} margin={{ top: 4, right: 10, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#2F343C" strokeDasharray="2 3" />
              <XAxis dataKey="t" tick={{ fill: "#5C6578", fontSize: 8, fontFamily: "JetBrains Mono" }} unit="s" />
              <YAxis domain={[0, 100]} tick={{ fill: "#5C6578", fontSize: 8, fontFamily: "JetBrains Mono" }} />
              <Line type="step" dataKey="ref_splice" stroke="#22D3EE" dot={false} strokeWidth={1.4} />
              <Line type="step" dataKey="raw_splice" stroke="#F59E0B" dot={false} strokeWidth={1.2} />
            </ComposedChart>
          </ResponsiveContainer>
        </Track>
      </div>
    </section>
  );
}
