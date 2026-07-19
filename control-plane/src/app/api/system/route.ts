import { db } from "@/db";
import { agents, workflows, integrations, logs } from "@/db/schema";
import { sql, desc, eq, gt } from "drizzle-orm";
import { cacheStats } from "@/lib/cache";
import { VERSION, CODENAME, VERSION_INFO } from "@/lib/version";

export const dynamic = "force-dynamic";

/** Aggregated overview used by the dashboard + live polling. */
export async function GET() {
  const [a] = await db.select({ c: sql<number>`count(*)::int` }).from(agents);
  const awake = await db.select({ c: sql<number>`count(*)::int` }).from(agents).where(eq(agents.status, "awake"));
  const executing = await db.select({ c: sql<number>`count(*)::int` }).from(agents).where(eq(agents.status, "executing"));
  const [w] = await db.select({ c: sql<number>`count(*)::int` }).from(workflows);
  const running = await db.select({ c: sql<number>`count(*)::int` }).from(workflows).where(eq(workflows.status, "running"));
  const [i] = await db.select({ c: sql<number>`count(*)::int` }).from(integrations);
  const healthy = await db.select({ c: sql<number>`count(*)::int` }).from(integrations).where(eq(integrations.status, "healthy"));

  const since = new Date(Date.now() - 1000 * 60 * 60);
  const recentLogs = await db
    .select({ c: sql<number>`count(*)::int` })
    .from(logs)
    .where(gt(logs.createdAt, since));

  return Response.json({
    version: VERSION,
    codename: CODENAME,
    phases: VERSION_INFO.phases,
    uptime: process.uptime(),
    agents: { total: a?.c ?? 0, awake: awake[0]?.c ?? 0, executing: executing[0]?.c ?? 0 },
    workflows: { total: w?.c ?? 0, running: running[0]?.c ?? 0 },
    integrations: { total: i?.c ?? 0, healthy: healthy[0]?.c ?? 0 },
    logsLastHour: recentLogs[0]?.c ?? 0,
    cache: cacheStats(),
  });
}
