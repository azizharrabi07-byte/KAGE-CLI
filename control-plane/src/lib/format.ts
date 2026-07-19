/** Small pure formatting helpers shared across server + client code. */

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function relativeTime(iso: string | Date | null): string {
  if (!iso) return "never";
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const diff = Date.now() - d.getTime();
  if (Number.isNaN(diff)) return "—";
  const abs = Math.abs(diff);
  const future = diff < 0;
  const units: Array<[number, string]> = [
    [1000, "s"],
    [60_000, "m"],
    [3_600_000, "h"],
    [86_400_000, "d"],
  ];
  if (abs < 1000) return future ? "just now" : "just now";
  let unit: [number, string] = units[0];
  for (const u of units) if (abs >= u[0]) unit = u;
  const value = Math.round(abs / unit[0]);
  return future ? `in ${value}${unit[1]}` : `${value}${unit[1]} ago`;
}

export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return `${n}`;
}

export function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function truncate(value: string, max = 120): string {
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}

export function titleCase(value: string): string {
  return value
    .split(/[-_ ]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
