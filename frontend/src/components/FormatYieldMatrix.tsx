import { Tag } from "@blueprintjs/core";
import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { VisualRig, YieldMatrix } from "../types/telemetry";

type Props = {
  matrix: YieldMatrix | null;
  selectedRigId: string;
  onSelectRig: (rig: VisualRig) => void;
};

function formatViews(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(n);
}

export default function FormatYieldMatrix({ matrix, selectedRigId, onSelectRig }: Props) {
  const rigs = matrix?.rigs ?? [];

  return (
    <section className="oc-panel flex h-full min-h-[440px] flex-col overflow-hidden">
      <div className="oc-panel-header">
        <div className="oc-panel-title">Format Yield Matrix</div>
        <div className="oc-panel-meta">Saturation % × Engagement Yield (x)</div>
      </div>

      <div className="relative h-[230px] px-1 pt-1">
        <div className="pointer-events-none absolute bottom-8 left-10 top-3 w-[36%] bg-phosphor/[0.035]" />
        <div className="pointer-events-none absolute bottom-8 right-3 top-[48%] w-[40%] bg-hazard/[0.04]" />
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 12, bottom: 4, left: -8 }}>
            <CartesianGrid stroke="#2F343C" strokeDasharray="2 3" />
            <XAxis
              type="number"
              dataKey="saturation_pct"
              domain={[0, 55]}
              tick={{ fill: "#8B95A8", fontSize: 9, fontFamily: "JetBrains Mono" }}
              unit="%"
            />
            <YAxis
              type="number"
              dataKey="yield_multiplier"
              domain={[0, 4.2]}
              tick={{ fill: "#8B95A8", fontSize: 9, fontFamily: "JetBrains Mono" }}
              unit="x"
            />
            <ZAxis range={[70, 180]} />
            <ReferenceLine x={10} stroke="#404854" strokeDasharray="3 3" />
            <ReferenceLine y={2} stroke="#404854" strokeDasharray="3 3" />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{
                background: "#0E1017",
                border: "1px solid #2F343C",
                borderRadius: 2,
                fontFamily: "JetBrains Mono",
                fontSize: 10,
              }}
              formatter={(value: number, name: string) => [
                name === "yield_multiplier" ? `${value}x` : `${value}%`,
                name === "yield_multiplier" ? "Yield" : "Saturation",
              ]}
              labelFormatter={() => ""}
            />
            <Scatter
              data={rigs}
              onClick={(d) => {
                const rig = d as unknown as VisualRig;
                if (rig?.rig_id) onSelectRig(rig);
              }}
            >
              {rigs.map((r) => (
                <Cell
                  key={r.rig_id}
                  cursor="pointer"
                  fill={
                    r.yield_multiplier >= 2
                      ? r.rig_id === selectedRigId
                        ? "#34D399"
                        : "#10B981"
                      : r.rig_id === selectedRigId
                        ? "#F87171"
                        : "#EF4444"
                  }
                  stroke={r.rig_id === selectedRigId ? "#E8ECF2" : "transparent"}
                  strokeWidth={r.rig_id === selectedRigId ? 1.5 : 0}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute left-12 top-4 font-mono text-[8px] uppercase tracking-wider text-phosphor/70">
          High-Yield / Unsaturated
        </div>
        <div className="pointer-events-none absolute bottom-10 right-4 font-mono text-[8px] uppercase tracking-wider text-hazard/70">
          Oversaturated Commodity
        </div>
      </div>

      <div className="flex-1 space-y-1.5 overflow-auto border-t border-rail p-2">
        {rigs.map((rig) => {
          const active = rig.rig_id === selectedRigId;
          return (
            <button
              key={rig.rig_id}
              type="button"
              className={`oc-rig-row ${active ? "is-active" : ""}`}
              onClick={() => onSelectRig(rig)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-[12px] font-medium leading-snug text-slate-100">{rig.title}</div>
                <Tag
                  minimal
                  intent={rig.yield_multiplier >= 2 ? "success" : "danger"}
                  style={{ flexShrink: 0 }}
                >
                  {rig.yield_multiplier.toFixed(2)}x
                </Tag>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[10px] text-slate-400">
                <span>SAT {rig.saturation_pct}%</span>
                <span>SPLICE {rig.target_specs.splices_per_10s}/10s</span>
                <span>VIEWS {formatViews(rig.mean_views)}</span>
                <span>{rig.reference_creator}</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
