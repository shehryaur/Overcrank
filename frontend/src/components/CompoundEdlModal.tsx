import {
  Classes,
  Drawer,
  DrawerSize,
  HTMLTable,
  Tag,
} from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import type { CompoundEdl } from "../types/telemetry";

type Props = {
  open: boolean;
  onClose: () => void;
  edl: CompoundEdl | null;
  prompt: string;
};

export default function CompoundEdlModal({ open, onClose, edl, prompt }: Props) {
  return (
    <Drawer
      className={Classes.DARK}
      isOpen={open}
      onClose={onClose}
      size={DrawerSize.STANDARD}
      icon={IconNames.CODE}
      title="Compound.mov Agent Runbook"
      position="right"
      canOutsideClickClose
    >
      <div className={Classes.DRAWER_BODY}>
        <div className="space-y-3 p-3">
          <div className="oc-panel-meta">Edit Decision List · MCP Bridge</div>

          {edl ? (
            <>
              <div className="grid grid-cols-2 gap-1.5">
                <div className="border border-rail bg-[#0a0c12] p-2">
                  <div className="oc-panel-meta">Engine</div>
                  <div className="mt-0.5 font-mono text-[11px] text-slate-200">{edl.engine}</div>
                </div>
                <div className="border border-rail bg-[#0a0c12] p-2">
                  <div className="oc-panel-meta">Rig</div>
                  <div className="mt-0.5 font-mono text-[11px] text-slate-200">{edl.rig_id}</div>
                </div>
                <div className="border border-rail bg-[#0a0c12] p-2">
                  <div className="oc-panel-meta">Target Splices / 10s</div>
                  <Tag minimal intent="success" className="mt-1">
                    {edl.target_splices_per_10s}
                  </Tag>
                </div>
                <div className="border border-rail bg-[#0a0c12] p-2">
                  <div className="oc-panel-meta">Dead-Air Max</div>
                  <Tag minimal intent="warning" className="mt-1">
                    {edl.silence_gate.max_pause_ms}ms
                  </Tag>
                </div>
              </div>

              <div>
                <div className="mb-1.5 oc-panel-meta">Focal Push Keyframes</div>
                <div className="overflow-auto border border-rail" style={{ maxHeight: 180 }}>
                  <HTMLTable compact striped bordered>
                    <thead>
                      <tr>
                        <th>TC</th>
                        <th>Scale</th>
                        <th>Easing</th>
                      </tr>
                    </thead>
                    <tbody>
                      {edl.focal_push_keyframes.map((k) => (
                        <tr key={`${k.timecode_sec}-${k.scale}`}>
                          <td style={{ color: "var(--cyan)" }}>{k.timecode_sec.toFixed(2)}s</td>
                          <td style={{ color: "var(--phosphor)" }}>{k.scale.toFixed(2)}x</td>
                          <td>{k.easing}</td>
                        </tr>
                      ))}
                    </tbody>
                  </HTMLTable>
                </div>
              </div>

              <div>
                <div className="mb-1.5 oc-panel-meta">B-Roll Insert Markers</div>
                <div className="flex flex-wrap gap-1.5">
                  {edl.broll_insert_markers.length === 0 && (
                    <span className="font-mono text-[11px] text-slate-500">None</span>
                  )}
                  {edl.broll_insert_markers.map((t) => (
                    <Tag key={t} minimal>
                      {t.toFixed(1)}s
                    </Tag>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="font-mono text-xs text-slate-400">
              Run CONFORM to generate the Compound.mov EDL runbook.
            </p>
          )}

          <div>
            <div className="mb-1.5 oc-panel-meta">Agent Prompt</div>
            <pre className="oc-code">{prompt || "—"}</pre>
          </div>
        </div>
      </div>
    </Drawer>
  );
}
