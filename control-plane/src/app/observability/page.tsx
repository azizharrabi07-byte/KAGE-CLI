"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, SectionHeader, Pill, Sparkline, EmptyState, MetricBar } from "@/components/ui";
import { relativeTime, formatNumber } from "@/lib/format";

type Log = { id: string; level: string; source: string; message: string; meta: Record<string, unknown>; createdAt: string };
type Trace = { id: string; agentId: string; action: string; decision: string | null; durationMs: number | null; createdAt: string };
type MetricSummary = { kind: string; total: number; count: number; avg: number };

const LEVEL_COLOR: Record<string, string> = {
  error: "#fb7185",
  warn: "#fbbf24",
  info: "#60a5fa",
  debug: "#9ca3af",
  trace: "#a78bfa",
};

const TABS = ["logs", "metrics", "traces"] as const;
type Tab = (typeof TABS)[number];

export default function ObservabilityPage() {
  const [tab, setTab] = useState<Tab>("logs");
  const [logs, setLogs] = useState<Log[]>([]);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [summary, setSummary] = useState<MetricSummary[]>([]);
  const [series, setSeries] = useState<{ responseTime: number[]; tokenUsage: number[] }>({ responseTime: [], tokenUsage: [] });
  const [level, setLevel] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const loadLogs = useCallback(async () => {
    const url = level ? `/api/observability/logs?level=${level}&limit=120` : "/api/observability/logs?limit=120";
    const r = await fetch(url, { cache: "no-store" });
    setLogs((await r.json()).data ?? []);
  }, [level]);

  const loadMetrics = useCallback(async () => {
    const r = await fetch("/api/observability/metrics", { cache: "no-store" });
    const j = await r.json();
    setSummary(j.data?.summary ?? []);
    setSeries(j.data?.series ?? { responseTime: [], tokenUsage: [] });
  }, []);

  const loadTraces = useCallback(async () => {
    const r = await fetch("/api/observability/traces?limit=80", { cache: "no-store" });
    setTraces((await r.json()).data ?? []);
  }, []);

  useEffect(() => {
    (async () => {
      await Promise.all([loadLogs(), loadMetrics(), loadTraces()]);
      setLoading(false);
    })();
  }, [loadLogs, loadMetrics, loadTraces]);

  const maxCall = Math.max(...summary.map((s) => s.total), 1);

  return (
    <div className="space-y-6">
      <SectionHeader title="Observability" subtitle="Structured logs, metrics and agent decision traces" icon="◉" />

      <div className="flex gap-1.5">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`k-btn capitalize ${tab === t ? "k-btn-primary" : ""}`}>{t}</button>
        ))}
      </div>

      {tab === "logs" && (
        <Card>
          <div className="mb-3 flex items-center gap-2">
            <span className="text-xs text-[var(--kage-muted)]">level</span>
            {["", "info", "warn", "error", "trace", "debug"].map((l) => (
              <button key={l || "all"} onClick={() => setLevel(l)} className={`k-btn ${level === l ? "k-btn-primary" : ""}`}>{l || "all"}</button>
            ))}
          </div>
          <div className="k-inset max-h-[560px] overflow-auto divide-y divide-white/5">
            {logs.map((l) => (
              <div key={l.id} className="flex items-start gap-3 px-3 py-2 text-xs">
                <span className="mono shrink-0 text-[var(--kage-muted)]">{relativeTime(l.createdAt)}</span>
                <span className="mono shrink-0 font-semibold uppercase" style={{ color: LEVEL_COLOR[l.level] ?? "#9ca3af" }}>{l.level}</span>
                <span className="min-w-0">
                  <span className="text-[var(--kage-violet-soft)]">{l.source}</span>{" "}
                  <span className="text-[var(--kage-text)]">{l.message}</span>
                  {Object.keys(l.meta ?? {}).length > 0 && <span className="mono ml-1 text-[10px] text-[var(--kage-muted)]">{JSON.stringify(l.meta)}</span>}
                </span>
              </div>
            ))}
            {logs.length === 0 && <div className="p-6"><EmptyState icon="◉" title="No logs" /></div>}
          </div>
        </Card>
      )}

      {tab === "metrics" && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            {summary.map((s) => (
              <div key={s.kind} className="k-inset p-4">
                <p className="text-[11px] uppercase tracking-wider text-[var(--kage-muted)]">{s.kind.replace(/_/g, " ")}</p>
                <p className="mono mt-1 text-2xl font-semibold text-white">{formatNumber(s.total)}</p>
                <p className="mono text-[10px] text-[var(--kage-muted)]">{s.count} samples · avg {Math.round(s.avg)}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <SectionHeader title="Response time" subtitle="ms over recent steps" icon="⟶" action={<Pill tone="violet">series</Pill>} />
              <div className="mt-4"><Sparkline values={series.responseTime} color="#a78bfa" height={70} /></div>
            </Card>
            <Card>
              <SectionHeader title="Token usage" subtitle="cumulative tokens" icon="▦" action={<Pill tone="emerald">series</Pill>} />
              <div className="mt-4"><Sparkline values={series.tokenUsage} color="#34d399" height={70} /></div>
            </Card>
          </div>
          <Card>
            <SectionHeader title="Volume by kind" subtitle="relative totals" icon="◉" />
            <div className="mt-4 space-y-3">
              {summary.map((s) => (
                <MetricBar key={s.kind} label={s.kind.replace(/_/g, " ")} value={s.total} max={maxCall} />
              ))}
            </div>
          </Card>
        </div>
      )}

      {tab === "traces" && (
        <Card>
          <div className="k-inset max-h-[600px] overflow-auto divide-y divide-white/5">
            {traces.map((t) => (
              <div key={t.id} className="flex items-start gap-3 px-3 py-2.5 text-xs">
                <span className="mono shrink-0 text-[var(--kage-muted)]">{relativeTime(t.createdAt)}</span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--kage-violet-soft)]">{t.action}</span>
                    <Pill>{t.agentId}</Pill>
                    <span className="mono text-[10px] text-[var(--kage-muted)]">{t.durationMs ?? 0}ms</span>
                  </div>
                  {t.decision && <p className="mt-0.5 text-[var(--kage-muted)]">{t.decision}</p>}
                </div>
              </div>
            ))}
            {traces.length === 0 && <div className="p-6"><EmptyState icon="◉" title="No traces yet" hint="Run workflows or execute agents to populate the decision chain." /></div>}
          </div>
        </Card>
      )}

      {loading && <p className="text-xs text-[var(--kage-muted)]">syncing…</p>}
    </div>
  );
}
