import { db } from "@/db";
import { agents, workflows, integrations, logs, metrics } from "@/db/schema";
import { sql, desc, eq, gt } from "drizzle-orm";
import { ensureSeeded } from "@/lib/seed";
import { cacheStats } from "@/lib/cache";
import { VERSION_INFO } from "@/lib/version";
import { Card, SectionHeader, Stat, StatusBadge, Pill, Sparkline, MetricBar } from "@/components/ui";
import { relativeTime, formatNumber, formatMs } from "@/lib/format";

export const dynamic = "force-dynamic";

async function summary() {
  const [a] = await db.select({ c: sql<number>`count(*)::int` }).from(agents);
  const awake = await db.select({ c: sql<number>`count(*)::int` }).from(agents).where(eq(agents.status, "awake"));
  const [w] = await db.select({ c: sql<number>`count(*)::int` }).from(workflows);
  const integ = await db.select().from(integrations);
  const healthy = integ.filter((i) => i.status === "healthy").length;
  const since = new Date(Date.now() - 3600_000);
  const [lc] = await db.select({ c: sql<number>`count(*)::int` }).from(logs).where(gt(logs.createdAt, since));
  const mSummary = await db
    .select({ kind: metrics.kind, total: sql<number>`coalesce(sum(${metrics.value}),0)::float8`, count: sql<number>`count(*)::int` })
    .from(metrics)
    .groupBy(metrics.kind);
  const series = await db.select({ value: metrics.value }).from(metrics).where(eq(metrics.kind, "response_time")).orderBy(desc(metrics.createdAt)).limit(40);
  return {
    agentTotal: a?.c ?? 0,
    awake: awake[0]?.c ?? 0,
    wfTotal: w?.c ?? 0,
    healthy,
    integTotal: integ.length,
    logsHour: lc?.c ?? 0,
    metrics: mSummary,
    series: series.map((s) => s.value).reverse(),
    integ,
  };
}

function uptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default async function HomePage() {
  await ensureSeeded();
  const s = await summary();
  const recentAgents = await db.select().from(agents).orderBy(desc(agents.createdAt)).limit(6);
  const recentLogs = await db.select().from(logs).orderBy(desc(logs.createdAt)).limit(8);
  const tokenMetric = s.metrics.find((m) => m.kind === "token_usage");
  const callMetric = s.metrics.find((m) => m.kind === "agent_call");
  const rtMetric = s.metrics.find((m) => m.kind === "response_time");

  return (
    <div className="space-y-7">
      <header>
        <div className="flex items-center gap-2">
          <Pill tone="violet">v{VERSION_INFO.version}</Pill>
          <Pill tone="emerald">phases 1–8</Pill>
        </div>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">Supervisor Overview</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--kage-muted)]">
          Real-time posture of the KAGE OS multi-agent supervisor — registry, workflow engine, integration health and observability.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Agents awake" value={`${s.awake}/${s.agentTotal}`} sub={`${formatNumber(s.agentTotal)} registered`} accent="#a78bfa" />
        <Stat label="Workflows" value={s.wfTotal} sub="across all statuses" accent="#60a5fa" />
        <Stat label="Integrations healthy" value={`${s.healthy}/${s.integTotal}`} sub="live probes" accent="#34d399" />
        <Stat label="Logs / hour" value={formatNumber(s.logsHour)} sub={`uptime ${uptime(process.uptime())}`} accent="#fbbf24" />
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader
            title="Agent Registry"
            subtitle="Multi-agent crew with wake / execute / sleep lifecycle"
            icon="⬡"
            action={<Pill>{recentAgents.length} shown</Pill>}
          />
          <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {recentAgents.map((a) => (
              <div key={a.id} className="k-inset flex items-center justify-between px-3.5 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{a.name}</p>
                  <p className="mono truncate text-[11px] text-[var(--kage-muted)]">{a.kind} · {a.model}</p>
                </div>
                <StatusBadge status={a.status} live={a.status === "executing"} />
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader title="Integration Health" subtitle="Phase 4 probes" icon="⊞" />
          <div className="mt-4 space-y-2.5">
            {s.integ.slice(0, 6).map((i) => (
              <div key={i.id} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm text-white">{i.name}</p>
                  <p className="mono text-[11px] text-[var(--kage-muted)]">
                    {i.latencyMs != null ? formatMs(i.latencyMs) : "—"} · {i.kind}
                  </p>
                </div>
                <StatusBadge status={i.status} live={i.status === "healthy"} />
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <SectionHeader title="Response Latency" subtitle="recent workflow step timings (ms)" icon="◉" action={<Pill tone="emerald">avg {rtMetric ? Math.round(rtMetric.total / (rtMetric.count || 1)) : 0}ms</Pill>} />
          <div className="mt-4">
            <Sparkline values={s.series} color="#a78bfa" height={64} />
          </div>
          <div className="mt-4 space-y-3">
            <MetricBar label="Token usage" value={tokenMetric?.total ?? 0} max={(tokenMetric?.total ?? 0) + 1} unit="tokens" color="#34d399" />
            <MetricBar label="Agent calls" value={callMetric?.total ?? 0} max={(callMetric?.total ?? 0) + 1} color="#60a5fa" />
          </div>
        </Card>

        <Card>
          <SectionHeader title="Activity Stream" subtitle="structured logs" icon="❒" />
          <div className="mt-4 space-y-2">
            {recentLogs.map((l) => (
              <div key={l.id} className="flex items-start gap-2 text-xs">
                <span className="mono mt-0.5 shrink-0 text-[var(--kage-muted)]">{relativeTime(l.createdAt)}</span>
                <span className="min-w-0">
                  <span className="text-[var(--kage-violet-soft)]">{l.source}</span>{" "}
                  <span className="text-[var(--kage-muted)]">{l.message}</span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}
