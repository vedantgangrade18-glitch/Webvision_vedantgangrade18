import { cx } from "@/lib/format";

/** Woven stitch motif (separators, passport border, Karu ID band). */
export function Woven({ className }: { className?: string }) {
  return <div className={cx("woven w-full", className)} aria-hidden />;
}

/** DeckleEdge: inline SVG torn-paper deckle edge divider (24px tall). */
export function DeckleEdge({
  flip = false,
  fill = "currentColor",
  className,
}: {
  flip?: boolean;
  fill?: string;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "w-full overflow-hidden leading-none",
        flip ? "rotate-180" : "",
        className
      )}
      aria-hidden
    >
      <svg
        viewBox="0 0 1200 24"
        preserveAspectRatio="none"
        className="h-6 w-full block"
        style={{ color: fill }}
      >
        <path
          d="M0,0 C150,18 280,4 420,16 C560,28 700,6 840,18 C980,30 1100,8 1200,14 L1200,24 L0,24 Z"
          fill="currentColor"
        />
      </svg>
    </div>
  );
}

/** Emblem: Karu Solar Craft Bloom as standalone SVG. */
export function Emblem({
  size = 28,
  className,
  tone = "brand",
}: {
  size?: number;
  className?: string;
  tone?: "brand" | "gold" | "white";
}) {
  const strokeColor = {
    brand: "#8c3b1e",
    gold: "#c59b27",
    white: "#ffffff",
  }[tone];

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={cx("shrink-0", className)}
      aria-hidden
    >
      <circle cx="16" cy="16" r="4.5" fill={strokeColor} />
      <g stroke={strokeColor} strokeWidth="1.5" strokeLinecap="round">
        <line x1="16" y1="3" x2="16" y2="7.5" />
        <line x1="16" y1="24.5" x2="16" y2="29" />
        <line x1="3" y1="16" x2="7.5" y2="16" />
        <line x1="24.5" y1="16" x2="29" y2="16" />
        <line x1="6.8" y1="6.8" x2="10" y2="10" />
        <line x1="22" y1="22" x2="25.2" y2="25.2" />
        <line x1="6.8" y1="25.2" x2="10" y2="22" />
        <line x1="22" y1="10" x2="25.2" y2="6.8" />
      </g>
    </svg>
  );
}

/** Spot illustrations: loom, basket, thread, wheel, needle, parcel. */
export function SpotArt({
  name,
  className,
  size = 64,
}: {
  name: "loom" | "basket" | "thread" | "wheel" | "needle" | "parcel";
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={cx("shrink-0", className)}
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {name === "loom" && (
        <>
          <path d="M12 12h40v40H12z" />
          <line x1="20" y1="12" x2="20" y2="52" strokeDasharray="3 3" />
          <line x1="28" y1="12" x2="28" y2="52" />
          <line x1="36" y1="12" x2="36" y2="52" strokeDasharray="3 3" />
          <line x1="44" y1="12" x2="44" y2="52" />
          <line x1="8" y1="32" x2="56" y2="32" stroke="#c59b27" strokeWidth="2" />
        </>
      )}
      {name === "basket" && (
        <>
          <path d="M14 26h36l-4 26H18z" />
          <path d="M22 26c0-7 4-14 10-14s10 7 10 14" stroke="#c59b27" />
          <line x1="16" y1="35" x2="48" y2="35" />
          <line x1="17" y1="44" x2="47" y2="44" />
        </>
      )}
      {name === "thread" && (
        <>
          <rect x="22" y="16" width="20" height="32" rx="4" />
          <line x1="22" y1="24" x2="42" y2="24" stroke="#c59b27" />
          <line x1="22" y1="32" x2="42" y2="32" stroke="#c59b27" />
          <line x1="22" y1="40" x2="42" y2="40" stroke="#c59b27" />
          <path d="M32 48v8c0 2 2 4 4 4h4" />
        </>
      )}
      {name === "wheel" && (
        <>
          <circle cx="32" cy="32" r="20" />
          <circle cx="32" cy="32" r="6" fill="#c59b27" />
          <line x1="32" y1="12" x2="32" y2="26" />
          <line x1="32" y1="38" x2="32" y2="52" />
          <line x1="12" y1="32" x2="26" y2="32" />
          <line x1="38" y1="32" x2="52" y2="32" />
        </>
      )}
      {name === "needle" && (
        <>
          <line x1="14" y1="50" x2="48" y2="16" strokeWidth="2" />
          <ellipse cx="49" cy="15" rx="3" ry="1.5" transform="rotate(-45 49 15)" stroke="#c59b27" />
          <path d="M51 13c3-3 8-1 9 4s-4 9-9 7" stroke="#c59b27" strokeDasharray="2 2" />
        </>
      )}
      {name === "parcel" && (
        <>
          <rect x="14" y="20" width="36" height="32" rx="2" />
          <path d="M14 28h36" stroke="#c59b27" />
          <line x1="32" y1="20" x2="32" y2="52" stroke="#c59b27" />
          <path d="M26 14h12l6 6H20z" />
        </>
      )}
    </svg>
  );
}
