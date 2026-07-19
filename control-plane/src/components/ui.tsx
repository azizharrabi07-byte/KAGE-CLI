import type { ReactNode } from "react";
import { cx, formatNumber } from "@/lib/format";

/* --------------------------------- Layout --------------------------------- */

export function Card({
  children,
  className,
  hover,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return <div className={cx("k-card p-5", hover && "k-card-hover", className)}>{children}</div>;
}

export function SectionHeader({
  title,
  subtitle,
  icon,
  action,
}: {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && <div className="text-xl leading-none">{icon}</div>}
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-white">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-[var(--kage-muted)]">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ icon = "·", title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="k-inset flex flex-col items-center justify-center gap-1 px-6 py-10 text-center">
      <div className="text-2xl opacity-60">{icon}</div>
      <p className="text-sm font-medium text-[var(--kage-text)]">{title}</p>
      {hint && <p className="text-xs text-[var(--kage-muted)]">{hint}</p>}
    </div>
  );
}

/* --------------------------------- Badges --------------------------------- */

const STATUS_TONES: Record<string, { dot: string; text: string; bg: string }> = {
  awake: { dot: "#34d399", text: "#6ee7b7", bg: "rgba(52,211,153,0.12)" },
  healthy: { dot: "#34d399", text: "#6ee7b7", bg: "rgba(52,211,153,0.12)" },
  completed: { dot: "#34d399", text: "#6ee7b7", bg: "rgba(52,211,153,0.12)" },
  ok: { dot: "#34d399", text: "#6ee7b7", bg: "rgba(52,211,153,0.12)" },
  executing: { dot: "#fbbf24", text: "#fcd34d", bg: "rgba(251,191,36,0.12)" },
  running: { dot: "#60a5fa", text: "#93c5fd", bg: "rgba(96,165,250,0.12)" },
  degraded: { dot: "#fbbf24", text: "#fcd34d", bg: "rgba(251,191,36,0.12)" },
  paused: { dot: "#fbbf24", text: "#fcd34d", bg: "rgba(251,191,36,0.12)" },
  sleeping: { dot: "#9ca3af", text: "#cbd5e1", bg: "rgba(148,163,184,0.12)" },
  unknown: { dot: "#9ca3af", text: "#cbd5e1", bg: "rgba(148,163,184,0.12)" },
  draft: { dot: "#9ca3af", text: "#cbd5e1", bg: "rgba(148,163,184,0.12)" },
  error: { dot: "#fb7185", text: "#fda4af", bg: "rgba(251,113,133,0.12)" },
  down: { dot: "#fb7185", text: "#fda4af", bg: "rgba(251,113,133,0.12)" },
  failed: { dot: "#fb7185", text: "#fda4af", bg: "rgba(251,113,133,0.12)" },
  cancelled: { dot: "#6b7280", text: "#9ca3af", bg: "rgba(107,114,128,0.14)" },
};

export function StatusBadge({ status, live }: { status: string; live?: boolean }) {
  const tone = STATUS_TONES[status] ?? STATUS_TONES.unknown;
  return (
    <span
      className="k-chip mono inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide"
      style={{ color: tone.text, background: tone.bg }}
    >
      <span
        className={cx("inline-block h-1.5 w-1.5 rounded-full", live && "k-live")}
        style={{ background: tone.dot }}
      />
      {status}
    </span>
  );
}

export function Pill({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "violet" | "emerald" }) {
  const styles: Record<string, string> = {
    default: "text-[var(--kage-muted)]",
    violet: "text-[var(--kage-violet-soft)]",
    emerald: "text-[var(--kage-emerald)]",
  };
  return (
    <span className={cx("k-chip mono px-2 py-0.5 text-[11px] uppercase tracking-wide", styles[tone])}>{children}</span>
  );
}

/* ---------------------------------- Stats --------------------------------- */

export function Stat({ label, value, sub, accent }: { label: string; value: ReactNode; sub?: string; accent?: string }) {
  return (
    <div className="k-inset p-4">
      <p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">{label}</p>
      <p className="mono mt-1 text-2xl font-semibold" style={{ color: accent ?? "var(--kage-text)" }}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-[var(--kage-muted)]">{sub}</p>}
    </div>
  );
}

export function MetricBar({ label, value, max, unit, color = "#8b5cf6" }: { label: string; value: number; max: number; unit?: string; color?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-[var(--kage-muted)]">{label}</span>
        <span className="mono text-[var(--kage-text)]">
          {formatNumber(value)}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

/* -------------------------------- Sparkline ------------------------------- */

export function Sparkline({ values, color = "#a78bfa", height = 40 }: { values: number[]; color?: string; height?: number }) {
  if (values.length === 0) {
    return <div className="k-inset flex items-center justify-center text-xs text-[var(--kage-muted)]" style={{ height }}>no data yet</div>;
  }
  const w = 100;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = values.length > 1 ? w / (values.length - 1) : w;
  const pts = values.map((v, i) => `${(i * step).toFixed(2)},${(height - ((v - min) / range) * height).toFixed(2)}`);
  const area = `0,${height} ${pts.join(" ")} ${w},${height}`;
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }}>
      <defs>
        <linearGradient id={`spark-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#spark-${color.replace("#", "")})`} />
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
