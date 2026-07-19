import { db } from "@/db";
import { metrics } from "@/db/schema";
import { sql, eq, asc } from "drizzle-orm";

export const dynamic = "force-dynamic";

export async function GET() {
  const summary = await db
    .select({
      kind: metrics.kind,
      total: sql<number>`coalesce(sum(${metrics.value}),0)::float8`,
      count: sql<number>`count(*)::int`,
      avg: sql<number>`coalesce(avg(${metrics.value}),0)::float8`,
    })
    .from(metrics)
    .groupBy(metrics.kind);

  const responseSeries = await db
    .select({ t: metrics.createdAt, value: metrics.value })
    .from(metrics)
    .where(eq(metrics.kind, "response_time"))
    .orderBy(asc(metrics.createdAt))
    .limit(48);

  const tokenSeries = await db
    .select({ t: metrics.createdAt, value: metrics.value })
    .from(metrics)
    .where(eq(metrics.kind, "token_usage"))
    .orderBy(asc(metrics.createdAt))
    .limit(48);

  const byKind = (rows: { value: number }[]) => rows.map((r) => r.value);

  return Response.json({
    status: "ok",
    data: {
      summary,
      series: {
        responseTime: byKind(responseSeries),
        tokenUsage: byKind(tokenSeries),
      },
    },
  });
}
