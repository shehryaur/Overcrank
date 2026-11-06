import {
  Button,
  ButtonGroup,
  HTMLSelect,
  InputGroup,
  Navbar,
  NavbarDivider,
  NavbarGroup,
  NavbarHeading,
  Tag,
} from "@blueprintjs/core";
import { IconNames } from "@blueprintjs/icons";
import type { CohortSummary, HealthResponse } from "../types/telemetry";

type Props = {
  cohorts: CohortSummary[];
  cohortId: string;
  onCohortChange: (id: string) => void;
  visualQuery: string;
  onVisualQueryChange: (q: string) => void;
  onSearch: () => void;
  indexedVideos: number;
  health: HealthResponse | null;
  onOpenEdl: () => void;
  onOpenSecrets: () => void;
};

export default function StudioHeader({
  cohorts,
  cohortId,
  onCohortChange,
  visualQuery,
  onVisualQueryChange,
  onSearch,
  indexedVideos,
  health,
  onOpenEdl,
  onOpenSecrets,
}: Props) {
  return (
    <Navbar className="oc-panel" style={{ padding: "4px 8px" }}>
      <NavbarGroup align="start" style={{ gap: 10 }}>
        <span className="oc-led" aria-hidden />
        <NavbarHeading style={{ margin: 0 }}>
          <div className="oc-brand">OVERCRANK</div>
          <div className="oc-brand-sub">Broadcast Telemetry & Conform Rig</div>
        </NavbarHeading>
        <NavbarDivider />
        <HTMLSelect
          value={cohortId}
          onChange={(e) => onCohortChange(e.currentTarget.value)}
          options={cohorts.map((c) => ({ label: c.label, value: c.cohort_id }))}
          style={{ maxWidth: 340, minWidth: 220 }}
        />
        <InputGroup
          leftIcon={IconNames.SEARCH}
          placeholder="Search visual frame setup via Oriane API…"
          value={visualQuery}
          onChange={(e) => onVisualQueryChange(e.currentTarget.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
          style={{ minWidth: 240, width: 320 }}
          rightElement={
            <Button minimal intent="primary" icon={IconNames.SERIES_SEARCH} onClick={onSearch} text="Scan" />
          }
        />
      </NavbarGroup>

      <NavbarGroup align="end" style={{ gap: 6 }}>
        <Tag minimal intent="none">
          Oriane Index · {indexedVideos.toLocaleString()} clips
        </Tag>
        <Tag minimal intent="success">
          GMI GPU · 18ms
        </Tag>
        <Tag minimal intent={health?.oriane_connected ? "success" : "warning"}>
          {health?.oriane_connected ? "Oriane Live" : "Fixture Mode"}
        </Tag>
        <ButtonGroup>
          <Button
            icon={IconNames.KEY}
            intent="warning"
            minimal
            onClick={onOpenSecrets}
            text="Secrets"
          />
          <Button
            icon={IconNames.CODE}
            intent="success"
            outlined
            onClick={onOpenEdl}
            text="MCP / Compound.mov EDL"
          />
        </ButtonGroup>
      </NavbarGroup>
    </Navbar>
  );
}
