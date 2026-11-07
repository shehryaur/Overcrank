/** Muse / Instagram-style outline icons — stroke only, empty fill. */

import type { ReactNode } from "react";

type IconProps = {
  size?: number;
  className?: string;
  strokeWidth?: number;
};

function Svg({
  size = 18,
  className,
  strokeWidth = 1.5,
  children,
}: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <g
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      >
        {children}
      </g>
    </svg>
  );
}

export function IconSearch(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </Svg>
  );
}

export function IconArrowRight(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </Svg>
  );
}

export function IconArrowLeft(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M19 12H5" />
      <path d="M11 6l-6 6 6 6" />
    </Svg>
  );
}

export function IconUpload(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M12 16V5" />
      <path d="M8 9l4-4 4 4" />
      <path d="M4 19h16" />
    </Svg>
  );
}

export function IconCopy(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </Svg>
  );
}

export function IconRefresh(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M21 12a9 9 0 1 1-2.6-6.3" />
      <path d="M21 4v5h-5" />
    </Svg>
  );
}

export function IconCheck(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M5 12.5l4.5 4.5L19 7" />
    </Svg>
  );
}

export function IconPlay(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M10 8.5v7l6-3.5-6-3.5z" />
    </Svg>
  );
}

export function IconClapper(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="3" y="8" width="18" height="12" rx="2" />
      <path d="M3 12h18" />
      <path d="M7 4l3 4M12 4l3 4M17 4l3 4" />
    </Svg>
  );
}

export function IconWave(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M3 12h2l2-5 3 10 3-8 2 3h6" />
    </Svg>
  );
}

export function IconScissors(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="6" cy="7" r="2.5" />
      <circle cx="6" cy="17" r="2.5" />
      <path d="M8.2 8.5L20 17" />
      <path d="M8.2 15.5L20 7" />
    </Svg>
  );
}

export function IconYoutube(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="2.5" y="6" width="19" height="12" rx="3.5" />
      <path d="M10.5 9.5v5l5-2.5-5-2.5z" />
    </Svg>
  );
}

export function IconTiktok(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M14 4v9.2a3.8 3.8 0 1 1-2.6-3.6" />
      <path d="M14 7.2c1.2 1.4 2.8 2.2 4.5 2.3V12c-1.9-.1-3.6-.9-4.5-2.2" />
    </Svg>
  );
}

export function IconInstagram(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="0.8" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function IconMark(p: IconProps) {
  return (
    <Svg {...p} size={p.size ?? 16}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  );
}

export function PlatformIcon({ platform, size = 14 }: { platform: string; size?: number }) {
  const p = platform.toLowerCase();
  if (p === "youtube") return <IconYoutube size={size} />;
  if (p === "tiktok") return <IconTiktok size={size} />;
  if (p === "instagram") return <IconInstagram size={size} />;
  return <IconPlay size={size} />;
}
