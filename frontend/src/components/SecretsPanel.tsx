import { Callout, Classes, Drawer, DrawerSize, Tag } from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import { useEffect, useState } from "react";
import { api } from "../api/client";

type SecretVar = {
  name: string;
  required: boolean;
  set: boolean;
  value?: string;
  purpose: string;
};

type Props = {
  open: boolean;
  onClose: () => void;
};

export default function SecretsPanel({ open, onClose }: Props) {
  const [vars, setVars] = useState<SecretVar[]>([]);
  const [envFile, setEnvFile] = useState("");
  const [instructions, setInstructions] = useState("");

  useEffect(() => {
    if (!open) return;
    api
      .secretsStatus()
      .then((s) => {
        setVars(s.vars);
        setEnvFile(s.env_file);
        setInstructions(s.instructions);
      })
      .catch(() => {
        setInstructions("Could not load secrets status — ensure backend is running.");
      });
  }, [open]);

  return (
    <Drawer
      className={Classes.DARK}
      isOpen={open}
      onClose={onClose}
      size={DrawerSize.SMALL}
      icon={IconNames.KEY}
      title="Studio Secrets"
      position="right"
      canOutsideClickClose
    >
      <div className={Classes.DRAWER_BODY}>
        <div className="space-y-3 p-3">
          <div className="oc-panel-meta">Paste keys after demo · never commit .env</div>
          <Callout intent="warning" icon={IconNames.INFO_SIGN}>
            {instructions}
          </Callout>
          <div className="border border-rail bg-[#0a0c12] p-2 font-mono text-[11px] text-cyanMark">
            {envFile || "backend/.env"}
          </div>

          <div className="space-y-1.5">
            {vars.map((v) => (
              <div key={v.name} className="border border-rail bg-[#0a0c12] p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-slate-100">{v.name}</span>
                  <Tag minimal intent={v.set ? "success" : "warning"}>
                    {v.set ? (v.value ? v.value : "SET") : "EMPTY — paste here"}
                  </Tag>
                </div>
                <p className="mt-1 font-mono text-[10px] leading-snug text-slate-400">{v.purpose}</p>
              </div>
            ))}
          </div>

          <pre className="oc-code">{`# backend/.env
ORIANE_API_KEY=paste_your_key_here
ORIANE_BASE_URL=https://connect.oriane.xyz
ORIANE_CACHE_TTL_HOURS=24`}</pre>
        </div>
      </div>
    </Drawer>
  );
}
